from typing import List, Optional, Dict, Any
from pathlib import Path

import numpy as np
import pandas as pd
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_subsurface._datainput.fmu_input import find_sens_type
from .ensemble_set_model import EnsembleSetModel


class InplaceVolumesModel:

    SENS_COLUMNS = [
        "ENSEMBLE",
        "REAL",
        "SENSCASE",
        "SENSNAME",
        "SENSTYPE",
    ]
    POSSIBLE_SELECTORS = [
        "FLUID",
        "SOURCE",
        "ENSEMBLE",
        "REAL",
        "ZONE",
        "REGION",
        "FACIES",
        "LICENSE",
        "SENSNAME",
        "SENSCASE",
        "SENSTYPE",
    ]

    def __init__(
        self,
        volumes_table: pd.DataFrame,
        parameter_table: Optional[pd.DataFrame] = None,
        drop_constants: bool = False,
    ):
        self._parameters: List[str] = []
        if parameter_table is not None:
            self._prepare_parameter_data(parameter_table, drop_constants=drop_constants)

        self._designrun = (
            parameter_table is not None and "SENSNAME" in parameter_table.columns
        )
        if self._designrun:
            parameter_table["SENSTYPE"] = parameter_table.apply(
                lambda row: find_sens_type(row.SENSCASE)
                if not pd.isnull(row.SENSCASE)
                else np.nan,
                axis=1,
            )
        self._sensrun = self._designrun and (
            parameter_table["SENSNAME"].nunique() > 1
            or (
                parameter_table["SENSNAME"].nunique() == 1
                and parameter_table["SENSTYPE"].unique() != ["mc"]
            )
        )

        sens_params_table = (
            parameter_table[self.SENS_COLUMNS] if self._designrun else None
        )

        # TO-DO add code for computing water volumes if "TOTAL" is present
        dfs = []
        for fluid in ["OIL", "GAS"]:
            selector_columns = [
                x for x in volumes_table.columns if x in self.POSSIBLE_SELECTORS
            ]
            fluid_columns = [x for x in volumes_table.columns if x.endswith(fluid)]
            if not fluid_columns:
                continue
            df = volumes_table[selector_columns + fluid_columns].copy()
            df.columns = df.columns.str.replace(f"_{fluid}", "")
            df["FLUID"] = fluid.lower()
            dfs.append(df)

        volumes_table = pd.concat(dfs)

        # Rename PORE to PORV (PORE will be deprecated..)
        if "PORE" in volumes_table:
            volumes_table.rename(columns={"PORE": "PORV"}, inplace=True)

        # Merge into one dataframe
        self._dataframe = (
            volumes_table
            if sens_params_table is None
            else pd.merge(volumes_table, sens_params_table, on=["ENSEMBLE", "REAL"])
        )

        if self._sensrun and self._dataframe["SENSNAME"].isnull().values.any():
            df = self._dataframe
            raise ValueError(
                "Ensembles with and without sensitivity data mixed - this is not supported \n"
                f"Sensitivity ensembles: {df.loc[~df['SENSNAME'].isnull()]['ENSEMBLE'].unique()} "
                f"Non-sensitivity ensembles: {df.loc[df['SENSNAME'].isnull()]['ENSEMBLE'].unique()}"
            )

        self.set_initial_property_columns()

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    @property
    def parameter_df(self) -> pd.DataFrame:
        return self._parameterdf

    @property
    def sensrun(self) -> bool:
        return self._sensrun

    @property
    def sources(self) -> List[str]:
        return sorted(list(self._dataframe["SOURCE"].unique()))

    @property
    def realizations(self) -> List[int]:
        return sorted(list(self._dataframe["REAL"].unique()))

    @property
    def ensembles(self) -> List[str]:
        return list(self._dataframe["ENSEMBLE"].unique())

    @property
    def property_columns(self) -> List[str]:
        return self._property_columns

    @property
    def volume_columns(self) -> List[str]:
        return [
            x
            for x in self._dataframe
            if x not in self.selectors and x not in self.property_columns
        ]

    @property
    def selectors(self) -> List[str]:
        return [x for x in self.POSSIBLE_SELECTORS if x in self._dataframe]

    @property
    def responses(self) -> List[str]:
        return self.volume_columns + self.property_columns

    @property
    def parameters(self) -> List[str]:
        return self._parameters

    def set_initial_property_columns(self) -> None:
        self._property_columns = []
        # if Net not given, Net is equal to Bulk
        net_column = "NET" if "NET" in self._dataframe else "BULK"

        if all(col in self._dataframe for col in ["NET", "BULK"]):
            self._property_columns.append("NTG")

        if all(col in self._dataframe for col in [net_column, "PORV"]):
            self._property_columns.append("PORO")

        if all(col in self._dataframe for col in ["HCPV", "PORV"]):
            self._property_columns.append("SW")

        for vol_column in ["STOIIP", "GIIP"]:
            if all(col in self._dataframe for col in ["HCPV", vol_column]):
                pvt = "BO" if vol_column == "STOIIP" else "BG"
                self._property_columns.append(pvt)

        self._dataframe = self.compute_property_columns(self._dataframe)

    def compute_property_columns(
        self, dframe: pd.DataFrame, properties: Optional[list] = None
    ) -> pd.DataFrame:

        properties = self.property_columns if properties is None else properties

        # if NTG not given Net is equal to bulk
        net_column = "NET" if "NET" in dframe.columns else "BULK"

        if "NTG" in properties:
            dframe["NTG"] = dframe[net_column] / dframe["BULK"]
        if "PORO" in properties:
            dframe["PORO"] = dframe["PORV"] / dframe[net_column]
        if "SW" in properties:
            dframe["SW"] = 1 - (dframe["HCPV"] / dframe["PORV"])
        if "BO" in properties:
            dframe["BO"] = dframe["HCPV"] / dframe["STOIIP"]
        if "BG" in properties:
            dframe["BG"] = dframe["HCPV"] / dframe["GIIP"]

        return dframe

    def _prepare_parameter_data(
        self, parameter_table: pd.DataFrame, drop_constants: bool
    ) -> None:
        """
        Different data preparations on the parameters, before storing them as an attribute.
        Option to drop parameters with constant values. Prefixes on parameters from GEN_KW
        are removed, in addition parameters with LOG distribution will be kept while the
        other is dropped.
        """

        parameter_table = parameter_table.reset_index(drop=True)

        if drop_constants:
            constant_params = [
                param
                for param in [
                    x for x in parameter_table.columns if x not in self.SENS_COLUMNS
                ]
                if len(parameter_table[param].unique()) == 1
            ]
            parameter_table = parameter_table.drop(columns=constant_params)

        # Keep only LOG parameters
        log_params = [
            param.replace("LOG10_", "")
            for param in [
                x for x in parameter_table.columns if x not in self.SENS_COLUMNS
            ]
            if param.startswith("LOG10_")
        ]
        parameter_table = parameter_table.drop(columns=log_params)

        parameter_table = parameter_table.rename(
            columns={
                col: f"{col} (log)"
                for col in parameter_table.columns
                if col.startswith("LOG10_")
            }
        )
        # Remove prefix on parameter name added by GEN_KW
        parameter_table = parameter_table.rename(
            columns={
                col: (col.split(":", 1)[1])
                for col in parameter_table.columns
                if (":" in col and col not in self.SENS_COLUMNS)
            }
        )

        # Drop columns if duplicate names
        parameter_table = parameter_table.loc[:, ~parameter_table.columns.duplicated()]

        self._parameterdf = parameter_table
        self._parameters = [
            x for x in parameter_table.columns if x not in self.SENS_COLUMNS
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def extract_volumes(
    ensemble_set_model: EnsembleSetModel, volfolder: str, volfiles: Dict[str, Any]
) -> pd.DataFrame:
    """Aggregates volumetric files from an FMU ensemble.
    Files must be stored on standardized csv format.
    """

    dfs = []
    for volname, volfile in volfiles.items():
        df = ensemble_set_model.load_csv(Path(volfolder) / volfile)
        df["SOURCE"] = volname
        dfs.append(df)

    if not dfs:
        raise ValueError(
            f"Error when aggregating inplace volumetric files: {list(volfiles)}. "
            f"Ensure that the files are present in relative folder {volfolder}"
        )
    return pd.concat(dfs)
