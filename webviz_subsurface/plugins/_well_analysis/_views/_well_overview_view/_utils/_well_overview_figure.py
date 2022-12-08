import datetime
import itertools
import math
from typing import Dict, List, Tuple, Union

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from webviz_config import WebvizConfigTheme

from ...._types import ChartType
from ...._utils import EnsembleWellAnalysisData


class WellOverviewFigure:
    def __init__(
        self,
        ensembles: List[str],
        data_models: Dict[str, EnsembleWellAnalysisData],
        sumvec: str,
        prod_from_date: Union[datetime.datetime, None],
        prod_until_date: Union[datetime.datetime, None],
        charttype: ChartType,
        wells: List[str],
        theme: WebvizConfigTheme,
    ) -> None:
        # pylint: disable=too-many-arguments
        self._ensembles = ensembles
        self._data_models = data_models
        self._sumvec = sumvec
        self._prod_from_date = prod_from_date
        self._prod_until_date = prod_until_date
        self._charttype = charttype
        self._wells = wells
        self._colors = theme.plotly_theme["layout"]["colorway"]
        self._rows, self._cols = self.get_subplot_dim()
        spec_type = "scatter" if self._charttype == ChartType.AREA else self._charttype
        subplot_titles = None if self._charttype == ChartType.BAR else self._ensembles

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

    @property
    def figure(self) -> go.Figure:
        return self._figure

    def get_subplot_dim(self) -> Tuple[int, int]:
        """Returns the subplot dimensions of the currently selected chart type.
        Pie charts have two columns, while the other has one. Area charts have one
        row per ensemble.
        """
        number_of_ens = len(self._ensembles)
        if self._charttype == ChartType.BAR:
            return 2, 1
        if self._charttype == ChartType.PIE:
            return max(math.ceil(number_of_ens / 2), 2), 2
        if self._charttype == ChartType.AREA:
            return number_of_ens, 1
        raise ValueError(f"Chart type: {self._charttype.value} not implemented")

    def _get_ensemble_charttype_data(self, ensemble: str) -> pd.DataFrame:
        """Returns a dataframe with summary data on the form needed for the
        different chart types.
        """
        if self._charttype in [ChartType.BAR, ChartType.PIE]:
            df = self._data_models[ensemble].get_dataframe_melted(
                well_sumvec=self._sumvec,
                prod_from_date=self._prod_from_date,
                prod_until_date=self._prod_until_date,
            )
            df = df[df["WELL"].isin(self._wells)]
            df_mean = df.groupby("WELL").mean().reset_index()
            return df_mean[df_mean[self._sumvec] > 0]

        # else chart type == area
        df = self._data_models[ensemble].get_summary_data(
            well_sumvec=self._sumvec,
            prod_from_date=self._prod_from_date,
            prod_until_date=self._prod_until_date,
        )
        return df.groupby("DATE").mean().reset_index()

    def _add_traces(self) -> None:
        """Add all traces for the currently selected chart type."""
        wells_in_legend = []

        for i, ensemble in enumerate(self._ensembles):
            df = self._get_ensemble_charttype_data(ensemble)

            if self._charttype == ChartType.PIE:
                self._figure.add_trace(
                    go.Pie(
                        values=df[self._sumvec],
                        labels=df["WELL"],
                        marker_colors=self._colors,
                        textposition="inside",
                        texttemplate="%{label}",
                    ),
                    row=i // 2 + 1,
                    col=i % 2 + 1,
                )

            elif self._charttype == ChartType.BAR:
                trace = {
                    "x": df["WELL"],
                    "y": df[self._sumvec],
                    "orientation": "v",
                    "type": "bar",
                    "name": ensemble,
                    "marker": {"color": self._colors[i]},
                    "text": df[self._sumvec],
                    "textposition": "none",
                    "texttemplate": "%{text:.2s}",
                }

                self._figure.add_trace(
                    trace,
                    row=1,
                    col=1,
                )
            elif self._charttype == ChartType.AREA:
                color_iterator = itertools.cycle(self._colors)

                for well in self._data_models[ensemble].wells:
                    if well in self._wells:
                        showlegend = False
                        if well not in wells_in_legend:
                            showlegend = True
                            wells_in_legend.append(well)

                        self._figure.add_trace(
                            go.Scatter(
                                x=df["DATE"],
                                y=df[f"{self._sumvec}:{well}"],
                                hoverinfo="text+x+y",
                                hoveron="fills",
                                mode="lines",
                                stackgroup="one",
                                name=well,
                                line=dict(width=0.1, color=next(color_iterator)),
                                legendgroup="Wells",
                                showlegend=showlegend,
                            ),
                            row=i + 1,
                            col=1,
                        )


def format_well_overview_figure(
    figure: go.Figure,
    charttype: ChartType,
    settings: List[str],
    sumvec: str,
    prod_from_date: Union[str, None],
    prod_until_date: Union[str, None],
) -> go.Figure:
    """This function formate the well overview figure. The reason for keeping this
    function outside the figure class is that we can update the figure formatting
    without generating a new WellOverviewFigure object and reloading the data. It can
    be applied directly to the current state of the figure dict if only formatting
    settings are changed. See in the well_overview_callbacks how it is used.
    """

    if charttype == ChartType.PIE:
        figure.update_traces(
            texttemplate=(
                "%{label}<br>%{value:.2s}"
                if "show_prod_text" in settings
                else "%{label}"
            )
        )

    elif charttype == ChartType.BAR:
        figure.update_layout(
            barmode=("overlay" if "overlay_bars" in settings else "group")
        )
        figure.update_traces(
            textposition=("auto" if "show_prod_text" in settings else "none")
        )

    # These are valid for all chart types
    figure.update_layout(
        template=("plotly_white" if "white_background" in settings else "plotly")
    )

    # Make title
    phase = {"WOPT": "Oil", "WGPT": "Gas", "WWPT": "Water"}[sumvec]
    title = f"Cumulative Well {phase} Production (Sm3)"
    if prod_from_date is not None:
        title += f" from {prod_from_date}"
    if prod_until_date is not None:
        title += f" until {prod_until_date}"

    figure.update(
        layout_title_text=title,
        layout_showlegend=("legend" in settings),
    )
    return figure
