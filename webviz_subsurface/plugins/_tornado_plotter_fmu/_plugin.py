from pathlib import Path
from typing import List, Type

from dash.development.base_component import Component
from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._datainput.fmu_input import find_sens_type
from webviz_subsurface._providers import EnsembleTableProviderFactory

from ._error import error
from ._plugin_ids import PlugInIDs
from .shared_settings import Filters, PlotPicker, Selectors, ViewSettings
from .views import TornadoView


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

        # Defining members
        self._single_filters = single_value_selectors if single_value_selectors else []
        self._multi_filters = multi_value_selectors if multi_value_selectors else []

        provider_factory = EnsembleTableProviderFactory.instance()
        self.error_message = ""

        # Reading from the csv file
        if ensemble is not None and csvfile is not None:
            ens_path = webviz_settings.shared_settings["scratch_ensembles"][ensemble]
            self._parameter_provider = (
                provider_factory.create_from_per_realization_parameter_file(ens_path)
            )
            self._table_provider = (
                provider_factory.create_from_per_realization_csv_file(ens_path, csvfile)
            )
            self._ensemble_name = ensemble

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
                self.error_message = f"'ENSEMBLE' is missing from {aggregated_csvfile}"

        else:
            self.error_message = (
                "Specify either ensembles and csvfile or aggregated_csvfile "
                "and aggregated_parameterfile"
            )

        try:
            design_matrix_df = self._parameter_provider.get_column_data(
                column_names=["SENSNAME", "SENSCASE"]
            )
        except KeyError:
            self.error_message = (
                "Required columns 'SENSNAME' and 'SENSCASE' is missing "
                f"from {self._ensemble_name}. Cannot calculate tornado plots"
            )

        # Defining the datafame
        design_matrix_df["ENSEMBLE"] = self._ensemble_name
        design_matrix_df["SENSTYPE"] = design_matrix_df.apply(
            lambda row: find_sens_type(row.SENSCASE), axis=1
        )

        self._responses: List[str] = self._table_provider.column_names()
        if self._single_filters:
            self._responses = [
                response
                for response in self._responses
                if response not in self._single_filters
            ]
        if self._multi_filters:
            self._responses = [
                response
                for response in self._responses
                if response not in self._multi_filters
            ]
        self._initial_response: str = (
            initial_response if initial_response else self._responses[0]
        )

        # Settingsgroup for switching between table and bars
        self.add_shared_settings_group(
            PlotPicker(), PlugInIDs.SharedSettings.PLOTPICKER
        )

        # Settingsgroup for Selector
        self.add_shared_settings_group(
            Selectors(self._responses, self._initial_response),
            PlugInIDs.SharedSettings.SELECTORS,
        )

        # Settingsgroup for filters
        self.add_shared_settings_group(
            Filters(
                self._table_provider,
                self._single_filters,
                self._multi_filters,
                self._ensemble_name,
            ),
            PlugInIDs.SharedSettings.FILTERS,
        )

        # Settingsgroup for the view options
        self.add_shared_settings_group(
            ViewSettings(design_matrix_df), PlugInIDs.SharedSettings.VIEW_SETTINGS
        )

        # Stores for data
        self.add_store(
            PlugInIDs.Stores.DataStores.TORNADO_DATA,
            WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            PlugInIDs.Stores.DataStores.CLICK_DATA, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.DataStores.HIGH_LOW, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.DataStores.CLIENT_HIGH_PIXELS,
            WebvizPluginABC.StorageType.SESSION,
        )

        self.add_view(
            TornadoView(webviz_settings=webviz_settings, realizations=design_matrix_df),
            PlugInIDs.TornardoPlotGroup.TORNADO_PLOT,
            PlugInIDs.TornardoPlotGroup.GROUPNAME,
        )

    @property
    def tour_steps(self) -> List[dict]:
        """Tour of the plugin"""
        return [
            {
                "id": self.view(PlugInIDs.TornardoPlotGroup.TORNADO_PLOT)
                .layout_element(TornadoView.IDs.MAIN_COLUMN)
                .get_unique_id(),
                "content": ("Shows tornado plot."),
            },
            {
                "id": self.shared_settings_group(
                    PlugInIDs.SharedSettings.PLOTPICKER
                ).component_unique_id(PlotPicker.IDs.BARS_OR_TABLE),
                "content": "Choose between showing the data with bars og in a table",
            },
            {
                "id": self.shared_settings_group(
                    PlugInIDs.SharedSettings.SELECTORS
                ).component_unique_id(Selectors.IDs.RESPONSE),
                "content": "Choose the response for the data",
            },
            {
                "id": self.shared_settings_group(
                    PlugInIDs.SharedSettings.FILTERS
                ).component_unique_id(Filters.IDs.SINGLE_FILTER),
                "content": "Choose the response for the data",
            },
            {
                "id": self.shared_settings_group(
                    PlugInIDs.SharedSettings.FILTERS
                ).component_unique_id(Filters.IDs.MULTI_FILTER),
                "content": "Choose the response for the data",
            },
            {
                "id": self.shared_settings_group(
                    PlugInIDs.SharedSettings.VIEW_SETTINGS
                ).component_unique_id(ViewSettings.IDs.REFERENCE),
                "content": (
                    "Set reference sensitivity for which to calculate tornado plot"
                ),
            },
            {
                "id": self.shared_settings_group(
                    PlugInIDs.SharedSettings.VIEW_SETTINGS
                ).component_unique_id(ViewSettings.IDs.SCALE),
                "content": (
                    "Set tornadoplot scale to either percentage or absolute values"
                ),
            },
            {
                "id": self.shared_settings_group(
                    PlugInIDs.SharedSettings.VIEW_SETTINGS
                ).component_unique_id(ViewSettings.IDs.SENSITIVITEIS),
                "content": ("Pick sensitivities to be displayed"),
            },
            {
                "id": self.shared_settings_group(
                    PlugInIDs.SharedSettings.VIEW_SETTINGS
                ).component_unique_id(ViewSettings.IDs.PLOT_OPTIONS),
                "content": "Options for dispaying the bars",
            },
            {
                "id": self.shared_settings_group(
                    PlugInIDs.SharedSettings.VIEW_SETTINGS
                ).component_unique_id(ViewSettings.IDs.LABEL),
                "content": "Plick settings for the label at the bars",
            },
        ]

    @property
    def layout(self) -> Type[Component]:
        return error(self.error_message)
