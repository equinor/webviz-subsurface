from typing import List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go

from webviz_config import WebvizSettings

from webviz_subsurface._figures import TimeSeriesFigure
from webviz_subsurface._components.tornado._tornado_bar_chart import TornadoBarChart
from webviz_subsurface._components.tornado._tornado_data import TornadoData
from webviz_subsurface._components.tornado._tornado_table import TornadoTable
from webviz_subsurface._models.parameter_model import ParametersModel
from webviz_subsurface._figures import create_figure
from .models import ProviderTimeSeriesDataModel
from ._utils import datetime_utils


class SimulationTimeSeriesOneByOneDataModel:
    """Class keeping the data needed in the vizualisations and various
    data providing methods.
    """

    SELECTORS = ["QC_FLAG", "SATNUM", "EQLNUM", "FIPNUM"]

    def __init__(
        self,
        vectormodel: ProviderTimeSeriesDataModel,
        parametermodel: ParametersModel,
        webviz_settings: WebvizSettings,
        initial_vector: Optional[str],
    ) -> None:

        self.theme = webviz_settings.theme
        self.pmodel = parametermodel
        self.vmodel = vectormodel

        self.parameter_df = parametermodel.sens_df.copy()

        def test(x: pd.Series) -> pd.Series:
            return x.apply(lambda v: list(x.unique()).index(v))

        self.parameter_df["t"] = self.parameter_df.groupby("SENSNAME")[
            "SENSCASE"
        ].transform(test)

        self.smry_meta = None
        self._senscolormap = {
            sens: color for sens, color in zip(self.pmodel.sensitivities, self.colors)
        }
        self.initial_vector = (
            initial_vector
            if initial_vector and initial_vector in vectormodel.vectors
            else vectormodel.vectors[0]
        )

    def create_vectors_statistics_df(self, dframe: pd.DataFrame) -> pd.DataFrame:
        cols = [x for x in self.parameter_df.columns if x != "REAL"]
        return dframe.groupby(["DATE"] + cols).mean().reset_index()

    @property
    def colors(self) -> list:
        return self.theme.plotly_theme["layout"]["colorway"] * 5

    @property
    def realizations(self) -> List[int]:
        return list(self.parameter_df["REAL"].unique())

    @property
    def ensembles(self) -> List[str]:
        return list(self.parameter_df["ENSEMBLE"].unique())

    @property
    def sensname_colormap(self) -> dict:
        return self._senscolormap

    def get_sensitivity_dataframe_for_ensemble(self, ensemble: str) -> pd.DataFrame:
        return self.parameter_df[self.parameter_df["ENSEMBLE"] == ensemble]

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
                plotly_theme=self.theme.plotly_theme,
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
                dateline=datetime_utils.from_str(date),
                historical_vector_df=self.vmodel.get_historical_vector_df(
                    vector, ensemble
                ),
                color_col="SENSNAME",
                line_shape_fallback=self.vmodel.line_shape_fallback,
                discrete_color_map=self.sensname_colormap,
                groupby="SENSNAME_CASE",
            ).figure
        ).update_layout({"title": f"{vector}, Date: {date}"})
