import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype

from .ensemble_set_model import EnsembleSetModel
from .parameter_model import ParametersModel


class InplaceVolumesModel:

    POSSIBLE_SELECTORS = [
        "FLUID_ZONE",
        "SOURCE",
        "ENSEMBLE",
        "REAL",
        "FIPNUM",
        "SET",
        "ZONE",
        "REGION",
        "FACIES",
        "LICENSE",
        "SENSNAME_CASE",
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
        volume_type: str = "static",
    ):
        self._volume_type = volume_type
        self.pmodel = ParametersModel(
            parameter_table, drop_constants=drop_constants, keep_numeric_only=False
        )
        selectors = [x for x in volumes_table.columns if x in self.POSSIBLE_SELECTORS]

        if volume_type != "dynamic":
            # compute water zone volumes if total volumes are present
            if any(col.endswith("_TOTAL") for col in volumes_table.columns):
                volumes_table = self._compute_water_zone_volumes(
                    volumes_table, selectors
                )

            # stack dataframe on fluid zone and add fluid as column instead of a column suffix
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
                dfs.append(df)
            self._dataframe = pd.concat(dfs)

            # Set NET volumes based on facies if non_net_facies in input
            if non_net_facies is not None and "FACIES" in self._dataframe:
                self._dataframe["NET"] = self._dataframe["BULK"]
                self._dataframe.loc[
                    self._dataframe["FACIES"].isin(non_net_facies), "NET"
                ] = 0
        else:
            self._dataframe = volumes_table
            # Workaround the FUID ZONE needs to be defined in the
            # VolumetricAnalysis plugin - this will be fixed later!
            self._dataframe["FLUID_ZONE"] = "-"

        # If sensitivity run merge sensitivity columns into the dataframe
        if self.pmodel.sensrun:
            self._dataframe = pd.merge(
                self._dataframe, self.pmodel.sens_df, on=["ENSEMBLE", "REAL"]
            )

        # set column order
        colorder = self.selectors + self.VOLCOL_ORDER
        self._dataframe = self._dataframe[
            [x for x in colorder if x in self._dataframe]
            + [x for x in self._dataframe if x not in colorder]
        ]

        self._dataframe.sort_values(by=["ENSEMBLE", "REAL"], inplace=True)

        # ensure ensemble column consists of strings
        self._dataframe["ENSEMBLE"] = self._dataframe["ENSEMBLE"].astype(str)

        # compute and set property columns
        self._set_initial_property_columns()
        self._dataframe = self.compute_property_columns(self._dataframe)

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    @property
    def parameter_df(self) -> pd.DataFrame:
        return self.pmodel.dataframe

    @property
    def sensrun(self) -> bool:
        return self.pmodel.sensrun

    @property
    def volume_type(self) -> str:
        return self._volume_type

    @property
    def sensitivities(self) -> List[str]:
        return self.pmodel.sensitivities

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
    def ensemble_sensitivities(self) -> Dict[str, list]:
        return {
            ens: (
                list(
                    self._dataframe.loc[
                        self._dataframe["ENSEMBLE"] == ens, "SENSNAME_CASE"
                    ].unique()
                )
                if "SENSNAME_CASE" in self._dataframe
                else []
            )
            for ens in self.ensembles
        }

    @property
    def property_columns(self) -> List[str]:
        return self._property_columns

    @property
    def volume_columns(self) -> List[str]:
        return [
            x
            for x in self._dataframe
            if x not in self.selectors
            and x not in self.property_columns
            and is_numeric_dtype(self._dataframe[x])
        ]

    @property
    def selectors(self) -> List[str]:
        return [x for x in self.POSSIBLE_SELECTORS if x in self._dataframe]

    @property
    def region_selectors(self) -> List[str]:
        return [
            x
            for x in ["FIPNUM", "ZONE", "REGION", "SET", "LICENSE"]
            if x in self.selectors
        ]

    @property
    def responses(self) -> List[str]:
        return self.volume_columns + self.property_columns

    @property
    def hc_responses(self) -> List[str]:
        return [
            x
            for x in ["STOIIP", "GIIP", "ASSOCIATEDGAS", "ASSOCIATEDOIL"]
            if x in self.volume_columns
        ]

    @property
    def parameters(self) -> List[str]:
        return self.pmodel.parameters

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

        if all(
            col in self._dataframe for col in ["NET", "BULK"]
        ) and not self._dataframe["NET"].equals(self._dataframe["BULK"]):
            self._property_columns.append("NTG")
        if all(col in self._dataframe for col in ["BULK", "PORV"]):
            self._property_columns.append("PORO")
        if all(
            col in self._dataframe for col in ["NET", "PORV"]
        ) and not self._dataframe["NET"].equals(self._dataframe["BULK"]):
            self._property_columns.append("PORO_NET")
        if all(col in self._dataframe for col in ["HCPV", "PORV"]):
            self._property_columns.append("SW")

        for vol_column in ["STOIIP", "GIIP"]:
            if all(col in self._dataframe for col in ["HCPV", vol_column]):
                pvt = "BO" if vol_column == "STOIIP" else "BG"
                self._property_columns.append(pvt)

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
            dframe["PORO"] = dframe["PORV"] / dframe["BULK"]
        if "PORO_NET" in properties:
            dframe["PORO_NET"] = dframe["PORV"] / dframe["NET"]
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
            dframe = dframe.groupby(groups).mean(numeric_only=True).reset_index()

        dframe = self.compute_property_columns(dframe, properties)
        if "FLUID_ZONE" not in groups:
            if not filters.get("FLUID_ZONE") == ["oil"]:
                dframe["BO"] = np.nan
            if not filters.get("FLUID_ZONE") == ["gas"]:
                dframe["BG"] = np.nan
        return dframe


def filter_df(dframe: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Filter dataframe using dictionary with form
    'column_name': [list of values to keep]
    """
    for filt, values in filters.items():
        dframe = dframe.loc[dframe[filt].isin(values)]
    return dframe


def extract_volumes(
    ensemble_set_model: EnsembleSetModel,
    volfolder: str,
    volfiles: Dict[str, Any],
) -> pd.DataFrame:
    """Aggregates volumetric files from an FMU ensemble.
    Files must be stored on standardized csv format.
    """
    dfs = []
    for volname, files in volfiles.items():
        if isinstance(files, list):
            volframes = [
                ensemble_set_model.load_csv(Path(volfolder) / volfile)
                for volfile in files
            ]
            df = merge_csv_files(volframes)
        elif isinstance(files, str):
            df = ensemble_set_model.load_csv(Path(volfolder) / files)
        else:
            raise ValueError("Wrong format of volfile value argument!")
        df["SOURCE"] = volname
        dfs.append(df)

    if not dfs:
        raise ValueError(
            f"Error when aggregating inplace volumetric files: {list(volfiles)}. "
            f"Ensure that the files are present in relative folder {volfolder}"
        )
    return pd.concat(dfs)


def merge_csv_files(volframes: List[pd.DataFrame]) -> pd.DataFrame:
    """Merge csv files on common columns"""
    common_columns = list(
        set.intersection(*[set(frame.columns) for frame in volframes])
    )
    merged_dframe = pd.DataFrame(columns=common_columns)
    for frame in volframes:
        merged_dframe = pd.merge(merged_dframe, frame, on=common_columns, how="outer")
    return merged_dframe
