from typing import List, Optional, Dict
from pathlib import Path

import numpy as np
import pandas as pd
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_subsurface._datainput.fmu_input import find_sens_type

from webviz_subsurface._abbreviations.volume_terminology import (
    volume_description,
    volume_unit,
)


class InplaceVolumesModel:
    """Class to .."""

    SENS_COLUMNS = [
        "ENSEMBLE",
        "REAL",
        "SENSCASE",
        "SENSNAME",
        "SENSTYPE",
    ]

    POSSIBLE_SELECTORS = [
        "SOURCE",
        "ENSEMBLE",
        "REAL",
        "FLUID",
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
                and parameter_table["SENSTYPE"] != "mc"
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

        self.compute_property_columns()

    @property
    def dataframe(self) -> list:
        """Returns surface attributes"""
        return self._dataframe

    @property
    def parameter_df(self) -> list:
        """Returns surface attributes"""
        return self._parameterdf

    @property
    def sensrun(self) -> list:
        """Returns surface attributes"""
        return self._sensrun

    @property
    def sources(self) -> list:
        """Returns surface attributes"""
        return sorted(list(self._dataframe["SOURCE"].unique()))

    @property
    def realizations(self) -> list:
        """Returns surface attributes"""
        return sorted(list(self._dataframe["REAL"].unique()))

    @property
    def ensembles(self) -> list:
        """Returns surface attributes"""
        return list(self._dataframe["ENSEMBLE"].unique())

    @property
    def property_columns(self) -> List[str]:
        """List of all columns in dataframe"""
        return self._property_columns

    @property
    def volume_columns(self) -> List[str]:
        """List of all columns in dataframe"""
        return [
            x
            for x in self._dataframe
            if x not in self.selectors and x not in self.property_columns
        ]

    @property
    def selectors(self) -> List[str]:
        """List of available selector columns in dframe"""
        return [x for x in self.POSSIBLE_SELECTORS if x in self._dataframe]

    @property
    def responses(self) -> List[str]:
        """List of available volume responses in dframe"""
        return self.volume_columns + self.property_columns

    @property
    def parameters(self) -> List[str]:
        """List of available volume responses in dframe"""
        return self._parameters

    @property
    def aggregations(self) -> List[str]:
        aggregations = {x: "sum" for x in self.volume_columns}
        aggregations.update(
            {x: "mean" for x in self.property_columns + self.parameters}
        )
        return aggregations

    def compute_property_columns(self):
        self._property_columns = []

        net_column = "NET"
        bulk_column = "BULK"
        pore_column = "PORV"
        hcpv_column = "HCPV"

        # if NTG not given Net is equal to bulk
        if not net_column in self._dataframe.columns:
            net_column = bulk_column

        # compute NTG
        if (
            net_column in self._dataframe.columns
            and bulk_column in self._dataframe.columns
        ):
            self._dataframe["NTG"] = (
                self._dataframe[net_column] / self._dataframe[bulk_column]
            )
            self._property_columns.append("NTG")
        # compute PORO
        if (
            net_column in self._dataframe.columns
            and pore_column in self._dataframe.columns
        ):
            self._dataframe["PORO"] = (
                self._dataframe[pore_column] / self._dataframe[net_column]
            )
            self._property_columns.append("PORO")
        # compute SW
        if (
            hcpv_column in self._dataframe.columns
            and pore_column in self._dataframe.columns
        ):
            self._dataframe["SW"] = (
                1 - self._dataframe[hcpv_column] / self._dataframe[pore_column]
            )
            self._property_columns.append("SW")

        for voltype in ["OIL", "GAS"]:
            vol_column = "STOIIP" if voltype == "OIL" else "GIIP"
            # compute Bo/Bg
            if (
                hcpv_column in self._dataframe.columns
                and vol_column in self._dataframe.columns
            ):
                pvt = "BO" if voltype == "OIL" else "BG"
                self._dataframe[pvt] = (
                    self._dataframe[hcpv_column] / self._dataframe[vol_column]
                )
                self._property_columns.append(pvt)

    def test(self, dframe):

        net_column = "NET"
        bulk_column = "BULK"
        pore_column = "PORV"
        hcpv_column = "HCPV"

        # if NTG not given Net is equal to bulk
        if not net_column in dframe.columns:
            net_column = bulk_column

        # compute NTG
        if net_column in dframe.columns and bulk_column in dframe.columns:
            dframe["NTG"] = dframe[net_column] / dframe[bulk_column]
        # compute PORO
        if net_column in dframe.columns and pore_column in dframe.columns:
            dframe["PORO"] = dframe[pore_column] / dframe[net_column]
        # compute SW
        if hcpv_column in dframe.columns and pore_column in dframe.columns:
            dframe["SW"] = 1 - dframe[hcpv_column] / dframe[pore_column]

        for voltype in ["OIL", "GAS"]:
            vol_column = "STOIIP" if voltype == "OIL" else "GIIP"
            # compute Bo/Bg
            if hcpv_column in dframe.columns and vol_column in dframe.columns:
                pvt = "BO" if voltype == "OIL" else "BG"
                dframe[pvt] = dframe[hcpv_column] / dframe[vol_column]
        return dframe

    def _prepare_parameter_data(self, parameter_table, drop_constants):
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
    ensemble_set_model, volfolder: str, volfiles: Dict[str, str]
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
