from typing import List, Dict

import numpy as np


class PlotlyLinePlot:
    def __init__(self) -> None:
        self._traces: List = []
        self._layout: Dict = {}

    def add_line(self, x: np.ndarray, y: np.ndarray) -> None:
        trace = {"type": "line", "x": x, "y": y}
        self._traces.append(trace)

    def add_observations(self, observations: dict, x_value: str) -> None:
        self._traces.extend(
            [
                {
                    "x": [value.get(x_value), []],
                    "y": [value.get("value"), []],
                    "marker": {"color": "black"},
                    "text": value.get("comment", None),
                    "hoverinfo": "y+x+text",
                    "showlegend": False,
                    "error_y": {
                        "type": "data",
                        "array": [value.get("error"), []],
                        "visible": True,
                    },
                }
                for value in observations
            ]
        )

    @property
    def figure(self) -> str:
        return dict(layout=self._layout, data=self._traces)
