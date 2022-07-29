import json
from typing import List, Optional

import webviz_core_components as wcc
from dash import ALL, Input, Output, callback, callback_context
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import LayoutUniqueId, SettingsGroupABC

from webviz_subsurface._providers import EnsembleTableProvider

from .._plugin_ids import PlugInIDs


class Filters(SettingsGroupABC):
    """Settingsgroup for filters"""

    class IDs:
        # pylint: disable=too-few-public-methods
        SINGLE_FILTER = "single-filter"
        MULTI_FILTER = "multi-filter"

    def __init__(
        self,
        table_provider: EnsembleTableProvider,
        single_filters: List[str],
        multi_filters: List[str],
        ensemble_name: str,
    ) -> None:
        super().__init__("Filters")
        self._table_provider = table_provider
        self._single_filters = single_filters
        self._multi_filters = multi_filters
        self._ensemble_name = ensemble_name
        self._plugin_unique_id = LayoutUniqueId(plugin_uuid=PlugInIDs.PlugIn.PLUGIN_ID)

    def layout(self) -> List[Component]:
        elements = []

        # Creates dropdowns for any data columns added as single value filters
        for selector in self._single_filters:
            values = self._table_provider.get_column_data([selector])[selector].unique()

            elements.append(
                wcc.Dropdown(
                    label=selector,
                    id={
                        "id": self.uuid(Filters.IDs.SINGLE_FILTER),
                        "name": selector,
                        "type": "single_filter",
                    },
                    options=[{"label": val, "value": val} for val in values],
                    value=values[0],
                    clearable=False,
                )
            )

        # Creates dropdowns for any data columns added as single value filters
        for selector in self._multi_filters:
            values = self._table_provider.get_column_data([selector])[selector].unique()
            elements.append(
                wcc.Dropdown(
                    label=selector,
                    id={
                        "id": self.uuid(  # kan jeg bruke denne egt?
                            Filters.IDs.MULTI_FILTER
                        ),
                        "name": selector,
                        "type": "multi_filter",
                    },
                    options=[{"label": val, "value": val} for val in values],
                    value=values,
                    multi=True,
                )
            )
        return elements

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.DataStores.TORNADO_DATA),
                "data",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.RESPONSE),
                "data",
            ),
            Input(
                {
                    "id": self.uuid(Filters.IDs.SINGLE_FILTER),
                    "name": ALL,
                    "type": "single_filter",
                },
                "value",
            ),
            Input(
                {
                    "id": self.uuid(Filters.IDs.MULTI_FILTER),
                    "name": ALL,
                    "type": "multi_filter",
                },
                "value",
            ),
        )
        def _update_tornado_with_response_values(
            response: str, single_filters: List, multi_filters: List
        ) -> str:
            """Returns a json dump for the tornado plot with the response values per realization"""

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

    def uuid(self, element: Optional[str] = None) -> str:
        """Typically used to get a unique ID for some given element/component in
        a plugins layout. If the element string is unique within the plugin, this
        function returns a string which is guaranteed to be unique also across the
        application (even when multiple instances of the same plugin is added).

        Within the same plugin instance, the returned uuid is the same for the same
        element string. I.e. storing the returned value in the plugin is not necessary.

        Main benefit of using this function instead of creating a UUID directly,
        is that the abstract base class can in the future provide IDs that
        are consistent across application restarts (i.e. when the webviz configuration
        file changes in a non-portable setting).
        """

        if element is None:
            return f"{self._plugin_unique_id.get_plugin_uuid()}"

        return f"{element}-{self._plugin_unique_id.get_plugin_uuid()}"
