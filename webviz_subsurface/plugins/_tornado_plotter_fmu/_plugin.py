import json
from pathlib import Path
from typing import List, Type

from dash import ALL, Input, Output, callback, callback_context
from dash.development.base_component import Component
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum, callback_typecheck

from webviz_subsurface._datainput.fmu_input import find_sens_type
from webviz_subsurface._providers import EnsembleTableProviderFactory

from ._error import error
from .shared_settings import Filters, Selectors, ViewSettings
from .views.plot_view import PlotSettings, TornadoPlotView
from .views.table_view import TornadoTableView


class TornadoPlotterFMU(WebvizPluginABC):
    """Tornado plotter for FMU data from csv file og responses
    * **`ensemble`:** Which ensemble in `shared_settings` to visualize.
    * **`csvfile`:** Relative ensemble path to csv file with responses
    * **`aggregated_csvfile`:** Alternative to ensemble + csvfile with
    aggregated responses. Requires REAL and ENSEMBLE columns
    * **`aggregated_parameterfile`:** Necessary when aggregated_csvfile
    is specified. File with sensitivity specification for each realization.
    Requires columns REAL, ENSEMBLE, SENSNAME and SENSCASE.
    * **`initial_response`:** Initialize plugin with this response column
    visualized
    * **`single_value_selectors`:** List of columns in response csv file
    that should be used to select/filter data. E.g. for UNSMRY data the DATE
    column can be used. For each entry a Dropdown is shown with all unique
    values and a single value can be selected at a time.
    * **`multi_value_selectors`:** List of columns in response csv file
    to filter/select data. For each entry a Select is shown with
    all unique values. Multiple values can be selected at a time,
    and a tornado plot will be shown from the matching response rows.
    Used e.g. for volumetrics data, to select a subset of ZONES and
    REGIONS.
    """

    class Ids(StrEnum):
        TORNADO_DATA = "tornado-data"

        SELECTORS = "selectors"
        FILTERS = "filters"
        VIEW_SETTINGS = "view-settings"

        TORNADO_PLOT_VIEW = "tornado-plot-view"
        TORNADO_TABLE_VIEW = "tornado-table-view"

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        webviz_settings: WebvizSettings,
        csvfile: str = None,
        ensemble: str = None,
        aggregated_csvfile: Path = None,
        aggregated_parameterfile: Path = None,
        initial_response: str = None,
        single_value_selectors: List[str] = None,
        multi_value_selectors: List[str] = None,
    ) -> None:
        super().__init__(stretch=True)

        self._single_filters = single_value_selectors if single_value_selectors else []
        self._multi_filters = multi_value_selectors if multi_value_selectors else []

        provider_factory = EnsembleTableProviderFactory.instance()
        self._error_message = ""

        self._ensemble_name = ""

        if ensemble is not None and csvfile is not None:
            ens_path = webviz_settings.shared_settings["scratch_ensembles"][ensemble]
            self._parameter_provider = (
                provider_factory.create_from_per_realization_parameter_file(ens_path)
            )
            self._table_provider = (
                provider_factory.create_from_per_realization_csv_file(ens_path, csvfile)
            )
            ensemble_name = ensemble

        elif aggregated_csvfile and aggregated_parameterfile is not None:
            self._parameter_provider = provider_factory.create_from_ensemble_csv_file(
                aggregated_parameterfile
            )
            self._table_provider = provider_factory.create_from_ensemble_csv_file(
                aggregated_csvfile
            )
            try:
                self._ensemble_name = self._table_provider.get_column_data(
                    column_names=["ENSEMBLE"]
                )
            except KeyError:
                self._error_message = f"'ENSEMBLE' is missing from {aggregated_csvfile}"

        else:
            self._error_message = (
                "Specify either ensembles and csvfile or aggregated_csvfile "
                "and aggregated_parameterfile"
            )

        try:
            design_matrix_df = self._parameter_provider.get_column_data(
                column_names=["SENSNAME", "SENSCASE"]
            )
        except KeyError:
            self._error_message = (
                "Required columns 'SENSNAME' and 'SENSCASE' is missing "
                f"from {ensemble_name}. Cannot calculate tornado plots"
            )

        design_matrix_df["ENSEMBLE"] = self._ensemble_name
        design_matrix_df["SENSTYPE"] = design_matrix_df.apply(
            lambda row: find_sens_type(row.SENSCASE), axis=1
        )

        responses: List[str] = self._table_provider.column_names()
        if self._single_filters:
            responses = [
                response
                for response in responses
                if response not in self._single_filters
            ]
        if self._multi_filters:
            responses = [
                response
                for response in responses
                if response not in self._multi_filters
            ]

        initial_response = initial_response if initial_response else responses[0]

        self.add_store(
            TornadoPlotterFMU.Ids.TORNADO_DATA,
            WebvizPluginABC.StorageType.SESSION,
        )

        self.add_shared_settings_group(
            Selectors(responses, initial_response),
            TornadoPlotterFMU.Ids.SELECTORS,
        )

        self.filters = Filters(
            self._table_provider,
            self._single_filters,
            self._multi_filters,
        )
        self.add_shared_settings_group(
            self.filters,
            TornadoPlotterFMU.Ids.FILTERS,
        )

        self.add_shared_settings_group(
            ViewSettings(design_matrix_df), TornadoPlotterFMU.Ids.VIEW_SETTINGS
        )

        self.add_view(
            TornadoPlotView(
                design_matrix_df,
                webviz_settings.theme.plotly_theme,
                TornadoPlotView.Slots(
                    reference=Input(
                        self.shared_settings_group(TornadoPlotterFMU.Ids.VIEW_SETTINGS)
                        .component_unique_id(ViewSettings.IDs.REFERENCE)
                        .to_string(),
                        "value",
                    ),
                    scale=Input(
                        self.shared_settings_group(TornadoPlotterFMU.Ids.VIEW_SETTINGS)
                        .component_unique_id(ViewSettings.IDs.SCALE)
                        .to_string(),
                        "value",
                    ),
                    filter_options=Input(
                        self.shared_settings_group(TornadoPlotterFMU.Ids.VIEW_SETTINGS)
                        .component_unique_id(ViewSettings.IDs.FILTER_OPTIONS)
                        .to_string(),
                        "value",
                    ),
                    data=Input(
                        self.get_store_unique_id(TornadoPlotterFMU.Ids.TORNADO_DATA),
                        "data",
                    ),
                    sens_filter=Input(
                        self.shared_settings_group(TornadoPlotterFMU.Ids.VIEW_SETTINGS)
                        .component_unique_id(ViewSettings.IDs.SENSITIVITIES)
                        .to_string(),
                        "value",
                    ),
                ),
            ),
            TornadoPlotterFMU.Ids.TORNADO_PLOT_VIEW,
        )

        self.add_view(
            TornadoTableView(
                design_matrix_df,
                TornadoTableView.Slots(
                    reference=Input(
                        self.shared_settings_group(TornadoPlotterFMU.Ids.VIEW_SETTINGS)
                        .component_unique_id(ViewSettings.IDs.REFERENCE)
                        .to_string(),
                        "value",
                    ),
                    scale=Input(
                        self.shared_settings_group(TornadoPlotterFMU.Ids.VIEW_SETTINGS)
                        .component_unique_id(ViewSettings.IDs.SCALE)
                        .to_string(),
                        "value",
                    ),
                    filter_options=Input(
                        self.shared_settings_group(TornadoPlotterFMU.Ids.VIEW_SETTINGS)
                        .component_unique_id(ViewSettings.IDs.FILTER_OPTIONS)
                        .to_string(),
                        "value",
                    ),
                    data=Input(
                        self.get_store_unique_id(TornadoPlotterFMU.Ids.TORNADO_DATA),
                        "data",
                    ),
                    sens_filter=Input(
                        self.shared_settings_group(TornadoPlotterFMU.Ids.VIEW_SETTINGS)
                        .component_unique_id(ViewSettings.IDs.SENSITIVITIES)
                        .to_string(),
                        "value",
                    ),
                ),
            ),
            TornadoPlotterFMU.Ids.TORNADO_TABLE_VIEW,
        )

    def _set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(TornadoPlotterFMU.Ids.TORNADO_DATA),
                "data",
            ),
            Input(
                self.shared_settings_group(TornadoPlotterFMU.Ids.SELECTORS)
                .component_unique_id(Selectors.IDs.RESPONSE)
                .to_string(),
                "value",
            ),
            Input(
                {
                    "id": self.filters.single_filter_id,
                    "name": ALL,
                    "type": "single_filter",
                },
                "value",
            ),
            Input(
                {
                    "id": self.filters.multi_filter_id,
                    "name": ALL,
                    "type": "multi_filter",
                },
                "value",
            ),
        )
        @callback_typecheck
        def _update_tornado_data_with_response_values(
            response: str, single_filters: list, multi_filters: list
        ) -> str:
            """Returns a json dump for the tornado data with the response values per realization"""

            data = self._table_provider.get_column_data(
                [response] + self._single_filters + self._multi_filters
            )

            # Filter data
            if single_filters is not None:
                for value, input_dict in zip(
                    single_filters, callback_context.inputs_list[1]
                ):
                    data = data.loc[data[input_dict["id"]["name"]] == value]
            if multi_filters is not None:
                for value, input_dict in zip(
                    multi_filters, callback_context.inputs_list[2]
                ):
                    data = data.loc[data[input_dict["id"]["name"]].isin(value)]

            return json.dumps(
                {
                    "ENSEMBLE": self._ensemble_name,
                    "data": data.groupby("REAL")
                    .sum()
                    .reset_index()[["REAL", response]]
                    .values.tolist(),
                    "number_format": "#.4g",
                }
            )

    @property
    def tour_steps(self) -> List[dict]:
        """Tour of the plugin"""
        tour = [
            {
                "id": self.view(TornadoPlotterFMU.Ids.TORNADO_PLOT_VIEW)
                .layout_element(TornadoPlotView.IDs.MAIN_COLUMN)
                .get_unique_id(),
                "content": ("Shows tornado plot."),
            },
            {
                "id": self.shared_settings_group(
                    TornadoPlotterFMU.Ids.SELECTORS
                ).component_unique_id(Selectors.IDs.RESPONSE),
                "content": "Choose the response for the data",
            },
        ]
        if len(self._single_filters) > 0:
            tour.append(
                {
                    "id": self.shared_settings_group(
                        TornadoPlotterFMU.Ids.FILTERS
                    ).component_unique_id(Filters.IDs.SINGLE_FILTER),
                    "content": "Choose the response for the data",
                }
            )
        if len(self._multi_filters) > 0:
            tour.append(
                {
                    "id": self.shared_settings_group(
                        TornadoPlotterFMU.Ids.FILTERS
                    ).component_unique_id(Filters.IDs.MULTI_FILTER),
                    "content": "Choose the response for the data",
                }
            )

        tour.extend(
            [
                {
                    "id": self.shared_settings_group(
                        TornadoPlotterFMU.Ids.VIEW_SETTINGS
                    ).component_unique_id(ViewSettings.IDs.REFERENCE),
                    "content": (
                        "Set reference sensitivity for which to calculate tornado plot"
                    ),
                },
                {
                    "id": self.shared_settings_group(
                        TornadoPlotterFMU.Ids.VIEW_SETTINGS
                    ).component_unique_id(ViewSettings.IDs.SCALE),
                    "content": (
                        "Set tornadoplot scale to either percentage or absolute values"
                    ),
                },
                {
                    "id": self.shared_settings_group(
                        TornadoPlotterFMU.Ids.VIEW_SETTINGS
                    ).component_unique_id(ViewSettings.IDs.SENSITIVITIES),
                    "content": ("Pick sensitivities to be displayed"),
                },
                {
                    "id": self.view(TornadoPlotterFMU.Ids.TORNADO_PLOT_VIEW)
                    .settings_group(TornadoPlotView.IDs.SETTINGS)
                    .component_unique_id(PlotSettings.IDs.PLOT_OPTIONS),
                    "content": "Options for dispaying the bars",
                },
                {
                    "id": self.view(TornadoPlotterFMU.Ids.TORNADO_PLOT_VIEW)
                    .settings_group(TornadoPlotView.IDs.SETTINGS)
                    .component_unique_id(PlotSettings.IDs.LABEL),
                    "content": "Plick settings for the label at the bars",
                },
            ]
        )
        return tour

    @property
    def layout(self) -> Type[Component]:
        return error(self._error_message)
