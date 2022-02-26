import math
from typing import Dict, List

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from webviz_config import WebvizConfigTheme

from .._ensemble_data import EnsembleWellAnalysisData


class WellOverviewChart:
    def __init__(
        self,
        ensembles: List[str],
        data_models: Dict[str, EnsembleWellAnalysisData],
        sumvec: str,
        charttype: str,  # bar, pie, area
        settings: List[str],
        theme: WebvizConfigTheme,
    ) -> None:

        self._ensembles = ensembles
        self._data_models = data_models
        self._sumvec = sumvec
        self._charttype = charttype
        self._settings = settings
        self._colors = theme.plotly_theme["layout"]["colorway"]
        self._cols = min(len(ensembles), 2) if charttype == "pie" else 1
        self._rows = max(math.ceil(len(ensembles) / self._cols), 2)
        self._figure = make_subplots(
            rows=self._rows,
            cols=self._cols,
            specs=[
                [{"type": self._charttype} for _ in range(self._cols)]
                for _ in range(self._rows)
            ],
        )

        self._add_traces()
        self._update_figure()

    @property
    def figure(self) -> go.Figure:
        return self._figure

    def _update_figure(self) -> None:
        """descr"""
        if self._charttype == "pie":
            self._figure.update_traces(textinfo="label", textposition="inside")
        elif self._charttype == "bar":
            barmode = "overlay" if "overlay" in self._settings else "group"
            self._figure.update_layout(barmode=barmode)

        self._figure.update(
            layout_title_text="Cumulative Well Production",
            layout_showlegend=("legend" in self._settings),
        )

    def _add_traces(self) -> None:
        """descr"""

        for i, ensemble in enumerate(self._ensembles):
            df = self._data_models[ensemble].get_dataframe_melted(self._sumvec)
            df_mean = df.groupby("WELL").mean().reset_index()
            df_mean = df_mean[df_mean[self._sumvec] > 0]

            if self._charttype == "pie":
                self._figure.add_trace(
                    go.Pie(
                        values=df[self._sumvec],
                        labels=df["WELL"],
                        title=f"{ensemble}",
                        marker_colors=self._colors,
                    ),
                    row=i // 2 + 1,
                    col=i % 2 + 1,
                )
            elif self._charttype == "bar":
                self._figure.add_trace(
                    {
                        "x": df_mean["WELL"],
                        "y": df_mean[self._sumvec],
                        # "text": df_mean["TEXT"],
                        "orientation": "v",
                        "type": "bar",
                        "name": ensemble,
                        "marker": {"color": self._colors[i]},
                        # "textposition": textposition,
                    },
                    row=1,
                    col=1,
                )
