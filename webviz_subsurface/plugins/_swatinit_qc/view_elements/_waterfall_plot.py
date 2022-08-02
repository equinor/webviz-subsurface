from typing import List

import plotly.graph_objects as go

from .._plugin_ids import PlugInIDs


def axis_defaults(showgrid: bool = True) -> dict:
    return {
        "showline": True,
        "linewidth": 2,
        "linecolor": "black",
        "mirror": True,
        "showgrid": showgrid,
        "gridwidth": 1,
        "gridcolor": "lightgrey",
    }


class WaterfallPlot:
    # Ensure fixed order of plot elements:
    ORDER = [
        "SWATINIT_WVOL",
        PlugInIDs.QcFlags.SWL_TRUNC,
        PlugInIDs.QcFlags.PPCWMAX,
        PlugInIDs.QcFlags.FINE_EQUIL,
        PlugInIDs.QcFlags.HC_BELOW_FWL,
        PlugInIDs.QcFlags.SWATINIT_1,
        "SWAT_WVOL",
    ]
    MEASURES = [
        "absolute",
        "relative",
        "relative",
        "relative",
        "relative",
        "relative",
        "total",
    ]

    def __init__(self, qc_vols: dict) -> None:
        # collect necessary values from input and make volume values more human friendly
        self.qc_vols = {
            key: (qc_vols[key] / (10**6))
            for key in self.ORDER + ["SWATINIT_HCVOL", "SWAT_HCVOL"]
        }
        self.qc_vols.update(
            {key: qc_vols[key] for key in ["WVOL_DIFF_PERCENT", "HCVOL_DIFF_PERCENT"]}
        )

    @property
    def range(self) -> list:
        range_min = min(self.qc_vols["SWATINIT_WVOL"], self.qc_vols["SWAT_WVOL"]) * 0.95
        range_max = max(self.qc_vols["SWATINIT_WVOL"], self.qc_vols["SWAT_WVOL"]) * 1.05
        return [range_min, range_max]

    @property
    def figure(self) -> go.Figure:
        return (
            go.Figure(
                go.Waterfall(
                    orientation="v",
                    measure=self.MEASURES,
                    x=self.ORDER,
                    textposition="outside",
                    text=self.create_bartext(),
                    y=[self.qc_vols[key] for key in self.ORDER],
                    connector={"mode": "spanning"},
                )
            )
            .update_yaxes(
                title="Water Volume (Mrm3)", range=self.range, **axis_defaults()
            )
            .update_xaxes(
                type="category",
                tickangle=-45,
                tickfont_size=17,
                **axis_defaults(showgrid=False),
            )
            .update_layout(
                plot_bgcolor="white",
                title="Waterfall chart showing changes from SWATINIT to SWAT",
                margin={"t": 50, "b": 50, "l": 50, "r": 50},
            )
        )

    def create_bartext(self) -> List[str]:
        """
        Create bartext for each qc_flag category with Water and HC volume change
        relative to SWATINIT_WVOL in percent.
        """
        text = []
        for bar_name in self.ORDER:
            bartext = [f"{self.qc_vols[bar_name]:.2f} Mrm3"]
            if bar_name != self.ORDER[0]:
                bartext.append(
                    f"Water {self.get_water_diff_in_percent(bar_name):.1f} %"
                )
                bartext.append(f"HC {self.get_hc_diff_in_percent(bar_name):.1f} %")

            text.append("<br>".join(bartext))
        return text

    def get_water_diff_in_percent(self, bar_name: str) -> float:
        if bar_name == self.ORDER[-1]:
            return self.qc_vols["WVOL_DIFF_PERCENT"]
        return (self.qc_vols[bar_name] / self.qc_vols["SWATINIT_WVOL"]) * 100

    def get_hc_diff_in_percent(self, bar_name: str) -> float:
        if bar_name == self.ORDER[-1]:
            return self.qc_vols["HCVOL_DIFF_PERCENT"]
        if self.qc_vols["SWATINIT_HCVOL"] > 0:
            return (-self.qc_vols[bar_name] / self.qc_vols["SWATINIT_HCVOL"]) * 100
        return 0
