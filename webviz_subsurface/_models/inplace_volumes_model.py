from typing import List, Optional, Dict, Any
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
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
        "FLUID_ZONE",
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

    VOLCOL_ORDER = [
        "STOIIP",
        "GIIP",
        "ASSOCIATEDOIL",
        "ASSOCIATEDGAS",
        "BULK",
        "NET",
        "PORV",
        "HCPV",
    ]

    def __init__(
        self,
        volumes_table: pd.DataFrame,
        parameter_table: Optional[pd.DataFrame] = None,
        non_net_facies: Optional[List[str]] = None,
        drop_constants: bool = True,
    ):
        self._parameters = []
        self._sensitivities = []
        self._sensrun = False
        self._parameterdf = (
            parameter_table if parameter_table is not None else pd.DataFrame()
        )
        selectors = [x for x in volumes_table.columns if x in self.POSSIBLE_SELECTORS]

        # It is not yet supported to combine sources with different selectors
        if volumes_table[selectors].isnull().values.any():
            raise TypeError(
                f"Selectors {[x for x in selectors if x not in ['ENSEMBLE', 'SOURCE', 'REAL']]} "
                "needs to be defined for all sources"
            )

        # compute water zone volumes if total volumes are present
        if any(col.endswith("_TOTAL") for col in volumes_table.columns):
            volumes_table = self._compute_water_zone_volumes(volumes_table, selectors)

        # stack dataframe on fluid zone and add fluid as column istead of a column suffix
        dfs = []
        for fluid in ["OIL", "GAS", "WATER"]:
            fluid_columns = [
                x for x in volumes_table.columns if x.endswith(f"_{fluid}")
            ]
            if not fluid_columns:
                continue
            df = volumes_table[selectors + fluid_columns].copy()
            df.columns = df.columns.str.replace(f"_{fluid}", "")
            df["FLUID_ZONE"] = fluid.lower()
            # Rename PORE to PORV (PORE will be deprecated..)
            if "PORE" in df:
                df.rename(columns={"PORE": "PORV"}, inplace=True)
            dfs.append(df)
        self._dataframe = pd.concat(dfs)

        # Set NET volumes based on facies if non_net_facies in input
        if non_net_facies is not None and "FACIES" in self._dataframe:
            self._dataframe["NET"] = self._dataframe["BULK"]
            self._dataframe.loc[
                self._dataframe["FACIES"].isin(non_net_facies), "NET"
            ] = 0

        # If parameters present check if the case is a sensitivity run
        # and merge sensitivity columns into the dataframe
        if parameter_table is not None:
            self._parameterdf = self._prepare_parameter_data(
                parameter_table, drop_constants
            )
            self._parameters = [
                x for x in self._parameterdf.columns if x not in self.SENS_COLUMNS
            ]
            if "SENSNAME" in self._parameterdf:
                self._add_sensitivity_columns()
                self._sensitivities = list(self._dataframe["SENSNAME"].unique())

        # set column order
        colorder = self.selectors + self.VOLCOL_ORDER
        self._dataframe = self._dataframe[
            [x for x in colorder if x in self._dataframe]
            + [x for x in self._dataframe if x not in colorder]
        ]

        self._dataframe.sort_values(by=["ENSEMBLE", "REAL"], inplace=True)

        # compute and set property columns
        self._set_initial_property_columns()
        self._dataframe = self.compute_property_columns(self._dataframe)

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
    def sensitivities(self) -> List[str]:
        return self._sensitivities

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

    @staticmethod
    def _compute_water_zone_volumes(
        voldf: pd.DataFrame, selectors: list
    ) -> pd.DataFrame:
        """Compute water zone volumes by subtracting HC-zone volumes from
        TOTAL volumes"""
        supported_columns = ["BULK_TOTAL", "NET_TOTAL", "PORE_TOTAL", "PORV_TOTAL"]
        # Format check
        for src, df in voldf.groupby("SOURCE"):
            volcols = [col for col in df if col not in selectors]
            if not any(col in volcols for col in supported_columns):
                continue
            if df[volcols].isnull().values.any():
                warnings.warn(
                    f"WARNING: Cannot calculate water zone volumes for source {src}, "
                    "due to wrong format in input volume file. \nTo ensure correct format "
                    "use: https://equinor.github.io/fmu-tools/fmu.tools.rms.html#fmu.tools."
                    "rms.volumetrics.merge_rms_volumetrics"
                )
                return voldf

        for col in [x.replace("_TOTAL", "") for x in voldf if x in supported_columns]:
            voldf[f"{col}_WATER"] = (
                voldf[f"{col}_TOTAL"]
                - voldf.get(f"{col}_OIL", 0)
                - voldf.get(f"{col}_GAS", 0)
            )
        return voldf

    def _set_initial_property_columns(self) -> None:
        """Create list of properties that can be computed based on
        available volume columns"""
        self._property_columns = []

        if all(col in self._dataframe for col in ["NET", "BULK"]):
            self._property_columns.append("NTG")
        if all(col in self._dataframe for col in ["BULK", "PORV"]):
            self._property_columns.append("PORO")
        if all(col in self._dataframe for col in ["NET", "PORV"]):
            self._property_columns.append("PORO (net)")
        if all(col in self._dataframe for col in ["HCPV", "PORV"]):
            self._property_columns.append("SW")

        for vol_column in ["STOIIP", "GIIP"]:
            if all(col in self._dataframe for col in ["HCPV", vol_column]):
                pvt = "BO" if vol_column == "STOIIP" else "BG"
                self._property_columns.append(pvt)

    def _add_sensitivity_columns(self) -> None:
        """Add sensitivity information columns from the parameters to the
        dataframe, and raise error if not all ensembles have sensitivity data"""

        self._parameterdf["SENSTYPE"] = self._parameterdf.apply(
            lambda row: find_sens_type(row.SENSCASE)
            if not pd.isnull(row.SENSCASE)
            else np.nan,
            axis=1,
        )
        sens_params_table = self._parameterdf[self.SENS_COLUMNS]

        sensruns = []
        for _, df in sens_params_table.groupby("ENSEMBLE"):
            is_sensrun = not df["SENSNAME"].isnull().values.all() and (
                df["SENSNAME"].nunique() > 1
                or (df["SENSNAME"].nunique() == 1 and df["SENSTYPE"].unique() != ["mc"])
            )
            sensruns.append(is_sensrun)
        self._sensrun = all(sensruns)

        # raise error if mixed ensemble types
        if not self._sensrun and any(sensruns):
            raise ValueError(
                "Ensembles with and without sensitivity data mixed - this is not supported"
            )

        # Merge into one dataframe
        self._dataframe = pd.merge(
            self._dataframe, sens_params_table, on=["ENSEMBLE", "REAL"]
        )

    def compute_property_columns(
        self, dframe: pd.DataFrame, properties: Optional[list] = None
    ) -> pd.DataFrame:
        """Compute property columns. As default all property columns are computed,
        but which properties to compute can be given as input"""
        dframe = dframe.copy()
        properties = self.property_columns if properties is None else properties

        if "NTG" in properties:
            dframe["NTG"] = dframe["NET"] / dframe["BULK"]
        if "PORO" in properties:
            if "NET" in dframe.columns:
                dframe["PORO (net)"] = dframe["PORV"] / dframe["NET"]
            dframe["PORO"] = dframe["PORV"] / dframe["BULK"]
        if "SW" in properties:
            dframe["SW"] = 1 - (dframe["HCPV"] / dframe["PORV"])
        if "BO" in properties:
            dframe["BO"] = dframe["HCPV"] / dframe["STOIIP"]
        if "BG" in properties:
            dframe["BG"] = dframe["HCPV"] / dframe["GIIP"]
        # nan is handled by plotly but not inf
        dframe.replace(np.inf, np.nan, inplace=True)
        return dframe

    def get_df(
        self,
        filters: Optional[Dict[str, list]] = None,
        groups: Optional[list] = None,
        parameters: Optional[list] = None,
        properties: Optional[list] = None,
    ) -> pd.DataFrame:
        """Function to retrieve a dataframe with volumetrics and properties. Parameters
        can be added to the dataframe if parameters are available in the instance.
        Filters are supported on dictionary form with 'column_name': [list ov values to keep].
        The final dataframe can be grouped by giving in a list of columns to group on.
        """
        dframe = self.dataframe.copy()

        groups = groups if groups is not None else []
        filters = filters if filters is not None else {}
        parameters = parameters if parameters is not None else []

        if parameters and self.parameters:
            columns = parameters + ["REAL", "ENSEMBLE"]
            dframe = pd.merge(
                dframe, self.parameter_df[columns], on=["REAL", "ENSEMBLE"]
            )
        if filters:
            dframe = filter_df(dframe, filters)

        prevent_sum_over = ["REAL", "ENSEMBLE", "SOURCE"]
        if groups:
            sum_over_groups = groups + [x for x in prevent_sum_over if x not in groups]

            # Need to sum volume columns and take the average of parameter columns
            aggregations = {x: "sum" for x in self.volume_columns}
            aggregations.update({x: "mean" for x in parameters})

            dframe = dframe.groupby(sum_over_groups).agg(aggregations).reset_index()
            dframe = dframe.groupby(groups).mean().reset_index()

        dframe = self.compute_property_columns(dframe, properties)
        if "FLUID_ZONE" not in groups:
            if not filters.get("FLUID_ZONE") == ["oil"]:
                dframe["BO"] = "NA"
            if not filters.get("FLUID_ZONE") == ["gas"]:
                dframe["BG"] = "NA"
        return dframe

    def _prepare_parameter_data(
        self, parameter_table: pd.DataFrame, drop_constants: bool
    ) -> pd.DataFrame:
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

        return parameter_table


def filter_df(dframe: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Filter dataframe using dictionary with form
    'column_name': [list ov values to keep]
    """
    for filt, values in filters.items():
        dframe = dframe.loc[dframe[filt].isin(values)]
    return dframe


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
