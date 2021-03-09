from typing import List, Dict

import numpy as np


class PlotlyLineFigure:
    def __init__(self) -> None:
        self._traces: List[Dict] = []
        self._layout: Dict = {}

    def add_line(self, x_values: np.ndarray, y_values: np.ndarray) -> None:
        trace = {"type": "line", "x": x_values, "y": y_values}
        self._traces.append(trace)

    @property
    def figure(self) -> Dict:
        return {"layout": self._layout, "data": self._traces}
