########################################
#
#  Copyright (C) 2020-     Equinor ASA
#
########################################

import sys
from typing import Dict, List, Any
import warnings

import pandas as pd

# opm and ecl2df are only available for Linux,
# hence, ignore any import exception here to make
# it still possible to use the PvtPlugin on
# machines with other OSes.
#
# NOTE: Functions in this file cannot be used
#       on non-Linux OSes.
try:
    import ecl2df
    from opm.io.ecl import EclFile
except ImportError:
    pass

from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from .opm_init_io import (
    Oil,
    Gas,
    Water,
    DryGas,
    WetGas,
    LiveOil,
    DeadOil,
    VariateAndValues,
)
from .fmu_input import load_ensemble_set, load_csv


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def filter_pvt_data_frame(
    data_frame: pd.DataFrame, drop_ensemble_duplicates: bool = False
) -> pd.DataFrame:

    data_frame = data_frame.rename(str.upper, axis="columns").rename(
        columns={
            "TYPE": "KEYWORD",
            "RS": "GOR",
            "RSO": "GOR",
            "R": "GOR",
            "RV": "OGR",
        }
    )
    data_frame = data_frame.fillna(0)
    if "GOR" in data_frame.columns and "OGR" in data_frame.columns:
        data_frame["RATIO"] = data_frame["GOR"] + data_frame["OGR"]
    elif "GOR" in data_frame.columns:
        data_frame["RATIO"] = data_frame["GOR"]
    elif "OGR" in data_frame.columns:
        data_frame["RATIO"] = data_frame["OGR"]

    columns = [
        "ENSEMBLE",
        "REAL",
        "PVTNUM",
        "KEYWORD",
        "RATIO",
        "PRESSURE",
        "VOLUMEFACTOR",
        "VISCOSITY",
    ]

    if not "RATIO" in data_frame.columns:
        raise ValueError(
            "The dataframe must contain a column for the ratio (OGR, GOR, R, RV, RS)."
        )

    data_frame = data_frame[columns]

    stored_data_frames: List[pd.DataFrame] = []
    cleaned_data_frame = data_frame.iloc[0:0]
    columns_subset = data_frame.columns.difference(["REAL", "ENSEMBLE"])

    for ens, ens_data_frame in data_frame.groupby("ENSEMBLE"):
        ens_merged_dataframe = data_frame.iloc[0:0]
        for _rno, realization_data_frame in ens_data_frame.groupby("REAL"):
            if ens_merged_dataframe.empty:
                ens_merged_dataframe = ens_merged_dataframe.append(
                    realization_data_frame
                ).reset_index(drop=True)
            else:
                ens_merged_dataframe = (
                    pd.concat([ens_merged_dataframe, realization_data_frame])
                    .drop_duplicates(
                        subset=columns_subset,
                        keep="first",
                    )
                    .reset_index(drop=True)
                )

        if ens_merged_dataframe["REAL"].nunique() > 1:
            warnings.warn(
                (
                    f"There are variations in PVT between realizations in ensemble {ens}. "
                    "This is currently not supported. Only keeping data for realization "
                    f"{ens_merged_dataframe['REAL'].iloc[0]}."
                ),
                UserWarning,
            )
            ens_merged_dataframe = ens_merged_dataframe[
                ens_merged_dataframe["REAL"] == ens_merged_dataframe["REAL"].iloc[0]
            ]
        if drop_ensemble_duplicates:
            data_frame_stored = False
            for stored_data_frame in stored_data_frames:
                if all(
                    stored_data_frame[columns_subset]
                    == ens_merged_dataframe[columns_subset]
                ):
                    data_frame_stored = True
                    break
            if data_frame_stored:
                continue
            stored_data_frames.append(ens_merged_dataframe)
        cleaned_data_frame = cleaned_data_frame.append(ens_merged_dataframe)

    return cleaned_data_frame


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def load_pvt_csv(
    ensemble_paths: dict,
    csv_file: str,
    ensemble_set_name: str = "EnsembleSet",
    drop_ensemble_duplicates: bool = False,
) -> pd.DataFrame:
    return filter_pvt_data_frame(
        load_csv(ensemble_paths, csv_file, ensemble_set_name), drop_ensemble_duplicates
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def load_pvt_dataframe(
    ensemble_paths: Dict[str, str],
    ensemble_set_name: str = "EnsembleSet",
    use_init_file: bool = False,
    drop_ensemble_duplicates: bool = False,
) -> pd.DataFrame:
    # pylint: disable=too-many-statements
    # If ecl2df is not loaded, this machine is probably not
    # running Linux and the modules are not available.
    # To avoid a crash, return an empty DataFrame here.
    if "ecl2df" not in sys.modules:
        print(
            "Your operating system does not support opening and reading"
            " Eclipse files. An empty data frame will be returned and your"
            " plot will therefore not show any data points. Please specify"
            " a relative path to a PVT CSV file in your PvtPlot settings"
            " to display PVT data anyways."
        )
        return pd.DataFrame({})

    def ecl2df_pvt_data_frame(kwargs: Any) -> pd.DataFrame:
        return ecl2df.pvt.df(kwargs["realization"].get_eclfiles())

    def init_to_pvt_data_frame(kwargs: Any) -> pd.DataFrame:
        # pylint: disable-msg=too-many-locals
        # pylint: disable=too-many-nested-blocks
        # pylint: disable=too-many-branches
        ecl_init_file = EclFile(
            kwargs["realization"].get_eclfiles().get_initfile().get_filename()
        )

        oil = Oil.from_ecl_init_file(ecl_init_file)
        gas = Gas.from_ecl_init_file(ecl_init_file)
        water = Water.from_ecl_init_file(ecl_init_file)

        column_pvtnum = []
        column_oil_gas_ratio = []
        column_volume_factor = []
        column_pressure = []
        column_viscosity = []
        column_keyword = []

        if oil:
            if len(oil.tables()) > 0 and isinstance(oil.tables()[0], LiveOil):
                keyword = "PVTO"
            elif len(oil.tables()) > 0 and isinstance(oil.tables()[0], DeadOil):
                keyword = "PVDO"
            else:
                raise NotImplementedError(
                    f"Oil of type '{type(oil)}' is not supported yet."
                )

            for table_index, table in enumerate(oil.tables()):
                for outer_pair in table.get_values():
                    for inner_pair in outer_pair.y:
                        if isinstance(inner_pair, VariateAndValues):
                            column_pvtnum.append(table_index + 1)
                            column_keyword.append(keyword)
                            if isinstance(table, DeadOil):
                                column_oil_gas_ratio.append(0.0)
                            else:
                                column_oil_gas_ratio.append(outer_pair.x)
                            column_pressure.append(inner_pair.x)
                            column_volume_factor.append(
                                1.0 / inner_pair.get_values_as_floats()[0]
                            )
                            column_viscosity.append(
                                inner_pair.get_values_as_floats()[0]
                                / inner_pair.get_values_as_floats()[1]
                            )

        if gas:
            if len(gas.tables()) > 0 and isinstance(gas.tables()[0], DryGas):
                keyword = "PVDG"
            elif len(gas.tables()) > 0 and isinstance(gas.tables()[0], WetGas):
                keyword = "PVTG"
            else:
                raise NotImplementedError(
                    f"Gas of type '{type(gas)}' is not supported yet."
                )
            for table_index, table in enumerate(gas.tables()):
                for outer_pair in table.get_values():
                    for inner_pair in outer_pair.y:
                        if isinstance(inner_pair, VariateAndValues):
                            column_pvtnum.append(table_index + 1)
                            column_keyword.append(keyword)
                            if isinstance(table, DryGas):
                                column_oil_gas_ratio.append(0.0)
                                column_pressure.append(inner_pair.x)
                            else:
                                column_oil_gas_ratio.append(inner_pair.x)
                                column_pressure.append(outer_pair.x)
                            column_volume_factor.append(
                                1.0 / inner_pair.get_values_as_floats()[0]
                            )
                            column_viscosity.append(
                                inner_pair.get_values_as_floats()[0]
                                / inner_pair.get_values_as_floats()[1]
                            )
        if water:
            for table_index, table in enumerate(water.tables()):
                for outer_pair in table.get_values():
                    for inner_pair in outer_pair.y:
                        if isinstance(inner_pair, VariateAndValues):
                            column_pvtnum.append(table_index + 1)
                            column_keyword.append("PVTW")
                            column_oil_gas_ratio.append(outer_pair.x)
                            column_pressure.append(inner_pair.x)
                            column_volume_factor.append(
                                1.0 / inner_pair.get_values_as_floats()[0]
                            )
                            column_viscosity.append(
                                1.0
                                / inner_pair.get_values_as_floats()[2]
                                * inner_pair.get_values_as_floats()[0]
                            )

        data_frame = pd.DataFrame(
            {
                "PVTNUM": column_pvtnum,
                "KEYWORD": column_keyword,
                "R": column_oil_gas_ratio,
                "PRESSURE": column_pressure,
                "VOLUMEFACTOR": column_volume_factor,
                "VISCOSITY": column_viscosity,
            }
        )

        return data_frame

    return filter_pvt_data_frame(
        load_ensemble_set(ensemble_paths, ensemble_set_name).apply(
            init_to_pvt_data_frame if use_init_file else ecl2df_pvt_data_frame
        ),
        drop_ensemble_duplicates,
    )
