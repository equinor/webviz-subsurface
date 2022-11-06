from typing import Any, Dict, List

import plotly.graph_objects as go


class VfpFigureBuilder:
    """Descr"""

    def __init__(self, vfp_name: str) -> None:

        self._traces: List[Dict[str, Any]] = []
        self._layout = {
            "yaxis": {"title": "BHP", "showgrid": True},
            "xaxis": {"title": "Rate", "showgrid": True},
            "legend": {"orientation": "h"},
            "hovermode": "closest",
            "title": f"{vfp_name}",
        }

    def get_figure(self) -> Dict[str, Any]:
        return go.Figure(data=self._traces, layout=self._layout)
        # return {"data": self._traces, "layout": self._layout}

    def add_vfp_curve(
        self,
        rates: List[float],
        bhp_values: List[float],
        cmax: float,
        cmin: float,
        cvalue: float,
    ) -> None:
        """Descr"""
        #color = "#1f77b4"
        cvalues = [cvalue] * len(rates)
        self._traces.append(
            {
                "x": rates,
                "y": bhp_values,
                # "hovertext": tracelabel,
                # "name": name,
                "showlegend": False,
                "mode": "lines",
                "marker_line": dict(
                    cmax=cmax,
                    cmin=cmin,
                    color=cvalues,
                    colorscale="Viridis",
                    autocolorscale=False,
                    cauto=False,
                )
                # "line": {"color": color},
            }
        )
