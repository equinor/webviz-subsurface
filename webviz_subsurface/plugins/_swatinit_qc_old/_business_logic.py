import re
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from webviz_config import WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore


class QcFlags(str, Enum):
    """Constants for use by check_swatinit"""

    FINE_EQUIL = "FINE_EQUIL"
    HC_BELOW_FWL = "HC_BELOW_FWL"
    PC_SCALED = "PC_SCALED"
    PPCWMAX = "PPCWMAX"
    SWATINIT_1 = "SWATINIT_1"
    SWL_TRUNC = "SWL_TRUNC"
    UNKNOWN = "UNKNOWN"
    WATER = "WATER"


class SwatinitQcDataModel:
    """Class keeping the data needed in the vizualisations and various
    data providing methods.
    """

    COLNAME_THRESHOLD = "HC cells above threshold (%)"
    SELECTORS = ["QC_FLAG", "SATNUM", "EQLNUM", "FIPNUM"]

    DROP_COLUMNS = [
        "Z_MIN",
        "Z_MAX",
        "GLOBAL_INDEX",
        "SWATINIT_SWAT",
        "SWATINIT_SWAT_WVOL",
        "SWL_x",
        "SWL_y",
        "Z_DATUM",
        "PRESSURE_DATUM",
    ]

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        csvfile: str,
        ensemble: str = None,
        realization: Optional[int] = None,
        faultlines: Optional[Path] = None,
    ):

        self._theme = webviz_settings.theme
        self._faultlines = faultlines
        self.faultlines_df = read_csv(faultlines) if faultlines else None

        if ensemble is not None:
            if isinstance(ensemble, list):
                raise TypeError(
                    'Incorrent argument type, "ensemble" must be a string instead of a list'
                )
            if realization is None:
                raise ValueError('Incorrent arguments, "realization" must be specified')

            ens_path = webviz_settings.shared_settings["scratch_ensembles"][ensemble]
            # replace realization in string from scratch_ensemble with input realization
            ens_path = re.sub(
                "realization-[^/]", f"realization-{realization}", ens_path
            )
            self.csvfile = Path(ens_path) / csvfile
        else:
            self.csvfile = Path(csvfile)

        self.dframe = read_csv(self.csvfile)
        self.dframe.drop(columns=self.DROP_COLUMNS, errors="ignore", inplace=True)

        for col in self.SELECTORS + ["OWC", "GWC", "GOC"]:
            if col in self.dframe:
                self.dframe[col] = self.dframe[col].astype("category")

        self._initial_qc_volumes = self.compute_qc_volumes(self.dframe)

    @property
    def webviz_store(self) -> List[Tuple[Callable, List[dict]]]:
        return [
            (
                read_csv,
                [
                    {"csv_file": path}
                    for path in [self._faultlines, self.csvfile]
                    if path is not None
                ],
            )
        ]

    @property
    def colors(self) -> List[str]:
        return self._theme.plotly_theme["layout"]["colorway"]

    @property
    def qc_flag_colors(self) -> Dict[str, str]:
        """Predefined colors for the QC_FLAG column"""
        return {
            QcFlags.FINE_EQUIL.value: self.colors[8],
            QcFlags.HC_BELOW_FWL.value: self.colors[5],
            QcFlags.PC_SCALED.value: self.colors[2],
            QcFlags.PPCWMAX.value: self.colors[9],
            QcFlags.SWATINIT_1.value: self.colors[6],
            QcFlags.SWL_TRUNC.value: self.colors[3],
            QcFlags.UNKNOWN.value: self.colors[1],
            QcFlags.WATER.value: self.colors[0],
        }

    @property
    def eqlnums(self) -> List[str]:
        return sorted(list(self.dframe["EQLNUM"].unique()), key=int)

    @property
    def satnums(self) -> List[str]:
        return sorted(list(self.dframe["SATNUM"].unique()), key=int)

    @property
    def qc_flag(self) -> List[str]:
        return sorted(list(self.dframe["QC_FLAG"].unique()))

    @property
    def filters_discrete(self) -> List[str]:
        return ["QC_FLAG", "SATNUM"]

    @property
    def filters_continuous(self) -> List[str]:
        return ["Z", "PC", "SWATINIT", "PERMX", "PORO"]

    @property
    def color_by_selectors(self) -> List[str]:
        return self.SELECTORS + ["PERMX", "PORO"]

    @property
    def pc_scaling_min_max(self) -> Tuple[float, float]:
        return (self.dframe["PC_SCALING"].max(), self.dframe["PC_SCALING"].min())

    @property
    def vol_diff_total(self) -> Tuple[float, float]:
        return (
            self._initial_qc_volumes["WVOL_DIFF_PERCENT"],
            self._initial_qc_volumes["HCVOL_DIFF_PERCENT"],
        )

    def get_dataframe(
        self,
        filters: Optional[dict] = None,
        range_filters: Optional[dict] = None,
    ) -> pd.DataFrame:

        df = self.dframe.copy()
        filters = filters if filters is not None else {}
        range_filters = range_filters if range_filters is not None else {}

        for filt, value in filters.items():
            df = df[df[filt].isin(value)]

        for filt, value in range_filters.items():
            min_val, max_val = value
            df = df[(df[filt] >= min_val) & (df[filt] <= max_val) | (df[filt].isnull())]

        return df

    @staticmethod
    def resample_dataframe(dframe: pd.DataFrame, max_points: int) -> pd.DataFrame:
        """Resample a dataframe to max number of points. The sampling will be
        weighted in order to avoid removal of points that has an important qc_flag.
        Points will mostly be removed if they are flagged as "WATER" or "PC_SCALED"
        """
        if dframe.shape[0] > max_points:
            dframe = dframe.copy()
            dframe["sample_weight"] = 1
            dframe.loc[dframe["QC_FLAG"] == "WATER", "sample_weight"] = 0.1
            dframe.loc[dframe["QC_FLAG"] == "PC_SCALED", "sample_weight"] = 0.5
            return dframe.sample(max_points, weights=dframe["sample_weight"])
        return dframe

    @staticmethod
    def filter_dframe_on_depth(dframe: pd.DataFrame) -> pd.DataFrame:
        """Suggest a deep depth limit for what to plot, in order to avoid
        showing too much of a less interesting water zone
        """
        max_z = dframe["Z"].max()
        hc_dframe = dframe[dframe["SWATINIT"] < 1]
        if not hc_dframe.empty:
            lowest_hc = hc_dframe["Z"].max()
            hc_height = lowest_hc - dframe["Z"].min()
            # Suggest to visualize a water height of 10% of the hc zone:
            max_z = lowest_hc + 0.2 * hc_height

        return dframe[dframe["Z"] <= max_z]

    @staticmethod
    def compute_qc_volumes(dframe: pd.DataFrame) -> dict:
        """Compute numbers relevant for QC of saturation initialization of a
        reservoir model.
        Different volume numbers are typically related to the different QC_FLAG
        """
        qc_vols: dict = {}

        # Ensure all QCFlag categories are represented:
        for qc_cat in QcFlags:
            qc_vols[qc_cat.value] = 0.0

        # Overwrite dict values with correct figures:
        for qc_cat, qc_df in dframe.groupby("QC_FLAG"):
            qc_vols[qc_cat] = (
                (qc_df["SWAT"] - qc_df["SWATINIT"]) * qc_df["PORV"]
            ).sum()

        if "VOLUME" in dframe:
            qc_vols["VOLUME"] = dframe["VOLUME"].sum()

        qc_vols["PORV"] = dframe["PORV"].sum()
        qc_vols["SWATINIT_WVOL"] = (dframe["SWATINIT"] * dframe["PORV"]).sum()
        qc_vols["SWATINIT_HCVOL"] = qc_vols["PORV"] - qc_vols["SWATINIT_WVOL"]
        qc_vols["SWAT_WVOL"] = (dframe["SWAT"] * dframe["PORV"]).sum()
        qc_vols["SWAT_HCVOL"] = qc_vols["PORV"] - qc_vols["SWAT_WVOL"]

        # compute difference columns
        qc_vols["WVOL_DIFF"] = qc_vols["SWAT_WVOL"] - qc_vols["SWATINIT_WVOL"]
        qc_vols["WVOL_DIFF_PERCENT"] = (
            qc_vols["WVOL_DIFF"] / qc_vols["SWATINIT_WVOL"]
        ) * 100
        qc_vols["HCVOL_DIFF"] = qc_vols["SWAT_HCVOL"] - qc_vols["SWATINIT_HCVOL"]
        qc_vols["HCVOL_DIFF_PERCENT"] = (
            ((qc_vols["HCVOL_DIFF"] / qc_vols["SWATINIT_HCVOL"]) * 100)
            if qc_vols["HCVOL_DIFF"] != 0.0
            else 0
        )
        qc_vols["EQLNUMS"] = sorted(dframe["EQLNUM"].unique())
        qc_vols["SATNUMS"] = sorted(dframe["SATNUM"].unique())

        return qc_vols

    def create_colormap(self, color_by: str) -> dict:
        """Create a colormap to ensure that the subplot and the mapfigure
        has the same color for the same unique value. If 'QC_FLAG' is used as
        color column, predefined colors are used.
        """

        return (
            dict(zip(self.dframe[color_by].unique(), self.colors * 10))
            if color_by != "QC_FLAG"
            else self.qc_flag_colors
        )

    def get_max_pc_info_and_percent_for_data_matching_condition(
        self,
        dframe: pd.DataFrame,
        condition: Optional[int],
        groupby_eqlnum: bool = True,
    ) -> pd.DataFrame:
        def get_percent_of_match(df: pd.DataFrame, condition: Optional[int]) -> float:
            df = df[df["QC_FLAG"] == "PC_SCALED"]
            if condition is None or df.empty:
                return np.nan
            return (len(df[df["PC_SCALING"] >= condition]) / len(df)) * 100

        groupby = ["SATNUM"] if not groupby_eqlnum else ["EQLNUM", "SATNUM"]
        df_group = dframe.groupby(groupby)
        df = df_group.max()[["PCOW_MAX", "PPCW", "PC_SCALING"]].round(6)
        df[self.COLNAME_THRESHOLD] = df_group.apply(
            lambda x: get_percent_of_match(x, condition)
        )
        return df.reset_index().sort_values(groupby, key=lambda col: col.astype(int))

    def table_data_qc_vol_overview(self) -> tuple:
        """Return data and columns for dash_table showing overview of qc volumes"""

        skip_if_zero = [QcFlags.UNKNOWN.value, QcFlags.WATER.value]
        column_order = [
            "",
            "Response",
            "Water Volume Diff",
            "HC Volume Diff",
            "Water Volume Mrm3",
            "HC Volume Mrm3",
        ]
        qc_vols = self._initial_qc_volumes

        table_data = []
        # First report the SWATINIT volumes
        table_data.append(
            {
                "Response": "SWATINIT",
                "Water Volume Mrm3": f"{qc_vols['SWATINIT_WVOL']/1e6:>10.3f}",
                "HC Volume Mrm3": f" {qc_vols['SWATINIT_HCVOL']/1e6:>8.3f}",
            }
        )
        # Then report the volume change per QC_FLAG
        for key in [x.value for x in QcFlags]:
            if key in skip_if_zero and np.isclose(qc_vols[key], 0, atol=1):
                # Tolerance is 1 rm3, which is small in relevant contexts.
                continue
            table_data.append(
                {
                    "": "+",
                    "Response": key,
                    "Water Volume Mrm3": f"{qc_vols[key]/1e6:>10.3f}",
                    "Water Volume Diff": f"{qc_vols[key]/qc_vols['SWATINIT_WVOL']*100:>3.2f} %",
                    "HC Volume Diff": f"{-qc_vols[key]/qc_vols['SWATINIT_HCVOL']*100:>3.2f} %"
                    if qc_vols["SWATINIT_HCVOL"] > 0
                    else "0.00 %",
                }
            )
        # Last report the SWAT volumes and change from SWATINIT
        table_data.append(
            {
                "": "=",
                "Response": "SWAT",
                "Water Volume Mrm3": f"{qc_vols['SWAT_WVOL']/1e6:>10.3f}",
                "Water Volume Diff": f"{qc_vols['WVOL_DIFF_PERCENT']:>3.2f} %",
                "HC Volume Diff": f"{qc_vols['HCVOL_DIFF_PERCENT']:>3.2f} %",
                "HC Volume Mrm3": f"{qc_vols['SWAT_HCVOL']/1e6:>8.3f}",
            }
        )
        return table_data, [{"name": i, "id": i} for i in column_order]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: str) -> pd.DataFrame:
    return pd.read_csv(csv_file)
