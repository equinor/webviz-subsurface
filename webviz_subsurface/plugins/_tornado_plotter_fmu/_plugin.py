from pathlib import Path
from typing import List, Type

from dash.development.base_component import Component
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE

from webviz_subsurface._datainput.fmu_input import find_sens_type
from webviz_subsurface._providers import EnsembleTableProviderFactory

from ._error import error
from ._plugin_ids import PlugInIDs
from .shared_settings import (
    MultiFilters,
    PlotPicker,
    Selectors,
    SingleFilters,
    ViewSettings,
)

from .views import TornadoWidget


class TornadoPlotterFMU(WebvizPluginABC):
    """Descibtion"""

    class IDs:
        # pylint: disable=too-few-public-methods
        TORNADO_PLUGIN = "tornado-plugin"

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
        super().__init__()

        # Defining members
        self._single_filters = single_value_selectors if single_value_selectors else []
        self._multi_filters = multi_value_selectors if multi_value_selectors else []

        # Undefined number of single and multifilter so IDs have to be arbitrarily defined
        self._single_filter_IDs = {}
        for filter_num, filter_str in enumerate(self._single_filters):
            self._single_filter_IDs.update({filter_num: filter_str})
    
        self._multi_filters_IDs = {}
        for filter_num, filter in enumerate(self._multi_filters):
            self._multi_filters_IDs.update({filter_num: filter})

        print("multi: ", self._multi_filters_IDs)

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

        self._tornado_widget = TornadoWidget(
            webviz_settings=webviz_settings, realizations=design_matrix_df
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
        self.add_store(
            PlugInIDs.Stores.PlotPicker.BARS_OR_TABLE,
            WebvizPluginABC.StorageType.SESSION,
        )
        self.add_shared_settings_group(
            PlotPicker(), PlugInIDs.SharedSettings.PLOTPICKER
        )

        # Settingsgroup for Selector
        self.add_store(
            PlugInIDs.Stores.Selectors.RESPONSE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_shared_settings_group(
            Selectors(self._responses, self._initial_response),
            PlugInIDs.SharedSettings.SELECTORS,
        )

        # Settingsgroup for the single valued filters
        for ID in self._single_filter_IDs.values():
            self.add_store(ID, WebvizPluginABC.StorageType.SESSION)
            print("added store with ID: ", ID)

        self.add_shared_settings_group(
            SingleFilters(
                self._table_provider, self._single_filters, self._single_filter_IDs
            ),
            PlugInIDs.SharedSettings.SINGLE_FILTER,
        )

        # Settingsgroup for the multi valued filters
        for ID in self._multi_filters_IDs:
            self.add_store(ID, WebvizPluginABC.StorageType.SESSION)

        self.add_shared_settings_group(
            MultiFilters(
                self._table_provider, self._multi_filters, self._multi_filters_IDs
            ),
            PlugInIDs.SharedSettings.MULTI_FILTER,
        )

        # Settingsgroup for the plotting options
        self.add_store(
            PlugInIDs.Stores.ViewSetttings.REFERENCE,
            WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            PlugInIDs.Stores.ViewSetttings.SCALE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.ViewSetttings.SENSITIVITIES,
            WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            PlugInIDs.Stores.ViewSetttings.RESET,
            WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            PlugInIDs.Stores.ViewSetttings.PLOT_OPTIONS,
            WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            PlugInIDs.Stores.ViewSetttings.LABEL, WebvizPluginABC.StorageType.SESSION
        )
        self.add_shared_settings_group(
            ViewSettings(design_matrix_df), PlugInIDs.SharedSettings.PLOTOPTIONS
        )

        # vet enda ikke helt hva disse skal brukes til
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
            self._tornado_widget,
            PlugInIDs.TornardoPlotGroup.TORNPLOT,
            PlugInIDs.TornardoPlotGroup.GROUPNAME,
        )

    @property
    def layout(self) -> Type[Component]:
        return error(self.error_message)
