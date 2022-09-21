import json
import sys
from dataclasses import dataclass
from typing import List, Optional, Union

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from webviz_subsurface._components.tornado._tornado_bar_chart import TornadoBarChart
from webviz_subsurface._components.tornado._tornado_data import TornadoData

from ...shared_settings import FilterOption, Scale
from .view_elements import TornadoPlot

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated


class PlotOption(StrEnum):
    SHOW_REAL_POINTS = "show-real-points"
    COLOR_BARS_BY_SENS = "color-bars-by-sens"


class LabelOption(StrEnum):
    SIMPLE = "simple"
    DETAILED = "detailed"
    HIDE = "hide"


class PlotSettings(SettingsGroupABC):
    class IDs(StrEnum):
        PLOT_OPTIONS = "plot-options"
        LABEL = "label"

    def __init__(
        self,
    ) -> None:
        super().__init__("Plot settings")

    def layout(self) -> List[Component]:
        return [
            wcc.Checklist(
                id=self.register_component_unique_id(PlotSettings.IDs.PLOT_OPTIONS),
                label="Plot options",
                options=[
                    {
                        "label": "Show realization points",
                        "value": PlotOption.SHOW_REAL_POINTS,
                    },
                    {
                        "label": "Color bars by sensitivity",
                        "value": PlotOption.COLOR_BARS_BY_SENS,
                    },
                ],
                value=[],
                labelStyle={"display": "block"},
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(PlotSettings.IDs.LABEL),
                label="Label",
                options=[
                    {"label": "No label", "value": LabelOption.HIDE},
                    {
                        "label": "Simple label",
                        "value": LabelOption.SIMPLE,
                    },
                    {
                        "label": "Detailed label",
                        "value": LabelOption.DETAILED,
                    },
                ],
                value=LabelOption.DETAILED,
                clearable=False,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(PlotSettings.IDs.LABEL).to_string(),
                "disabled",
            ),
            Input(
                self.component_unique_id(PlotSettings.IDs.PLOT_OPTIONS).to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _disable_label(plot_options: Optional[List[PlotOption]]) -> bool:
            if plot_options is None:
                return False
            return PlotOption.SHOW_REAL_POINTS in plot_options


class TornadoPlotView(ViewABC):
    class IDs(StrEnum):
        TORNADO_PLOT = "tornado-plot"
        MAIN_COLUMN = "main-column"
        SETTINGS = "settings"

    @dataclass
    class Slots:
        reference: Annotated[Input, str]
        scale: Annotated[Input, str]
        filter_options: Annotated[Input, List[str]]
        data: Annotated[Input, Union[str, bytes, bytearray]]
        sens_filter: Annotated[Input, Union[List[str], str]]

    def __init__(
        self, design_matrix_df: pd.DataFrame, plotly_theme: dict, slots: Slots
    ) -> None:
        super().__init__("Tornado Plot View")

        self._design_matrix_df = design_matrix_df
        self._plotly_theme = plotly_theme
        self._slots = slots

        column = self.add_column(TornadoPlotView.IDs.MAIN_COLUMN)
        first_row = column.make_row()
        first_row.add_view_element(TornadoPlot(), TornadoPlotView.IDs.TORNADO_PLOT)

        self.add_settings_group(PlotSettings(), TornadoPlotView.IDs.SETTINGS)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(TornadoPlotView.IDs.TORNADO_PLOT)
                .component_unique_id(TornadoPlot.IDs.GRAPH)
                .to_string(),
                "figure",
            ),
            self._slots.reference,
            self._slots.scale,
            self._slots.filter_options,
            Input(
                self.settings_group(TornadoPlotView.IDs.SETTINGS)
                .component_unique_id(PlotSettings.IDs.PLOT_OPTIONS)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(TornadoPlotView.IDs.SETTINGS)
                .component_unique_id(PlotSettings.IDs.LABEL)
                .to_string(),
                "value",
            ),
            self._slots.data,
            self._slots.sens_filter,
        )
        @callback_typecheck
        def _calc_tornado_plot(
            reference: str,
            scale: Scale,
            filter_options: List[FilterOption],
            plot_options: Optional[List[PlotOption]],
            label_option: LabelOption,
            data: Union[str, bytes, bytearray],
            sens_filter: Union[List[str], str],
        ) -> dict:
            if not data:
                raise PreventUpdate
            plot_options = plot_options if plot_options else []
            data = json.loads(data)
            if not isinstance(sens_filter, List):
                sens_filter = [sens_filter]
            if not isinstance(data, dict):
                raise PreventUpdate

            values = pd.DataFrame(data["data"], columns=["REAL", "VALUE"])
            realizations = self._design_matrix_df.loc[
                self._design_matrix_df["ENSEMBLE"] == data["ENSEMBLE"]
            ]

            design_and_responses = pd.merge(values, realizations, on="REAL")
            if sens_filter is not None:
                if reference not in sens_filter:
                    sens_filter.append(reference)
                design_and_responses = design_and_responses.loc[
                    design_and_responses["SENSNAME"].isin(sens_filter)
                ]

            tornado_data = TornadoData(
                dframe=design_and_responses,
                response_name=data.get("response_name"),
                reference=reference,
                scale="Percentage" if scale == Scale.REL_VALUE_PERC else "Absolute",
                cutbyref=FilterOption.REMOVE_SENS_WITH_NO_IMPACT in filter_options,
            )

            tornado_figure = TornadoBarChart(
                tornado_data=tornado_data,
                plotly_theme=self._plotly_theme,
                label_options=label_option,
                number_format=data.get("number_format", ""),
                unit=data.get("unit", ""),
                spaced=data.get("spaced", True),
                locked_si_prefix=data.get("locked_si_prefix", None),
                use_true_base=scale == Scale.TRUE_VALUE,
                show_realization_points=PlotOption.SHOW_REAL_POINTS in plot_options,
                color_by_sensitivity=PlotOption.COLOR_BARS_BY_SENS in plot_options,
            )
            return tornado_figure.figure
