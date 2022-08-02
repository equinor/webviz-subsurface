import glob
import logging
import re
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
from webviz_config.webviz_store import webvizstore


# -------------------------------
@webvizstore
# pylint: disable=too-many-locals
def makedf(
    ensemble_set: dict,
    attribute_name: str,
    attribute_sim_path: str,
    attribute_obs_path: str,
    obs_mult: float,
    sim_mult: float,
    realrange: Optional[List[List[int]]],
) -> pd.DataFrame:
    """Create dataframe of obs, meta and sim data for all ensembles.
    Uses the functions 'makedf_seis_obs_meta' and 'makedf_seis_addsim'."""

    meta_name = "meta--" + attribute_name
    dfs = []
    dfs_obs = []
    ens_count = 0
    for ens_name, ens_path in ensemble_set.items():
        logging.info(
            f"Working with ensemble name {ens_name}:\nRunpath: {ens_path}"
            f"\nAttribute name: {attribute_name}"
        )

        # grab runpath for one realization and locate obs/meta data relative to it
        single_runpath = sorted(glob.glob(ens_path))[0]
        obsfile = Path(single_runpath) / Path(attribute_obs_path) / meta_name

        df = makedf_seis_obs_meta(obsfile, obs_mult=obs_mult)

        df["ENSEMBLE"] = ens_name  # add ENSEMBLE column
        dfs_obs.append(df.copy())

        # --- add sim data ---
        fromreal, toreal = 0, 999
        if realrange is not None:
            if len(realrange[ens_count]) == 2:
                fromreal = int(realrange[ens_count][0])
                toreal = int(realrange[ens_count][1])
            else:
                raise RuntimeError(
                    "Error in "
                    + makedf.__name__
                    + "\nrealrange input is assigned wrongly (in yaml config file).\n"
                    "Make sure to add 2 integers in square brackets "
                    "for each of the ensembles. Alternatively, remove this optional "
                    "argument to use default settings (all realizations included)."
                )

        df = makedf_seis_addsim(
            df,
            ens_path,
            attribute_name,
            attribute_sim_path,
            fromreal=fromreal,
            toreal=toreal,
            sim_mult=sim_mult,
        )
        dfs.append(df)

        ens_count += 1

    return pd.concat(dfs)  # , pd.concat(dfs_obs)


# -------------------------------
def makedf_seis_obs_meta(
    obsfile: Path,
    obs_mult: float = 1.0,
) -> pd.DataFrame:
    """Make a dataframe of obsdata and metadata.
    (obs data multiplier: optional, default is 1.0")
    """
    # --- read obsfile into pandas dataframe ---
    df = pd.read_csv(obsfile)
    dframe = df.copy()  # make a copy to avoid strange pylint errors
    # for info: https://github.com/PyCQA/pylint/issues/4577
    dframe.columns = dframe.columns.str.lower()  # convert all headers to lower case
    logging.debug(
        f"Obs file: {obsfile} \n--> Number of seismic data points: {len(dframe)}"
    )
    tot_nan_val = dframe.isnull().sum().sum()  # count all nan values
    if tot_nan_val > 0:
        logging.warning(f"{obsfile} contains {tot_nan_val} NaN values")

    if "obs" not in dframe.columns:
        raise RuntimeError(f"'obs' column not included in {obsfile}")

    if "obs_error" not in dframe.columns:
        raise RuntimeError(f"'obs_error' column not included in {obsfile}")

    if "east" not in dframe.columns:
        if "x_utme" in dframe.columns:
            dframe.rename(columns={"x_utme": "east"}, inplace=True)
            logging.debug("renamed x_utme column to east")
        else:
            raise RuntimeError("'x_utm' (or 'east') column not included in meta data")

    if "north" not in dframe.columns:
        if "y_utmn" in dframe.columns:
            dframe.rename(columns={"y_utmn": "north"}, inplace=True)
            logging.debug("renamed y_utmn column to north")
        else:
            raise RuntimeError("'y_utm' (or 'north') column not included in meta data")

    if "region" not in dframe.columns:
        if "regions" in dframe.columns:
            dframe.rename(columns={"regions": "region"}, inplace=True)
            logging.debug("renamed regions column to region")
        else:
            raise RuntimeError(
                "'Region' column is not included in meta data"
                "Please check your yaml config file settings and/or the metadata file."
            )

    # --- apply obs multiplier ---
    dframe["obs"] = dframe["obs"] * obs_mult
    dframe["obs_error"] = dframe["obs_error"] * obs_mult

    # redefine to int if region numbers in metafile is float
    if dframe.region.dtype == "float64":
        dframe = dframe.astype({"region": "int64"})

    dframe["data_number"] = dframe.index + 1  # add a simple counter

    return dframe


# pylint: disable=too-many-locals
def makedf_seis_addsim(
    df: pd.DataFrame,
    ens_path: str,
    attribute_name: str,
    attribute_sim_path: str,
    fromreal: int = 0,
    toreal: int = 99,
    sim_mult: float = 1.0,
) -> pd.DataFrame:
    """Make a merged dataframe of obsdata/metadata and simdata."""

    data_found, no_data_found = [], []
    real_path = {}
    obs_size = len(df.index)

    runpaths = glob.glob(ens_path)
    if len(runpaths) == 0:
        logging.warning(f"No realizations was found, wrong input?: {ens_path}")
        return pd.DataFrame()

    for runpath in runpaths:
        realno = int(re.search(r"(?<=realization-)\d+", runpath).group(0))  # type: ignore
        real_path[realno] = runpath

    sim_df_list = [df]
    for real in sorted(real_path.keys()):
        if fromreal <= real <= toreal:

            simfile = (
                Path(real_path[real]) / Path(attribute_sim_path) / Path(attribute_name)
            )
            if simfile.exists():
                # ---read sim data and apply sim multiplier ---
                colname = "real-" + str(real)
                sim_df = pd.read_csv(simfile, header=None, names=[colname]) * sim_mult
                if len(sim_df.index) != obs_size:
                    raise RuntimeError(
                        f"---\nThe length of {simfile} is {len(sim_df.index)} which is "
                        f"different to the obs data which has {obs_size} data points. "
                        "These must be the same size.\n---"
                    )
                sim_df_list.append(sim_df)
                data_found.append(real)
            else:
                no_data_found.append(real)
                logging.debug(f"File does not exist: {str(simfile)}")
    df_addsim = pd.concat(sim_df_list, axis=1)

    if len(data_found) == 0:
        logging.warning(
            f"{ens_path}/{attribute_sim_path}: no sim data found for {attribute_name}"
        )
    else:
        logging.debug(f"Sim values added to dataframe for realizations: {data_found}")
    if len(no_data_found) == 0:
        logging.debug("OK. Found data for all realizations")
    else:
        logging.debug(f"No data found for realizations: {no_data_found}")

    return df_addsim


# pylint: disable=too-many-locals
def df_seis_ens_stat(
    df: pd.DataFrame, ens_name: str, obs_error_weight: bool = False
) -> pd.DataFrame:
    """Make a dataframe with ensemble statistics per datapoint across all realizations.
    Calculate for both sim and diff values. Return with obs/meta data included.
    Return empty dataframe if no realizations included in df."""

    # --- make dataframe with obs and meta data only
    column_names = df.columns.values.tolist()
    x = [name for name in column_names if not name.startswith("real-")]
    start, end = x[0], x[-1]
    df_obs_meta = df.loc[:, start:end]

    # --- make dataframe with real- columns only
    column_names = df.columns.values.tolist()
    x = [name for name in column_names if name.startswith("real-")]
    if len(x) > 0:
        start, end = x[0], x[-1]
        df_sim = df.loc[:, start:end]
    else:
        logging.info(f"{ens_name}: no data found for selected realizations.")
        return pd.DataFrame()

    # --- calculate absolute diff, (|sim - obs| / obs_error), and store in new df
    df_diff = pd.DataFrame()
    for col in df.columns:
        if col.startswith("real-"):
            df_diff[col] = abs(df[col] - df["obs"])
            if obs_error_weight:
                df_diff[col] = df_diff[col] / df["obs_error"]  # divide by obs error

    # --- ensemble statistics of sim and diff for each data point ----
    # --- calculate statistics per row (data point)
    sim_mean = df_sim.mean(axis=1)
    sim_std = df_sim.std(axis=1)
    sim_p90 = df_sim.quantile(q=0.1, axis=1)
    sim_p10 = df_sim.quantile(q=0.9, axis=1)
    sim_min = df_sim.min(axis=1)
    sim_max = df_sim.max(axis=1)
    diff_mean = df_diff.mean(axis=1)
    diff_std = df_diff.std(axis=1)

    df_stat = pd.DataFrame(
        data={
            "sim_mean": sim_mean,
            "sim_std": sim_std,
            "sim_p90": sim_p90,
            "sim_p10": sim_p10,
            "sim_min": sim_min,
            "sim_max": sim_max,
            "diff_mean": diff_mean,
            "diff_std": diff_std,
        }
    )

    # --- add obsdata and metadata to the dataframe
    df_stat = pd.concat([df_stat, df_obs_meta], axis=1, sort=False)

    # Create coverage parameter
    # •	Values between 0 and 1 = coverage
    # •	Values above 1 = all sim values lower than obs values
    # •	Values below 0 = all sim values higher than obs values

    # (obs-min)/(max-min)
    df_stat["sim_coverage"] = (df_stat.obs - df_stat.sim_min) / (
        df_stat.sim_max - df_stat.sim_min
    )
    # obs_error adjusted: (obs-min)/(obs_error+max-min)
    df_stat["sim_coverage_adj"] = (df_stat.obs - df_stat.sim_min) / (
        df_stat.obs_error + df_stat.sim_max - df_stat.sim_min
    )
    # force to zero if diff smaller than obs_error, but keep values already in range(0,1)
    # (this removes dilemma of small negative values showing up as overmodelled)
    df_stat["sim_coverage_adj"] = np.where(
        (
            ((df_stat.sim_coverage_adj > 0) & (df_stat.sim_coverage_adj < 1))
            | (
                (abs(df_stat.obs - df_stat.sim_min) > df_stat.obs_error)
                & (abs(df_stat.obs - df_stat.sim_max) > df_stat.obs_error)
            )
        ),
        df_stat.sim_coverage_adj,
        0,
    )

    return df_stat


@webvizstore
def make_polygon_df(ensemble_set: dict, polygon: str) -> pd.DataFrame:
    """Read polygon file. If there are one polygon file
    per realization only one will be read (first found)"""

    df_polygon: pd.DataFrame = pd.DataFrame()
    df_polygons: pd.DataFrame = pd.DataFrame()
    for _, ens_path in ensemble_set.items():
        for single_runpath in sorted(glob.glob(ens_path)):
            poly = Path(single_runpath) / Path(polygon)
            if poly.is_dir():  # grab all csv files in folder
                poly_files = glob.glob(str(poly) + "/*csv")
            else:
                poly_files = glob.glob(str(poly))

            if not poly_files:
                logging.debug(f"No polygon files found in '{poly}'")
            else:
                for poly_file in poly_files:
                    logging.debug(f"Read polygon file:\n {poly_file}")
                    df_polygon = pd.read_csv(poly_file)
                    cols = df_polygon.columns

                    if ("ID" in cols) and ("X" in cols) and ("Y" in cols):
                        df_polygon = df_polygon[["X", "Y", "ID"]]
                    elif (
                        ("POLY_ID" in cols)
                        and ("X_UTME" in cols)
                        and ("Y_UTMN" in cols)
                    ):
                        df_polygon = df_polygon[["X_UTME", "Y_UTMN", "POLY_ID"]].rename(
                            columns={"X_UTME": "X", "Y_UTMN": "Y", "POLY_ID": "ID"}
                        )
                        logging.warning(
                            "For the future, consider using X,Y,Z,ID as header names in "
                            "the polygon files, as this is regarded as the FMU standard."
                            f"The {poly_file} file uses X_UTME,Y_UTMN,POLY_ID."
                        )
                    else:
                        logging.warning(
                            f"The polygon file {poly_file} does not have an expected "
                            "format and is therefore skipped. The file must either "
                            "contain the columns 'POLY_ID', 'X_UTME' and 'Y_UTMN' or "
                            "the columns 'ID', 'X' and 'Y'."
                        )
                        continue

                    df_polygon["name"] = str(Path(poly_file).stem).replace("_", " ")
                    df_polygons = pd.concat([df_polygons, df_polygon])

                logging.debug(f"Polygon dataframe:\n{df_polygons}")
                return df_polygons

        if df_polygons.empty():
            raise RuntimeError(
                "Error in "
                + str(make_polygon_df.__name__)
                + ". Could not find polygon files with a valid format."
                f" Please update the polygon argument '{polygon}' in "
                "the config file (default is None) or edit the files in the "
                "list. The polygon files must contain the columns "
                "'POLY_ID', 'X_UTME' and 'Y_UTMN' "
                "(the column names must match exactly)."
            )

    logging.debug("Polygon file not assigned - continue without.")
    return df_polygons
