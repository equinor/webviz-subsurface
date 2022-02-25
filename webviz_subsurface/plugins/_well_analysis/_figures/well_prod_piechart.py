import math
from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .._ensemble_data import EnsembleWellAnalysisData


class WellProdPieChart:
    def __init__(
        self,
        ensembles: List[str],
        data_models: Dict[str, EnsembleWellAnalysisData],
        sumvec: str,
    ) -> None:

        self._ensembles = ensembles
        self._data_models = data_models
        self._sumvec = sumvec

        rows = max(math.ceil(len(ensembles) / 2), 2)
        self._figure = make_subplots(
            rows=rows,
            cols=2,
            specs=[[{"type": "pie"}, {"type": "pie"}] for _ in range(rows)],
        )

        for i, ensemble in enumerate(self._ensembles):
            row = (i) // 2 + 1
            col = i % 2 + 1
            self._figure.add_trace(self._create_piechart(ensemble), row=row, col=col)

        self._figure.update_traces(textinfo="label", textposition="inside")
        self._figure.update(
            layout_title_text="Cumulative Well Production Pie Charts",
            layout_showlegend=False,
        )

    def figure(self) -> go.Figure:
        return self._figure

    def _create_piechart(self, ensemble) -> go.Pie:
        """descr"""
        df = self._data_models[ensemble].get_dataframe_melted(self._sumvec)
        df_mean = df.groupby("WELL").mean().reset_index()
        df_mean = df_mean[df_mean[self._sumvec] > 0]

        return go.Pie(
            values=df[self._sumvec],
            labels=df["WELL"],
            title=f"{ensemble}",
        )
