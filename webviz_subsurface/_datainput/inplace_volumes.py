import os
import fnmatch
import json
from math import isclose
from pathlib import Path

import yaml
import pandas as pd
import numpy as np
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from .fmu_input import load_ensemble_set
from .._abbreviations.reservoir_simulation import simulation_region_vector_breakdown
from .._abbreviations.volume_terminology import simulation_vector_column_match

try:
    import fmu.ensemble
except ImportError:  # fmu.ensemble is an optional dependency, e.g.
    pass  # for a portable webviz instance, it is never used.


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def scratch_ensemble(ensemble_name, ensemble_path):
    return fmu.ensemble.ScratchEnsemble(ensemble_name, ensemble_path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def extract_volumes(
    ensemble_paths, volfolder, volfiles, fipfile, column_keys, time_index
) -> pd.DataFrame:
    volumes = []
    if volfiles:
        volumes.append(extract_volumes_csv(ensemble_paths, volfolder, volfiles))
        volumes[0]["DATE"] = "Initial"
    if fipfile:
        volumes.append(
            extract_volumes_simulation(ensemble_paths, fipfile, column_keys, time_index)
        )
    return pd.concat(volumes, sort=False)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def extract_volumes_csv(ensemble_paths, volfolder, volfiles) -> pd.DataFrame:
    """Aggregates volumetric files from an FMU ensemble.
    Files must be stored on standardized csv format.
    """
    dfs = []
    for ens_name, ens_path in ensemble_paths.items():
        ens_dfs = []
        ens = scratch_ensemble(ens_name, ens_path)
        for volname, volfile in volfiles.items():
            try:
                path = os.path.join(volfolder, volfile)
                df = ens.load_csv(path)
                df["SOURCE"] = volname
                df["ENSEMBLE"] = ens_name
                ens_dfs.append(df)
            except ValueError:
                pass
        try:
            dfs.append(pd.concat(ens_dfs))
        except ValueError:
            pass
    if not dfs:
        raise ValueError(
            f"Error when aggregating inplace volumetric files: {list(volfiles)}. "
            f"Ensure that the files are present in relative folder {volfolder}"
        )
    return pd.concat(dfs)


def _calc_recovery(vector: str):
    """Calculating recovery factor
    (-current inplace + initial inplace)/(initial inplace)

    Vector is inplace sorted by date.
    -np.inf will occur if vector.iloc[0]==0 => initial inplace = 0, but recovery without initial
    inplace is undefined, therefore replacing by np.nan.
    """
    return ((-vector + vector.iloc[0]) / vector.iloc[0]).replace(-np.inf, np.nan)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def _get_groups(fipmap: dict, fiparray: str, node: int):
    """Get groups (e.g. ZONE and REGION given a map (dict) fiparray (str, e.g. FIPNUM) and node
    (integer)"""
    groups = {}
    try:
        for group, group_map in fipmap[fiparray].items():
            inv_group_map = {vi: k for k, v in group_map.items() for vi in v}
            groups.update(
                {group: inv_group_map.get(int(node))}
                if inv_group_map.get(int(node)) is not None
                else {}
            )
    except KeyError:
        pass
    return groups


def _namedtuple_fixer(column: str):
    """Namedtuples cannot handle :"""
    return column.replace(":", "tempfix")


def _namedtuple_restore(column: str):
    """Namedtuples cannot handle :"""
    return column.replace("tempfix", ":")


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def extract_volumes_simulation(
    ensemble_paths: dict, fipfile, column_keys: list = None, time_index="monthly"
) -> pd.DataFrame:
    """Aggregates volumes from simulation data, matches them to inplace columns
    and groups, and calculates recovery
    """
    fipmap, fipnames = _read_and_format_fipfile(fipfile)
    if column_keys is None:
        # Default column_keys
        column_keys = ["R[WOG]IP*", "R[WOGRH]PV*", "F[OGW]PT"]
    for total_vector in ["FOPT", "FGPT", "FWPT"]:
        # Need at least one total production vector to check if initial,
        # preferably all phases. Checking if they are in the pattern to avoid
        # doubling (gives column names that are not unique)
        if not sum([fnmatch.fnmatch(total_vector, pattern) for pattern in column_keys]):
            column_keys.append(total_vector)

    smry_dynamic = (
        load_ensemble_set(ensemble_paths=ensemble_paths)
        .get_smry(time_index=time_index, column_keys=column_keys)
        .sort_values(by=["ENSEMBLE", "REAL", "DATE"])
    )
    # As we have sorted by date, we can simply pick first line per ENSEMBLE-REAL as first value.
    # If we have any production at this date (or lack data), it might be that the simulation is a
    # restart, and that the first in place point is not actually initial, therefore not calculating
    # recovery. Note that we only require one of FOPT, FGPT and FWPT to exist, so if e.g. you have
    # only produced oil/gas, but the only vector you have exported is FWPT, the test will pass.
    is_initial = {}
    for ens in ensemble_paths.keys():
        max_first = -1  # sub-zero start-point
        for total_vector in ["FOPT", "FGPT", "FWPT"]:
            if total_vector in smry_dynamic.columns:
                max_first = max(
                    [
                        max_first,
                        max(
                            smry_dynamic[smry_dynamic["ENSEMBLE"] == ens]
                            .groupby(by=["REAL"], as_index=False)
                            .nth(0)[total_vector]
                        ),
                    ]
                )
        if isclose(max_first, 0, abs_tol=1e-6):
            is_initial.update({ens: True})
        else:
            is_initial.update({ens: False})

    # Using the columns to build the new DataFrame structure by defining two dicts
    # Creating a separate dict for initial, as initial is not always at the same date.
    # Base information. Source will be e.g. FIPNUM, FIELD or FIPXXX
    initial_dict = {"ENSEMBLE": [], "REAL": [], "DATE": [], "SOURCE": []}
    # A group is e.g. REGION, ZONE (defined by the fip_file)
    groups = set()
    # Each fip_array is the sources defined in fip_file, like FIPNUM
    fip_arrays = {}
    for vector in smry_dynamic.columns:
        # Getting the vector name, e.g. ROIP for ROIP:1, the fiparray (like FIPNUM) and the node.
        [vector_base_name, fiparray, node,] = simulation_region_vector_breakdown(vector)
        # Checking if the vector fits with a valid volume terminology
        matched_column = simulation_vector_column_match(vector_base_name)
        if matched_column:
            # If so add to dict
            initial_dict.update({matched_column: []})
            if fip_arrays.get(fiparray) is None:
                # Add the fip_array if it doesn't exist
                fip_arrays[fiparray] = {}

            if fip_arrays[fiparray].get(node) is None:
                # Add the fip_array's node (e.g 1 for FIPNUM==1) if it is not yet included
                # fip_array's and nodes are enough to find associated groups: Storing these.
                # In addition: Store the vector's matched column as a column for this node.
                fip_arrays[fiparray][node] = {
                    matched_column: vector,
                    "GROUPS": _get_groups(fipmap, fiparray, node),
                }
                # Updating the set of used groups
                groups.update(_get_groups(fipmap, fiparray, node).keys())
            else:
                # Only storing vector - column match to node, as groups were added when
                # the node was initialized.
                fip_arrays[fiparray][node].update({matched_column: vector})
    # All the groups have separate columns in the future DataFrame
    for group in groups:
        initial_dict.update({group: []})
    # Safe copy of structure for the dynamic dict (all dates)
    dynamic_dict = json.loads(json.dumps(initial_dict))
    volume_columns = set(initial_dict.keys()).difference(
        {"ENSEMBLE", "REAL", "DATE", "SOURCE"}, groups
    )
    # The pandas itertuple returns namedtuples which can't handle ':'
    smry_dynamic.rename(columns=_namedtuple_fixer, inplace=True)
    current_ens_real = (None, None)
    # Iterating over all the rows in the dataframe to reformat to the required structure
    for row in smry_dynamic.itertuples(index=False):
        # Already sorted by date within ensemble - real pair. Checking if new pair, so that the
        # first row/date is appended as initial if initial test passed for ensemble.
        if current_ens_real != (row.ENSEMBLE, row.REAL):
            current_ens_real = (row.ENSEMBLE, row.REAL)
            new_real = True
        else:
            new_real = False
        for fip_array, nodes_data in fip_arrays.items():
            for node, node_data in nodes_data.items():
                if new_real and is_initial[row.ENSEMBLE]:
                    initial_dict["DATE"].append("Initial")
                    initial_dict["ENSEMBLE"].append(row.ENSEMBLE)
                    initial_dict["REAL"].append(row.REAL)
                    initial_dict["SOURCE"].append(fipnames.get(fip_array, fip_array))
                    for group in groups:
                        initial_dict[group].append(node_data["GROUPS"].get(group))
                    for volume_column in volume_columns:
                        initial_dict[volume_column].append(
                            getattr(
                                row,
                                _namedtuple_fixer(node_data.get(volume_column, "")),
                                None,
                            )
                        )
                dynamic_dict["DATE"].append(str(row.DATE))
                dynamic_dict["ENSEMBLE"].append(row.ENSEMBLE)
                dynamic_dict["REAL"].append(row.REAL)
                dynamic_dict["SOURCE"].append(fipnames.get(fip_array, fip_array))
                for group in groups:
                    dynamic_dict[group].append(node_data["GROUPS"].get(group))
                for volume_column in volume_columns:
                    dynamic_dict[volume_column].append(
                        getattr(
                            row,
                            _namedtuple_fixer(node_data.get(volume_column, "")),
                            None,
                        )
                    )
    initial_df = pd.DataFrame(initial_dict)
    return (
        pd.DataFrame(dynamic_dict)
        if initial_df.empty
        else pd.concat([initial_df, pd.DataFrame(dynamic_dict)], sort=False)
    )


def _read_and_format_fipfile(fipfile):
    formatted_dict = {}
    fipname_dict = {}
    # for name, fip_file in fipfiles.items():
    with open(Path(fipfile), "r") as stream:
        fipdict = yaml.safe_load(stream)
    for fip, fipdef in fipdict.items():
        formatted_dict[fip] = {}
        fipname_dict.update({fip: fipdef.get("name", fip)})
        for group, group_def in fipdef.get("groups").items():
            group_dict = {}
            fip_regions_used = set()
            for key, fip_regions in group_def.items():
                fip_regions = (
                    [fip_regions] if not isinstance(fip_regions, list) else fip_regions
                )
                if not all(isinstance(x, int) for x in fip_regions):
                    raise TypeError(
                        f"FIP: {fip}, group: {group}, subgroup: {key} has non-integer input."
                    )
                if any([x in fip_regions_used for x in fip_regions]):
                    raise ValueError(
                        f"FIP: {fip}, group: {group} has input which is not unique."
                        f"Same value is used for multiple subgroups."
                    )
                fip_regions_used.update(fip_regions)
                group_dict.update({key: fip_regions})
            formatted_dict[fip].update({str(group): group_dict})
    return formatted_dict, fipname_dict
