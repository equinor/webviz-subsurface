from typing import List, Dict

import numpy as np


class PlotlyLinePlot:
    def __init__(self) -> None:
        self._traces: List = []
        self._layout: Dict = {}

    def add_line(self, x: np.ndarray, y: np.ndarray) -> Dict:
        trace = {"type": "line", "x": x, "y": y}
        print(x)
        self._traces.append(trace)

    @property
    def figure(self) -> str:
        return dict(layout=self._layout, data=self._traces)
