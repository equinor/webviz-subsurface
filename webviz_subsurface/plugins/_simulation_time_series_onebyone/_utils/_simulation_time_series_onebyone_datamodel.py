import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
from webviz_config import WebvizSettings

from webviz_subsurface._components.tornado._tornado_bar_chart import TornadoBarChart
from webviz_subsurface._components.tornado._tornado_data import TornadoData
from webviz_subsurface._components.tornado._tornado_table import TornadoTable
from webviz_subsurface._figures import TimeSeriesFigure, create_figure
from webviz_subsurface._models.parameter_model import ParametersModel
from webviz_subsurface._providers import EnsembleSummaryProvider, Frequency
from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)

from ._datetime_utils import date_from_str, date_to_str


class SimulationTimeSeriesOneByOneDataModel:
    """Class keeping the data needed in the vizualisations and various
    data providing methods.
    """

    SELECTORS = ["QC_FLAG", "SATNUM", "EQLNUM", "FIPNUM"]

    def __init__(
        self,
        provider_set: EnsembleSummaryProviderSet,
        parametermodel: ParametersModel,
        webviz_settings: WebvizSettings,
        resampling_frequency: Frequency,
        initial_vector: Optional[str],
    ) -> None:
        self._theme = webviz_settings.theme
        self._pmodel = parametermodel
        self._provider_set = provider_set
        self._vectors = self._provider_set.all_vector_names()
        self._resampling_frequency = resampling_frequency

        self._parameter_df = parametermodel.sens_df.copy()

        def test(x: pd.Series) -> pd.Series:
            return x.apply(lambda v: list(x.unique()).index(v))

        self._parameter_df["t"] = self._parameter_df.groupby("SENSNAME")[
            "SENSCASE"
        ].transform(test)

        self._smry_meta = None
        self._senscolormap = {
            sens: color for sens, color in zip(self._pmodel.sensitivities, self.colors)
        }
        self._initial_vector = (
            initial_vector
            if initial_vector and initial_vector in self._vectors
            else self._vectors[0]
        )

    def create_vectors_statistics_df(self, dframe: pd.DataFrame) -> pd.DataFrame:
        cols = [x for x in self._parameter_df.columns if x != "REAL"]
        return dframe.groupby(["DATE"] + cols).mean().reset_index()

    @property
    def colors(self) -> list:
        return self._theme.plotly_theme["layout"]["colorway"] * 5

    @property
    def realizations(self) -> List[int]:
        return self._provider_set.all_realizations()

    @property
    def ensembles(self) -> List[str]:
        return self._provider_set.provider_names()

    @property
    def dates(self) -> List[datetime.datetime]:
        return self._provider_set.all_dates(
            resampling_frequency=self._resampling_frequency
        )

    @property
    def sensname_colormap(self) -> dict:
        return self._senscolormap

    def get_sensitivity_dataframe_for_ensemble(self, ensemble: str) -> pd.DataFrame:
        return self._parameter_df[self._parameter_df["ENSEMBLE"] == ensemble]

    def get_unique_sensitivities_for_ensemble(self, ensemble: str) -> list:
        df = self.get_sensitivity_dataframe_for_ensemble(ensemble)
        return list(df["SENSNAME"].unique())

    @staticmethod
    def get_tornado_reference(sensitivities: List[str], existing_reference: str) -> str:
        if existing_reference in sensitivities:
            return existing_reference
        if "rms_seed" in sensitivities:
            return "rms_seed"
        return sensitivities[0]

    def get_tornado_data(
        self, dframe: pd.DataFrame, response: str, selections: dict
    ) -> TornadoData:
        dframe.rename(columns={response: "VALUE"}, inplace=True)
        return TornadoData(
            dframe=dframe,
            reference=selections["Reference"],
            response_name=response,
            scale=selections["Scale"],
            cutbyref=bool(selections["Remove no impact"]),
        )

    def create_tornado_figure(
        self, tornado_data: TornadoData, selections: dict, use_si_format: bool
    ) -> tuple:
        return (
            TornadoBarChart(
                tornado_data=tornado_data,
                plotly_theme=self._theme.plotly_theme,
                label_options=selections["labeloptions"],
                number_format="#.3g",
                locked_si_prefix=None if use_si_format else "",
                use_true_base=selections["Scale"] == "True",
                show_realization_points=bool(selections["real_scatter"]),
                show_reference=selections["torn_ref"],
                color_by_sensitivity=selections["color_by_sens"],
                sensitivity_color_map=self.sensname_colormap,
            )
            .figure.update_xaxes(side="bottom", title=None)
            .update_layout(
                title_text=f"Tornadoplot for {tornado_data.response_name} <br>",
                margin={"t": 70},
            )
        )

    def create_realplot(self, tornado_data: TornadoData) -> go.Figure:
        df = tornado_data.real_df
        senscasecolors = {
            senscase: self.sensname_colormap[sensname]
            for senscase, sensname in zip(df["sensname_case"], df["sensname"])
        }

        return (
            create_figure(
                plot_type="bar",
                data_frame=df,
                x="REAL",
                y="VALUE",
                color="sensname_case",
                color_discrete_map=senscasecolors,
                barmode="overlay",
                custom_data=["casetype"],
                yaxis={"range": [df["VALUE"].min() * 0.7, df["VALUE"].max() * 1.1]},
                opacity=0.85,
            )
            .update_layout(legend={"orientation": "h", "yanchor": "bottom", "y": 1.02})
            .update_layout(legend_title_text="", margin_b=0, margin_r=10)
            .for_each_trace(
                lambda t: (
                    t.update(marker_line_color="black")
                    if t["customdata"][0][0] == "high"
                    else t.update(marker_line_color="white", marker_line_width=2)
                )
                if t["customdata"][0][0] != "mc"
                else None
            )
        )

    def create_tornado_table(
        self,
        tornado_data: TornadoData,
        use_si_format: bool,
    ) -> Tuple[List[dict], List[dict]]:
        tornado_table = TornadoTable(
            tornado_data=tornado_data,
            use_si_format=use_si_format,
            precision=4 if use_si_format else 3,
        )
        return tornado_table.as_plotly_table, tornado_table.columns

    def create_timeseries_figure(
        self,
        dframe: pd.DataFrame,
        vector: str,
        ensemble: str,
        date: str,
        visualization: str,
    ) -> go.Figure:
        return go.Figure(
            TimeSeriesFigure(
                dframe=dframe,
                visualization=visualization,
                vector=vector,
                ensemble=ensemble,
                dateline=date_from_str(date),
                historical_vector_df=self.vmodel.get_historical_vector_df(
                    vector, ensemble
                ),
                color_col="SENSNAME",
                line_shape_fallback=self.vmodel.line_shape_fallback,
                discrete_color_map=self.sensname_colormap,
                groupby="SENSNAME_CASE",
            ).figure
        ).update_layout({"title": f"{vector}, Date: {date}"})
