from typing import Optional, List, Dict, Any

from webviz_subsurface._abbreviations.number_formatting import si_prefixed
from webviz_subsurface._utils.formatting import printable_int_list
from ._tornado_data import TornadoData


class TornadoBarChart:
    """Creates a plotly bar figure from a TornadoData instance"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        tornado_data: TornadoData,
        plotly_theme: Dict[str, Any],
        figure_height: Optional[int] = None,
        show_labels: bool = True,
        locked_si_prefix: Optional[int] = None,
        number_format: str = "",
        unit: str = "",
        spaced: bool = True,
    ) -> None:
        self._tornadotable = tornado_data.tornadotable
        self._reference_average = tornado_data.reference_average
        self._plotly_theme = plotly_theme
        self._number_format = number_format
        self._unit = unit
        self._spaced = spaced
        self._locked_si_prefix = locked_si_prefix
        self._locked_si_prefix_relative: Optional[int]
        self._scale = tornado_data.scale
        if self._scale == "Percentage":
            self._unit_x = "%"
            self._locked_si_prefix_relative = 0
        else:
            self._unit_x = self._unit
            self._locked_si_prefix_relative = locked_si_prefix
        self._figure_height = (
            figure_height
            if figure_height
            else 100 * len(self._tornadotable["sensname"].unique())
        )
        self._show_labels = show_labels

    @property
    def figure_height(self) -> int:
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

    @property
    def data(self) -> List:
        return [
            dict(
                type="bar",
                y=self._tornadotable["sensname"],
                x=self._tornadotable["low"],
                name="low",
                base=self._tornadotable["low_base"],
                customdata=self._tornadotable["low_reals"],
                text=[
                    f"<b>{self._set_si_prefix_relative(x)}</b>, "
                    f"True: {self._set_si_prefix(val)}, "
                    f"<br><b>Case: {label}</b>, "
                    f"Reals: {printable_int_list(reals)}"
                    if reals
                    else None
                    for x, label, val, reals in zip(
                        self._tornadotable["low_tooltip"],
                        self._tornadotable["low_label"],
                        self._tornadotable["true_low"],
                        self._tornadotable["low_reals"],
                    )
                ]
                if self._show_labels
                else [],
                textposition="auto",
                insidetextanchor="middle",
                hoverinfo="none",
                orientation="h",
                marker={"line": {"width": 1.5}},
            ),
            dict(
                type="bar",
                y=self._tornadotable["sensname"],
                x=self._tornadotable["high"],
                name="high",
                base=self._tornadotable["high_base"],
                customdata=self._tornadotable["high_reals"],
                text=[
                    f"<b>{self._set_si_prefix_relative(x)}</b>, "
                    f"True: {self._set_si_prefix(val)}, "
                    f"<br><b>Case: {label}</b>, "
                    f"Reals: {printable_int_list(reals)}"
                    if reals
                    else None
                    for x, label, val, reals in zip(
                        self._tornadotable["high_tooltip"],
                        self._tornadotable["high_label"],
                        self._tornadotable["true_high"],
                        self._tornadotable["high_reals"],
                    )
                ]
                if self._show_labels
                else [],
                textposition="auto",
                insidetextanchor="middle",
                hoverinfo="none",
                orientation="h",
                marker={"line": {"width": 1.5}},
            ),
        ]

    @property
    def layout(self) -> Dict:
        _layout: Dict[str, Any] = {}
        _layout.update(self._plotly_theme["layout"])
        _layout.update(
            {
                "height": self.figure_height,
                "barmode": "overlay",
                "margin": {"l": 0, "r": 0, "b": 20, "t": 0},
                "xaxis": {
                    "title": self._scale,
                    "autorange": True,
                    "showgrid": False,
                    "zeroline": False,
                    "showline": True,
                    "automargin": True,
                    "side": "top",
                },
                "yaxis": {
                    "autorange": True,
                    "showgrid": False,
                    "zeroline": False,
                    "showline": False,
                    "automargin": True,
                    "title": None,
                    "dtick": 1,
                },
                "showlegend": False,
                "hovermode": "y",
                "annotations": [
                    {
                        "x": 0,
                        "y": len(list(self._tornadotable["low"])) - 0.5,
                        "xref": "x",
                        "yref": "y",
                        "text": f"Reference avg: "
                        f"{self._set_si_prefix(self._reference_average)}",
                        "showarrow": True,
                        "align": "center",
                        "arrowhead": 2,
                        "arrowsize": 1,
                        "arrowwidth": 1,
                        "arrowcolor": "#636363",
                        "ax": 20,
                        "ay": -25,
                    }
                ],
            }
        )
        return _layout

    @property
    def figure(self) -> Dict:
        return {"data": self.data, "layout": self.layout}
