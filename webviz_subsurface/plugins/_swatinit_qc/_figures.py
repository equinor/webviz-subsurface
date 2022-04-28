from typing import List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from webviz_subsurface._figures import create_figure
from webviz_subsurface._utils.colors import hex_to_rgb, rgb_to_str, scale_rgb_lightness

from ._business_logic import QcFlags


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
        QcFlags.SWL_TRUNC.value,
        QcFlags.PPCWMAX.value,
        QcFlags.FINE_EQUIL.value,
        QcFlags.HC_BELOW_FWL.value,
        QcFlags.SWATINIT_1.value,
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
            .update_layout(
                plot_bgcolor="white",
                title="Waterfall chart showing changes from SWATINIT to SWAT",
                margin={"t": 50, "b": 50, "l": 50, "r": 50},
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


class PropertiesVsDepthSubplots:
    def __init__(
        self,
        dframe: pd.DataFrame,
        color_by: str,
        colormap: dict,
        discrete_color: bool = True,
    ) -> None:
        self.dframe = dframe
        self.color_by = color_by
        self.discrete_color = discrete_color
        self.colormap = colormap
        self.layout = [(1, 1), (1, 2), (2, 1), (2, 2)]
        self.responses = ["SWATINIT", "SWAT", "PRESSURE", "PC"]
        self.hover_data = self.create_hover_data(
            include_columns=["QC_FLAG", "EQLNUM", "SATNUM", "I", "J", "K"]
        )
        self.uirevision = "".join([str(x) for x in self.dframe["EQLNUM"].unique()])

        self._figure = self.create_empty_subplots_figure(rows=2, cols=2)
        self.add_subplotfigures_to_main_figure()
        self.add_contacts_to_plot()

    @property
    def figure(self) -> go.Figure:
        return self._figure

    @property
    def hovertemplate(self) -> go.Figure:
        return (
            "X: %{x}<br>Y: %{y}<br>"
            + "<br>".join(
                [
                    f"{col}:%{{customdata[{idx}]}}"
                    for idx, col in enumerate(self.hover_data)
                ]
            )
            + "<extra></extra>"
        )

    def create_empty_subplots_figure(self, rows: int, cols: int) -> go.Figure:
        return (
            make_subplots(
                rows=rows,
                cols=cols,
                subplot_titles=[f"Depth vs {resp}" for resp in self.responses],
                shared_yaxes=True,
                vertical_spacing=0.07,
                horizontal_spacing=0.05,
            )
            .update_layout(
                plot_bgcolor="white",
                uirevision=self.uirevision,
                margin={"t": 50, "b": 10, "l": 10, "r": 10},
                legend={"orientation": "h"},
                clickmode="event+select",
                coloraxis={"colorscale": "Viridis", **self.colorbar},
            )
            .update_yaxes(autorange="reversed", **axis_defaults())
            .update_xaxes(axis_defaults())
        )

    def add_subplotfigures_to_main_figure(self) -> None:
        # for discrete colors there should be one trace per unique color
        unique_traces = (
            self.dframe[self.color_by].unique()
            if self.discrete_color
            else [self.color_by]
        )

        for color in unique_traces:
            df = self.dframe
            df = df[df[self.color_by] == color] if self.discrete_color else df
            customdata = np.stack([df[col] for col in self.hover_data], axis=-1)

            for idx, response in enumerate(self.responses):
                trace = go.Scattergl(
                    x=df[response],
                    y=df["Z"],
                    mode="markers",
                    name=color,
                    showlegend=idx == 0,
                    marker=self.set_marker_style(color, df),
                    unselected={"marker": self.set_unselected_marker_style(color)},
                    customdata=customdata,
                    hovertemplate=self.hovertemplate,
                    legendgroup=color,
                ).update(marker_size=10)

                row, col = self.layout[idx]
                self._figure.add_trace(trace, row=row, col=col)

    @property
    def colorbar(self) -> dict:
        if self.color_by != "PERMX":
            return {}
        tickvals = list(range(-4, 5, 1))
        return {
            "colorbar": {
                "tickvals": tickvals,
                "ticktext": [10**val for val in tickvals],
            }
        }

    def create_hover_data(self, include_columns: list) -> list:
        # ensure the colorby is the first entry in the list -> used in customdata in callback
        hover_data = [self.color_by]
        for col in include_columns:
            if col not in hover_data:
                hover_data.append(col)
        return hover_data

    def set_marker_style(self, color: str, df: pd.DataFrame) -> dict:
        if not self.discrete_color:
            return {
                "coloraxis": "coloraxis",
                "color": df[self.color_by]
                if self.color_by != "PERMX"
                else np.log10(df[self.color_by]),
            }
        return {"color": self.colormap[color], "opacity": 0.5}

    def set_unselected_marker_style(self, color: str) -> dict:
        if not self.discrete_color:
            return {"opacity": 0.1}
        return {
            "color": rgb_to_str(
                scale_rgb_lightness(hex_to_rgb(self.colormap[color]), 250)
            )
        }

    def add_contacts_to_plot(self) -> None:
        """Annotate axes with named horizontal lines for contacts."""
        for contact in ["OWC", "GWC", "GOC"]:
            if contact in self.dframe and self.dframe["EQLNUM"].nunique() == 1:
                # contacts are assumed constant in the dataframe
                value = self.dframe[contact].values[0]
                # do not include dummy contacts (shallower than the dataset)
                if value > self.dframe["Z"].min():
                    self._figure.add_hline(
                        value,
                        line={"color": "black", "dash": "dash", "width": 1.5},
                        annotation_text=f"{contact}={value:g}",
                        annotation_position="bottom left",
                    )


class MapFigure:
    def __init__(
        self,
        dframe: pd.DataFrame,
        color_by: str,
        colormap: dict,
        faultlinedf: Optional[pd.DataFrame] = None,
    ):
        self.dframe = dframe
        self.color_by = color_by
        self.colormap = colormap
        self.hover_data = ["I", "J", "K"]

        self._figure = self.create_figure()

        if faultlinedf is not None:
            self.add_fault_lines(faultlinedf)

    @property
    def figure(self) -> go.Figure:
        return self._figure

    @property
    def axis_layout(self) -> dict:
        return {
            "title": None,
            "showticklabels": False,
            "showgrid": False,
            "showline": False,
        }

    def create_figure(self) -> go.Figure:
        return (
            create_figure(
                plot_type="scatter",
                data_frame=self.dframe,
                x="X",
                y="Y",
                color=self.color_by
                if self.color_by != "PERMX"
                else np.log10(self.dframe[self.color_by]),
                color_discrete_map=self.colormap,
                xaxis={"constrain": "domain", **self.axis_layout},
                yaxis={"scaleanchor": "x", **self.axis_layout},
                hover_data=[self.color_by] + self.hover_data,
                color_continuous_scale="Viridis",
            )
            .update_traces(marker_size=10, unselected={"marker": {"opacity": 0}})
            .update_coloraxes(showscale=False)
            .update_layout(
                plot_bgcolor="white",
                margin={"t": 10, "b": 10, "l": 0, "r": 0},
                showlegend=False,
            )
        )

    def add_fault_lines(self, faultlinedf: pd.DataFrame) -> None:
        for _fault, faultdf in faultlinedf.groupby("POLY_ID"):
            self._figure.add_trace(
                {
                    "x": faultdf["X_UTME"],
                    "y": faultdf["Y_UTMN"],
                    "mode": "lines",
                    "type": "scatter",
                    "hoverinfo": "none",
                    "showlegend": False,
                    "line": {"color": "grey", "width": 1},
                }
            )
