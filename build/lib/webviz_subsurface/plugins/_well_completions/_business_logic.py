import io
import itertools
import json
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import numpy as np
import pandas as pd
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from ..._datainput.fmu_input import load_csv
from ..._datainput.well_completions import (
    get_ecl_unit_system,
    read_stratigraphy,
    read_well_attributes,
    read_well_connection_status,
    read_zone_layer_mapping,
)


class WellCompletionsDataModel:
    def __init__(
        self,
        ensemble_name: str,
        ensemble_path: str,
        compdat_file: str,
        well_connection_status_file: str,
        zone_layer_mapping_file: str,
        stratigraphy_file: str,
        well_attributes_file: str,
        kh_unit: Optional[str],
        kh_decimal_places: int,
        theme_colors: List[str],
    ) -> None:
        # pylint: disable=too-many-arguments

        self.ensemble_name = ensemble_name
        self.ensemble_path = ensemble_path
        self.compdat_file = compdat_file
        self.well_connection_status_file = well_connection_status_file
        self.zone_layer_mapping_file = zone_layer_mapping_file
        self.stratigraphy_file = stratigraphy_file
        self.well_attributes_file = well_attributes_file
        self.kh_unit = kh_unit
        self.kh_decimal_places = kh_decimal_places
        self.theme_colors = theme_colors

    def __repr__(self) -> str:
        """This is necessary for webvizstore to work"""
        return f"""
WellCompletionsDataModel {self.ensemble_name} {self.ensemble_path} {self.compdat_file}
{self.well_connection_status_file} {self.zone_layer_mapping_file} {self.stratigraphy_file}
{self.well_attributes_file}
        """

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    @webvizstore
    def create_ensemble_dataset(self) -> io.BytesIO:
        """Creates the well completion data set for the WellCompletions component

        Returns a dictionary on a given format specified here:
        https://github.com/equinor/webviz-subsurface-components/blob/master/react/src/lib/inputSchema/wellCompletions.json
        """
        df = load_csv(
            ensemble_paths={self.ensemble_name: self.ensemble_path},
            csv_file=self.compdat_file,
        )
        df = df[["REAL", "DATE", "WELL", "I", "J", "K1", "OP/SH", "KH"]]
        df.DATE = pd.to_datetime(df.DATE).dt.date

        df_connstatus = read_well_connection_status(
            ensemble_path=self.ensemble_path,
            well_connection_status_file=self.well_connection_status_file,
        )
        df_zone_layer = read_zone_layer_mapping(
            ensemble_path=self.ensemble_path,
            zone_layer_mapping_file=self.zone_layer_mapping_file,
        )
        stratigraphy = read_stratigraphy(
            ensemble_path=self.ensemble_path, stratigraphy_file=self.stratigraphy_file
        )
        well_attributes = read_well_attributes(
            ensemble_path=self.ensemble_path,
            well_attributes_file=self.well_attributes_file,
        )
        if self.kh_unit is None:
            self.kh_unit, self.kh_decimal_places = get_kh_unit(
                ensemble_path=self.ensemble_path
            )

        if df_connstatus is not None:
            df = merge_compdat_and_connstatus(df, df_connstatus)

        time_steps = sorted(df.DATE.unique())
        realizations = list(sorted(df.REAL.unique()))

        if df_zone_layer.empty:
            if stratigraphy is None:
                df["ZONE"] = df.agg(lambda x: f"Layer {x['K1']}", axis=1)
                df["COLOR"] = np.nan
            else:
                raise ValueError(
                    "It is not permitted to define the stratigraphy, but not the "
                    "zone ➔ layer mapping. If neither input is provided then layers "
                    "will be used as zones (NB! this can be slow with many wells and realizations)"
                )
        else:
            reals_without_mapping = set(df["REAL"].unique()) - set(
                df_zone_layer["REAL"].unique()
            )
            if reals_without_mapping:
                raise ValueError(
                    "The zone ➔ layer mapping seems to be missing for the "
                    f"following realizations: {reals_without_mapping}"
                )

            # We know that all realizations has a zone layer mapping, but we do
            # not require that all layers are defined in the zone layer mapping.
            # Layers missing from the zone layer mapping will be filtered out here.
            df = df.merge(df_zone_layer, on=["K1", "REAL"], how="inner")

        # Get the zone names in the correct order
        zone_names = (
            df.drop_duplicates(subset=["K1", "ZONE"])
            .sort_values(by="K1")["ZONE"]
            .unique()
        )

        zone_color_mapping = {
            item["ZONE"]: item["COLOR"]
            for item in df[["ZONE", "COLOR"]]
            .dropna()
            .drop_duplicates(keep="first")
            .to_dict("records")
        }

        result = {
            "version": "1.1.0",
            "units": {
                "kh": {"unit": self.kh_unit, "decimalPlaces": self.kh_decimal_places}
            },
            "stratigraphy": extract_stratigraphy(
                zone_names, stratigraphy, zone_color_mapping, self.theme_colors
            ),
            "timeSteps": [str(dte) for dte in time_steps],
            "wells": extract_wells(
                df, zone_names, time_steps, realizations, well_attributes
            ),
        }
        return io.BytesIO(json.dumps(result).encode())

    @property
    def webviz_store(self) -> Tuple[Callable, List[Dict]]:
        return (
            self.create_ensemble_dataset,
            [
                {
                    "self": self,
                }
            ],
        )


def merge_compdat_and_connstatus(
    df_compdat: pd.DataFrame, df_connstatus: pd.DataFrame
) -> pd.DataFrame:
    """This function merges the compdat data (exported with ecl2df) with the well connection
    status data (extracted from the CPI summary data). The connection status data will
    be used for wells where it exists. The KH will be merged from the compdat. For wells
    that are not in the connection status data, the compdat data will be used as it is.

    This approach is fast, but a couple of things should be noted:
    * in the connection status data, a connection is not set to SHUT before it has been OPEN. \
    In the compdat data, some times all connections are first defined and the opened later.
    * any connections that are in compdat but not in connections status will be ignored \
    (e.g. connections that are always shut)
    * there is no logic to handle KH changing with time for the same connection (this \
    can easily be added using apply in pandas, but it is very rare and slows down the function
    significantly)
    * if connection status is missing for a realization, but compdat exists, compdat will also \
    be ignored.
    """
    match_on = ["REAL", "WELL", "I", "J", "K1"]
    df = pd.merge(df_connstatus, df_compdat[match_on + ["KH"]], on=match_on, how="left")

    # There will often be several rows (with different OP/SH) matching in compdat.
    # Only the first is kept
    df.drop_duplicates(subset=["DATE"] + match_on, keep="first", inplace=True)

    # Concat from compdat the wells that are not in well connection status
    df = pd.concat([df, df_compdat[~df_compdat.WELL.isin(df.WELL.unique())]])

    df = df.reset_index(drop=True)
    df.KH = df.KH.fillna(0)
    return df


def get_kh_unit(ensemble_path: str) -> Tuple[str, int]:
    """Returns kh unit and decimal places based on the unit system of the eclipse deck"""
    units = {
        "METRIC": ("mD·m", 2),
        "FIELD": ("mD·ft", 2),
        "LAB": ("mD·cm", 2),
        "PVT-M": ("mD·m", 2),
    }
    unit_system = get_ecl_unit_system(ensemble_path=ensemble_path)
    if unit_system is not None:
        return units[unit_system]
    return ("", 2)


def get_time_series(df: pd.DataFrame, time_steps: list) -> tuple:
    """Create two lists with values for each time step
    * the first one is on the form [0,0,0,1,1,1,1,-1,-1,-1] where '0' means no event,\
    '1' is open, '-1' is shut.
    * the second is with sum of kh values for the open compdats in each zone

    The input data frame is assumed to contain data for single well,
    single zone and single realization.
    """
    if df.empty:
        return [0] * len(time_steps), [0] * len(time_steps)

    events, kh_values = [], []
    event_value, kh_value = 0, 0
    unique_dates = df.DATE.unique()

    for timestep in time_steps:
        if timestep in unique_dates:
            df_timestep = df[df.DATE == timestep]
            df_timestep_open = df_timestep[df_timestep["OP/SH"] == "OPEN"]

            # if minimum one of the compdats for the zone is OPEN then the zone is considered open
            event_value = 1 if not df_timestep_open.empty else -1
            kh_value = df_timestep_open.KH.sum()

        events.append(event_value)
        kh_values.append(kh_value)
    return events, kh_values


def get_completion_events_and_kh(
    df: pd.DataFrame, zone_names: list, time_steps: list
) -> tuple:
    """Extracts completion events ad kh values into two lists of lists of lists,
    one with completions events and one with kh values
    * Axis 0 is realization
    * Axis 1 is zone
    * Axis 2 is time step
    """
    compl_events, kh_values = [], []
    for _, realdata in df.groupby("REAL"):
        compl_events_real, kh_real = [], []
        for zone_name in zone_names:
            zone_data = realdata[realdata.ZONE == zone_name]
            compl_events_real_zone, kh_real_zone = get_time_series(
                zone_data, time_steps
            )
            compl_events_real.append(compl_events_real_zone)
            kh_real.append(kh_real_zone)

        compl_events.append(compl_events_real)
        kh_values.append(kh_real)
    return compl_events, kh_values


def format_time_series(
    open_frac: List[float],
    shut_frac: List[float],
    kh_mean: List[float],
    kh_min: List[float],
    kh_max: List[float],
) -> Optional[Dict]:
    """The functions takes in five lists with values per timestep
    * fractions of realizations open in this zone
    * fractions of realizations shut in this zone
    * kh mean over open realizations
    * kh min over open realizations
    * kh max over open realizations

    Returns the data in compact form:
    {
        t: [3, 5],
        open: [0.25, 1.0],
        shut: [0.75, 0.0],
        khMean: [500, 1000],
        khMin: [200, 800],
        khMean: [600, 1500]
    }
    """
    output: Dict[str, list] = {
        "t": [],
        "open": [],
        "shut": [],
        "khMean": [],
        "khMin": [],
        "khMax": [],
    }
    prev_open_val = prev_shut_val = 0.0

    for i, _ in enumerate(open_frac):
        open_val = open_frac[i]
        shut_val = shut_frac[i]
        if open_val != prev_open_val or shut_val != prev_shut_val:
            output["t"].append(i)
            output["open"].append(open_val)
            output["shut"].append(shut_val)
            output["khMean"].append(kh_mean[i])
            output["khMin"].append(kh_min[i])
            output["khMax"].append(kh_max[i])
        prev_open_val = open_val
        prev_shut_val = shut_val
    return output


def calc_over_realizations(
    compl_events: list, kh_values: list, realizations: list
) -> tuple:
    """Takes in two three dimensional lists where the levels are: 1. realization \
    2. zones and 3. timesteps

    Returns two dimensional lists where calculations have been done over the \
    realization level.
    """
    # calculate fraction of open realizations
    open_count = np.maximum(np.asarray(compl_events), 0)  # remove -1
    open_count_reduced = open_count.sum(axis=0)  # sum over realizations
    open_frac = (
        np.asarray(open_count_reduced, dtype=np.float64) / float(len(realizations))
    ).round(decimals=3)

    # calculate fraction of shut realizations
    shut_count = (
        np.minimum(np.asarray(compl_events), 0) * -1
    )  # remove +1 and convert -1 to 1
    shut_count_reduced = shut_count.sum(axis=0)  # sum over realizations
    shut_frac = (
        np.asarray(shut_count_reduced, dtype=np.float64) / float(len(realizations))
    ).round(decimals=3)

    # calculate khMean, khMin and khMax
    np_kh_values = np.asarray(kh_values)
    kh_mean = (np_kh_values.sum(axis=0) / float(len(realizations))).round(decimals=2)
    kh_min = np_kh_values.min(axis=0).round(decimals=2)
    kh_max = np_kh_values.max(axis=0).round(decimals=2)

    return open_frac, shut_frac, kh_mean, kh_min, kh_max


def extract_well(
    df: pd.DataFrame, well: str, zone_names: list, time_steps: list, realizations: list
) -> Dict[str, Any]:
    # pylint: disable=too-many-locals
    """Extract completion events and kh values for a single well"""
    well_dict: Dict[str, Any] = {}
    well_dict["name"] = well

    compl_events, kh_values = get_completion_events_and_kh(df, zone_names, time_steps)
    open_frac, shut_frac, kh_mean, kh_min, kh_max = calc_over_realizations(
        compl_events, kh_values, realizations
    )
    result = {}
    for (
        zone_name,
        open_frac_zone,
        shut_frac_zone,
        kh_mean_zone,
        kh_min_zone,
        kh_max_zone,
    ) in zip(zone_names, open_frac, shut_frac, kh_mean, kh_min, kh_max):
        if sum(open_frac_zone) != 0.0 or sum(shut_frac_zone) != 0.0:
            result[zone_name] = format_time_series(
                open_frac_zone, shut_frac_zone, kh_mean_zone, kh_min_zone, kh_max_zone
            )
    well_dict["completions"] = result
    return well_dict


def extract_wells(
    df: pd.DataFrame,
    zone_names: list,
    time_steps: list,
    realizations: list,
    well_attributes: Optional[dict],
) -> List[Dict]:
    """Generates the wells part of the input dictionary to the WellCompletions component"""
    well_list = []
    for well_name, well_group in df.groupby("WELL"):
        well_data = extract_well(
            well_group, well_name, zone_names, time_steps, realizations
        )
        well_data["attributes"] = (
            well_attributes[well_name]
            if (well_attributes is not None and well_name in well_attributes)
            else {}
        )
        well_list.append(well_data)
    return well_list


def add_colors_to_stratigraphy(
    stratigraphy: List[Dict[str, Any]],
    zone_color_mapping: Optional[Dict[str, str]],
    color_iterator: Iterator,
) -> List[Dict[str, Any]]:
    """Add colors to the stratigraphy tree. The function will recursively parse the tree.

    There are tree sources of color:
    1. The color is given in the stratigraphy list, in which case nothing is done to the node
    2. The color is given in the lyr file, and passed to this function in the zone->color map
    3. If none of the above applies, the color will be taken from the theme color iterable for \
    the leaves. For other levels, a dummy color grey is used
    """
    for zonedict in stratigraphy:
        if "color" not in zonedict:
            if (
                zone_color_mapping is not None
                and zonedict["name"] in zone_color_mapping
            ):
                zonedict["color"] = zone_color_mapping[zonedict["name"]]
            elif "subzones" not in zonedict:
                zonedict["color"] = next(
                    color_iterator
                )  # theme colors only applied on leaves
            else:
                zonedict["color"] = "#808080"  # grey
        if "subzones" in zonedict:
            zonedict["subzones"] = add_colors_to_stratigraphy(
                zonedict["subzones"], zone_color_mapping, color_iterator
            )
    return stratigraphy


def filter_valid_nodes(
    stratigraphy: List[Dict[str, Any]], valid_zone_names: list
) -> Tuple[List, List]:
    """Returns the stratigraphy tree with only valid nodes.
    A node is considered valid if it self or one of it's subzones are in the
    valid zone names list (passed from the lyr file)

    The function recursively parses the tree to add valid nodes.
    """
    output = []
    remaining_valid_zones = valid_zone_names
    for zonedict in stratigraphy:
        if "subzones" in zonedict:
            zonedict["subzones"], remaining_valid_zones = filter_valid_nodes(
                zonedict["subzones"], remaining_valid_zones
            )
        if zonedict["name"] in remaining_valid_zones:
            if "subzones" in zonedict and not zonedict["subzones"]:
                zonedict.pop("subzones")
            output.append(zonedict)
            remaining_valid_zones = [
                zone for zone in remaining_valid_zones if zone != zonedict["name"]
            ]  # remove zone name from valid zones if it is found in the stratigraphy
        elif "subzones" in zonedict and zonedict["subzones"]:
            output.append(zonedict)

    return output, remaining_valid_zones


def extract_stratigraphy(
    zone_names: List[str],
    stratigraphy: Optional[List[Dict[str, Any]]],
    zone_color_mapping: Optional[Dict[str, str]],
    theme_colors: list,
) -> List[Dict[str, Any]]:
    """Returns the stratigraphy part of the data set"""
    color_iterator = itertools.cycle(theme_colors)

    if stratigraphy is None:
        return [
            {
                "name": zone,
                "color": zone_color_mapping[zone]
                if zone_color_mapping is not None and zone in zone_color_mapping
                else next(color_iterator),
            }
            for zone in zone_names
        ]

    # If stratigraphy is not None the following is done:
    stratigraphy, remaining_valid_zones = filter_valid_nodes(stratigraphy, zone_names)

    if remaining_valid_zones:
        raise ValueError(
            "The following zones are defined in the zone ➔ layer mapping, "
            f"but not in the stratigraphy: {remaining_valid_zones}"
        )

    # Zones not found in the stratigraphy is added to the end.
    for zone_name in remaining_valid_zones:
        stratigraphy.append({"name": zone_name})

    return add_colors_to_stratigraphy(stratigraphy, zone_color_mapping, color_iterator)
