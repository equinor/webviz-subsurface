from typing import Any, Dict, List, Optional, Union

import pandas as pd
import plotly.graph_objects as go

from webviz_subsurface._abbreviations.number_formatting import si_prefixed

from ._tornado_data import TornadoData


class TornadoBarChart:
    """Creates a plotly bar figure from a TornadoData instance"""

    # pylint: disable=too-many-arguments, too-many-instance-attributes
    def __init__(
        self,
        tornado_data: TornadoData,
        plotly_theme: Dict[str, Any],
        figure_height: Optional[int] = None,
        label_options: str = "detailed",
        locked_si_prefix: Optional[Union[int, str]] = None,
        number_format: str = "",
        unit: str = "",
        spaced: bool = True,
        use_true_base: bool = False,
        show_realization_points: bool = True,
        show_reference: bool = True,
        color_by_sensitivity: bool = False,
        sensitivity_color_map: dict = None,
    ) -> None:
        self._tornadotable = tornado_data.tornadotable
        self._realtable = tornado_data.real_df
        self._reference_average = tornado_data.reference_average
        self._plotly_theme = plotly_theme
        self._number_format = number_format
        self._unit = unit
        self._spaced = spaced
        self._locked_si_prefix = locked_si_prefix
        self._locked_si_prefix_relative: Optional[Union[str, int]]
        self._scale = tornado_data.scale
        self._use_true_base = use_true_base
        self._show_reference = show_reference
        if self._scale == "Percentage":
            self._unit_x = "%"
            self._locked_si_prefix_relative = 0
        else:
            self._unit_x = self._unit
            self._locked_si_prefix_relative = locked_si_prefix
        self._figure_height = figure_height
        self._label_options = label_options
        self._show_scatter = show_realization_points
        self._color_by_sens = color_by_sensitivity
        self._sens_color_map = sensitivity_color_map

    def create_color_list(self, sensitivities: list) -> list:
        return (
            [self._sens_color_map.get(sensname, "grey") for sensname in sensitivities]
            if self._sens_color_map is not None
            else self._plotly_theme["layout"]["colorway"]
        )

    @property
    def figure_height(self) -> Optional[int]:
        """Set height of figure as a function of number of senscases(bars)"""
        return self._figure_height

    def _set_si_prefix(self, value: float) -> str:
        return str(
            si_prefixed(
                value,
                self._number_format,
                self._unit,
                self._spaced,
                self._locked_si_prefix,
            )
        )

    def _set_si_prefix_relative(self, value: float) -> str:
        return str(
            si_prefixed(
                value,
                self._number_format,
                self._unit_x,
                self._spaced,
                self._locked_si_prefix_relative,
            )
        )

    def bar_labels(self, case: str) -> List:
        if self._label_options not in ["simple", "detailed"]:
            return []

        barlabels = []
        for _, row in self._tornadotable.iterrows():
            # combine label if both bars on same side of reference
            comb_label = any((row["low_base"] > 0, row["high_base"] < 0))
            if comb_label:
                xvals = "  |  ".join(
                    [
                        self._set_si_prefix_relative(row["low_tooltip"]),
                        self._set_si_prefix_relative(row["high_tooltip"]),
                    ]
                )
                truevals = "  |  ".join(
                    [
                        self._set_si_prefix(row["true_low"]),
                        self._set_si_prefix(row["true_high"]),
                    ]
                )
                casename = f"{row['low_label']}  |  {row['high_label']}"
            else:
                xvals = self._set_si_prefix_relative(row[f"{case}_tooltip"])
                truevals = self._set_si_prefix(row[f"true_{case}"])
                casename = row[f"{case}_label"]

            text = f"<b>{xvals}</b>, " + ("<br>" if comb_label else "")
            if self._label_options == "detailed":
                text += f"True: {truevals}, <br><b>Case: {casename}</b> "
            barlabels.append(text)
        return barlabels

    def hover_labels(self) -> List:
        hovertext = []
        for _, row in self._tornadotable.iterrows():
            text = f"<b>Sensname: {row['sensname']}</b><br>"
            if row["low_label"] is not None:
                val = row["true_low"] if self._use_true_base else row["low_tooltip"]
                text += (
                    f"{row['low_label']}: <b>{self._set_si_prefix_relative(val)}</b> "
                )
            if row["high_label"] is not None:
                val = row["true_high"] if self._use_true_base else row["high_tooltip"]
                text += (
                    f"{row['high_label']}: <b>{self._set_si_prefix_relative(val)}</b>"
                )
            hovertext.append(text)
        return hovertext

    @property
    def data(self) -> List:
        colors = self.create_color_list(self._tornadotable["sensname"].unique())
        return [
            dict(
                type="bar",
                y=self._tornadotable["sensname"],
                x=self._tornadotable["low"],
                name="low",
                base=self._tornadotable["low_base"]
                if not self._use_true_base
                else (self._reference_average + self._tornadotable["low_base"]),
                customdata=self._tornadotable["low_reals"],
                text=self.bar_labels("low"),
                textposition="auto",
                insidetextanchor="middle",
                hoverinfo="text",
                hovertext=self.hover_labels(),
                orientation="h",
                marker={
                    "line": {"width": 1.5, "color": "black"},
                    "color": colors if self._color_by_sens else None,
                },
            ),
            dict(
                type="bar",
                y=self._tornadotable["sensname"],
                x=self._tornadotable["high"],
                name="high",
                base=self._tornadotable["high_base"]
                if not self._use_true_base
                else (self._reference_average + self._tornadotable["high_base"]),
                customdata=self._tornadotable["high_reals"],
                text=self.bar_labels("high"),
                textposition="auto",
                insidetextanchor="middle",
                hoverinfo="text",
                hovertext=self.hover_labels(),
                orientation="h",
                marker={
                    "line": {"width": 1.5, "color": "black"},
                    "color": colors if self._color_by_sens else None,
                },
            ),
        ]

    def calculate_scatter_value(self, case_values: pd.Series) -> List:
        if self._use_true_base:
            return case_values
        if self._scale == "Percentage":
            return (
                (case_values - self._reference_average) / self._reference_average
            ) * 100
        return case_values - self._reference_average

    @property
    def scatter_data(self) -> List[Dict]:
        return [
            {
                "type": "scatter",
                "mode": "markers",
                "y": df["sensname"],
                "x": self.calculate_scatter_value(df["VALUE"]),
                "text": df["REAL"],
                "hovertemplate": "REAL: <b>%{text}</b><br>"
                + "X: <b>%{x:.1f}</b> <extra></extra>",
                "marker": {
                    "size": 15,
                    "color": self._plotly_theme["layout"]["colorway"][0]
                    if case == "low"
                    else self._plotly_theme["layout"]["colorway"][1],
                },
            }
            for case, df in self._realtable.groupby("case")
        ]

    @property
    def range(self) -> List[float]:
        """Calculate x-axis range so that the reference is centered"""
        max_val = max(self._tornadotable[["low_tooltip", "high_tooltip"]].abs().max())
        if self._use_true_base:
            return [
                self._reference_average - (max_val * 1.1),
                self._reference_average + (max_val * 1.1),
            ]
        return [-max_val * 1.1, max_val * 1.1]

    @property
    def layout(self) -> Dict:
        _layout: Dict[str, Any] = go.Layout()
        _layout.update(self._plotly_theme["layout"])
        _layout.update(
            {
                "height": self.figure_height,
                "barmode": "overlay",
                "margin": {"l": 0, "r": 0, "b": 20, "t": 0, "pad": 21},
                "xaxis": {
                    "title": self._scale,
                    "range": self.range,
                    "autorange": self._show_scatter or self._tornadotable.empty,
                    "gridwidth": 1,
                    "gridcolor": "whitesmoke",
                    "showgrid": True,
                    "zeroline": False,
                    "linecolor": "black",
                    "showline": True,
                    "automargin": True,
                    "side": "top",
                    "tickfont": {"size": 15},
                },
                "yaxis": {
                    "autorange": True,
                    "showgrid": False,
                    "zeroline": False,
                    "showline": False,
                    "automargin": True,
                    "title": None,
                    "dtick": 1,
                    "tickfont": {"size": 15},
                },
                "showlegend": False,
                "hovermode": "closest",
                "hoverlabel": {"bgcolor": "white", "font_size": 16},
                "annotations": [
                    {
                        "x": 0 if not self._use_true_base else self._reference_average,
                        "y": 1.05,
                        "xref": "x",
                        "yref": "paper",
                        "text": f"<b>{self._set_si_prefix(self._reference_average)}</b>"
                        " (Ref avg)",
                        "showarrow": False,
                        "align": "center",
                    }
                ]
                if self._show_reference
                else None,
                "shapes": [
                    {
                        "type": "line",
                        "line": {"width": 3, "color": "lightgrey"},
                        "x0": 0 if not self._use_true_base else self._reference_average,
                        "x1": 0 if not self._use_true_base else self._reference_average,
                        "y0": 0,
                        "y1": 1,
                        "xref": "x",
                        "yref": "y domain",
                    }
                ],
            }
        )
        return _layout

    @property
    def figure(self) -> go.Figure:
        fig = go.Figure({"data": self.data, "layout": self.layout})
        if self._show_scatter:
            fig.update_traces(marker_opacity=0.4, text=None)
            for trace in self.scatter_data:
                fig.add_trace(trace)
        return fig
