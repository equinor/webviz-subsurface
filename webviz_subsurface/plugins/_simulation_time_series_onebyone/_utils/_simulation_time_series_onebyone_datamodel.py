import datetime
from typing import List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
from webviz_config import WebvizSettings

from webviz_subsurface._abbreviations.reservoir_simulation import historical_vector
from webviz_subsurface._components.tornado._tornado_bar_chart import TornadoBarChart
from webviz_subsurface._components.tornado._tornado_data import TornadoData
from webviz_subsurface._components.tornado._tornado_table import TornadoTable
from webviz_subsurface._figures import create_figure
from webviz_subsurface._models.parameter_model import ParametersModel
from webviz_subsurface._providers import EnsembleSummaryProvider, Frequency
from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)
from webviz_subsurface._utils.vector_selector import add_vector_to_vector_selector_data

from ._datetime_utils import date_from_str
from ._onebyone_timeseries_figure import OneByOneTimeSeriesFigure


class SimulationTimeSeriesOneByOneDataModel:
    """Class keeping the data needed in the vizualisations and various
    data providing methods.
    """

    def __init__(
        self,
        provider_set: EnsembleSummaryProviderSet,
        parametermodel: ParametersModel,
        webviz_settings: WebvizSettings,
        resampling_frequency: Frequency,
        line_shape_fallback: str,
        initial_vector: Optional[str],
    ) -> None:
        self._theme = webviz_settings.theme
        self._pmodel = parametermodel
        self._provider_set = provider_set
        self._vectors = self._provider_set.all_vector_names()
        self._resampling_frequency = resampling_frequency
        self._line_shape_fallback = line_shape_fallback
        self._parameter_df = parametermodel.sens_df.copy()

        def create_senscase_id(x: pd.Series) -> pd.Series:
            return x.apply(lambda v: list(x.unique()).index(v))

        self._parameter_df["SENSCASEID"] = self._parameter_df.groupby("SENSNAME")[
            "SENSCASE"
        ].transform(create_senscase_id)

        self._smry_meta = None
        self._senscolormap = dict(zip(self._pmodel.sensitivities, self.colors))

        self.initial_vector = (
            initial_vector
            if initial_vector and initial_vector in self._vectors
            else self._vectors[0]
        )
        self.initial_vector_selector_data = create_vector_selector_data(self._vectors)

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
    def vectors(self) -> List[str]:
        return self._vectors

    @property
    def ensembles(self) -> List[str]:
        return self._provider_set.provider_names()

    @property
    def all_dates(self) -> List[datetime.datetime]:
        return self._provider_set.all_dates(
            resampling_frequency=self._resampling_frequency
        )

    @property
    def sensname_colormap(self) -> dict:
        return self._senscolormap

    @property
    def sensitivities(self) -> List[str]:
        return self._pmodel.sensitivities

    def ensemble_dates(self, ensemble: str) -> List[datetime.datetime]:
        return self._provider_set.provider(ensemble).dates(
            resampling_frequency=self._resampling_frequency
        )

    def provider(self, ensemble: str) -> EnsembleSummaryProvider:
        return self._provider_set.provider(ensemble)

    def get_vectors_df(
        self,
        ensemble: str,
        vector_names: List[str],
        realizations: Optional[List[int]] = None,
        date: Optional[datetime.datetime] = None,
    ) -> pd.DataFrame:
        provider = self._provider_set.provider(ensemble)
        if date is None:
            return provider.get_vectors_df(
                vector_names=vector_names,
                realizations=realizations,
                resampling_frequency=self._resampling_frequency,
            )
        return provider.get_vectors_for_date_df(
            date=date,
            vector_names=vector_names,
            realizations=realizations,
        )

    def get_historical_vector_df(
        self, vector: str, ensemble: str
    ) -> Optional[pd.DataFrame]:
        hist_vecname = historical_vector(vector, smry_meta=None)
        provider = self.provider(ensemble)
        if hist_vecname and hist_vecname in provider.vector_names():
            return provider.get_vectors_df(
                [hist_vecname], None, realizations=provider.realizations()[:1]
            ).rename(columns={hist_vecname: vector})
        return None

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

    @staticmethod
    def get_realizations_for_sensitivies(
        sens_df: pd.DataFrame, sensitivities: List[str]
    ) -> List[int]:
        return list(sens_df[sens_df["SENSNAME"].isin(sensitivities)]["REAL"].unique())

    def create_tornado_figure(
        self,
        tornado_data: TornadoData,
        selections: dict,
        use_si_format: bool,
        title: Optional[str],
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
                title_text=title
                if title is not None
                else f"Tornadoplot for {tornado_data.response_name} <br>",
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

    def create_timeseries_figure(
        self,
        dframe: pd.DataFrame,
        vector: str,
        ensemble: str,
        date: str,
        visualization: str,
    ) -> go.Figure:
        return go.Figure(
            OneByOneTimeSeriesFigure(
                dframe=dframe,
                visualization=visualization,
                vector=vector,
                ensemble=ensemble,
                dateline=date_from_str(date),
                historical_vector_df=self.get_historical_vector_df(
                    vector=vector, ensemble=ensemble
                ),
                color_col="SENSNAME",
                line_shape_fallback=self._line_shape_fallback,
                discrete_color_map=self.sensname_colormap,
                groupby="SENSNAME_CASE",
            ).figure
        ).update_layout({"title": f"{vector}"})


def get_tornado_data(
    dframe: pd.DataFrame, response: str, selections: dict
) -> TornadoData:
    dframe.rename(columns={response: "VALUE"}, inplace=True)
    return TornadoData(
        dframe=dframe,
        reference=selections["Reference"],
        response_name=response,
        scale=selections["Scale"],
        cutbyref=bool(selections["Remove no impact"]),
    )


def create_tornado_table(
    tornado_data: TornadoData,
    use_si_format: bool,
) -> Tuple[List[dict], List[dict]]:
    tornado_table = TornadoTable(
        tornado_data=tornado_data,
        use_si_format=use_si_format,
        precision=4 if use_si_format else 3,
    )
    return tornado_table.as_plotly_table, tornado_table.columns


def create_vector_selector_data(vector_names: list) -> list:
    vector_selector_data: list = []
    for vector in _get_non_historical_vector_names(vector_names):
        add_vector_to_vector_selector_data(vector_selector_data, vector)
    return vector_selector_data


def _get_non_historical_vector_names(vector_names: list) -> list:
    return [
        vector
        for vector in vector_names
        if historical_vector(vector, None, False) not in vector_names
    ]
