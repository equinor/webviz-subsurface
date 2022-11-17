from typing import Any, Dict, List

import plotly.graph_objects as go

from ......_utils.colors import find_intermediate_color, rgba_to_str
from ...._types import VfpParam
from ...._utils import VfpTable

RED = rgba_to_str((255, 18, 67, 1))
MID_COLOR = rgba_to_str((31, 119, 180, 1))
GREEN = rgba_to_str((62, 208, 62, 1))


class VfpFigureBuilder:
    """Class to build the VFP graph object"""

    def __init__(self, vfp_name: str) -> None:

        self._traces: List[Dict[str, Any]] = []
        self._layout = {
            "legend": {"orientation": "h"},
            "hovermode": "closest",
            "title": f"VFP table: {vfp_name}",
            "plot_bgcolor": "white",
        }

    def get_figure(self) -> Dict[str, Any]:
        return go.Figure(data=self._traces, layout=self._layout)

    def set_yaxis_settings(self, title: str, showgrid: bool = True) -> None:
        self._layout["yaxis"] = {"title": title, "showgrid": showgrid}

    def set_xaxis_settings(self, title: str, showgrid: bool = True) -> None:
        self._layout["xaxis"] = {"title": title, "showgrid": showgrid}

    def add_vfp_curve(
        self,
        rates: List[float],
        bhp_values: List[float],
        cmax: float,
        cmin: float,
        vfp_table: VfpTable,
        indices: Dict[VfpParam, int],
        color_by: VfpParam,
        showscale: bool,
    ) -> None:
        # pylint: disable=too-many-arguments
        """Adds one vfp trace to the vfp graph, formatted with
        color and hoverdata.

        Plotly apparently doesn't support colorscale on both markers and
        lines: https://github.com/plotly/plotly.js/issues/5259. So I needed
        to interpolate the line color manually in order to match the marker
        color.
        """
        cvalue = vfp_table.params[color_by][indices[color_by]]
        hovertext = "<br>".join(
            [
                f"{vfp_table.param_types[tpe].name}={vfp_table.params[tpe][idx]}"
                for tpe, idx in indices.items()
            ]
        )

        self._traces.append(
            {
                "x": rates,
                "y": bhp_values,
                "hovertext": hovertext,
                "hoverinfo": "y+x+text",
                "showlegend": False,
                "mode": "markers+lines",
                "marker": dict(
                    cmax=cmax,
                    cmin=cmin,
                    cmid=(cmin + cmax) / 2,
                    color=[cvalue] * len(rates),
                    colorscale=[[0, RED], [0.5, MID_COLOR], [1, GREEN]],
                    showscale=showscale,
                    colorbar={"title": vfp_table.param_types[color_by].value},
                ),
                "line": {"color": _get_color(cmax, cmin, cvalue)},
            }
        )


def _get_color(cmax: float, cmin: float, cvalue: float) -> str:
    """Returns an interpolated color"""
    if cmax < cmin:
        raise ValueError("'cmax' must be equal to or larger than 'cmin'")
    if cvalue < cmin or cvalue > cmax:
        raise ValueError("'cvalue' must be between 'cmin' and 'cmax'")
    if cmax == cmin:
        return MID_COLOR
    factor = (cvalue - cmin) / (cmax - cmin)
    if factor >= 0.5:
        return find_intermediate_color(MID_COLOR, GREEN, (factor - 0.5) / 0.5)
    return find_intermediate_color(RED, MID_COLOR, (factor) / 0.5)
