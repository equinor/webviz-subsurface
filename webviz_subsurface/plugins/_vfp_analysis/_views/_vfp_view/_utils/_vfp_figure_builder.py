from typing import Any, Dict, List


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
        return {"data": self._traces, "layout": self._layout}

    def add_vfp_curve(self, rates: List[float], bhp_values: List[float]) -> None:
        """Descr"""
        color = "#1f77b4"
        self._traces.append(
            {
                "x": rates,
                "y": bhp_values,
                # "hovertext": tracelabel,
                # "name": name,
                "showlegend": False,
                "mode": "lines",
                "line": {"color": color},
            }
        )
