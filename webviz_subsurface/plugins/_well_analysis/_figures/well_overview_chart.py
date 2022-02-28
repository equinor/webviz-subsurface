import itertools
import math
from typing import Dict, List, Tuple

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
        self._rows, self._cols = self.get_subplot_dim()
        spec_type = "scatter" if self._charttype == "area" else self._charttype
        subplot_titles = None if self._charttype == "bar" else self._ensembles

        self._figure = make_subplots(
            rows=self._rows,
            cols=self._cols,
            specs=[
                [{"type": spec_type} for _ in range(self._cols)]
                for _ in range(self._rows)
            ],
            subplot_titles=subplot_titles,
        )

        self._add_traces()
        self._update_figure()

    @property
    def figure(self) -> go.Figure:
        return self._figure

    def get_subplot_dim(self) -> Tuple[int, int]:
        """descr"""
        number_of_ens = len(self._ensembles)
        if self._charttype == "bar":
            return 2, 1
        if self._charttype == "pie":
            return max(math.ceil(number_of_ens / 2), 2), 2
        if self._charttype == "area":
            return number_of_ens, 1

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

            if self._charttype == "pie":
                df = self._data_models[ensemble].get_dataframe_melted(self._sumvec)
                df_mean = df.groupby("WELL").mean().reset_index()
                df_mean = df_mean[df_mean[self._sumvec] > 0]

                self._figure.add_trace(
                    go.Pie(
                        values=df[self._sumvec],
                        labels=df["WELL"],
                        # title=f"{ensemble}",
                        marker_colors=self._colors,
                    ),
                    row=i // 2 + 1,
                    col=i % 2 + 1,
                )
            elif self._charttype == "bar":
                df = self._data_models[ensemble].get_dataframe_melted(self._sumvec)
                df_mean = df.groupby("WELL").mean().reset_index()
                df_mean = df_mean[df_mean[self._sumvec] > 0]

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
            elif self._charttype == "area":
                color_iterator = itertools.cycle(self._colors)
                df = self._data_models[ensemble].summary_data
                df_mean = df.groupby("DATE").mean().reset_index()
                for well in self._data_models[ensemble].wells:

                    self._figure.add_trace(
                        go.Scatter(
                            x=df_mean["DATE"],
                            y=df_mean[f"{self._sumvec}:{well}"],
                            hoverinfo="text+x+y",
                            hoveron="fills",
                            mode="lines",
                            stackgroup="one",
                            name=well,
                            line=dict(width=0.1, color=next(color_iterator)),
                        ),
                        row=i + 1,
                        col=1,
                    )
