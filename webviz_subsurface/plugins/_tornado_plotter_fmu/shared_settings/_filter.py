from subprocess import call
from typing import List, Optional

import webviz_core_components as wcc
from dash import Input, Output, callback, html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._providers import EnsembleTableProviderFactory

from .._plugin_ids import PlugInIDs


class PlotPicker(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        BARS_OR_TABLE = "bars-or-table"

    def __init__(self) -> None:
        super().__init__("Vizualisation type")

        self.plicker_options = [
            {"label": "Show bars", "value": "bars"},
            {"label": "Show table", "value": "table"},
        ]

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(PlotPicker.IDs.BARS_OR_TABLE),
                options=self.plicker_options,
                value="bars",
                inline=True,
            )
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.PlotPicker.BARS_OR_TABLE),
                "data",
            ),
            Input(
                self.component_unique_id(PlotPicker.IDs.BARS_OR_TABLE).to_string(),
                "value",
            ),
        )
        def _set_plotpicker(pick: str) -> str:
            return pick


class Selectors(SettingsGroupABC):
    """Settings class for labelled dropdown with all response columns"""

    class IDs:
        # pylint: disable=too-few-public-methods
        RESPONSE = "response"

    def __init__(
        self,
        responses: List[str],
        initial_response: str,
    ) -> None:
        super().__init__("Selectors")
        self._responses = responses
        self._initial_response = initial_response

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(Selectors.IDs.RESPONSE),
                label="Response",
                options=[{"label": i, "value": i} for i in self._responses],
                value=self._initial_response,
                multi=False,
                clearable=False,
            )
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.RESPONSE), "data"
            ),
            Input(
                self.component_unique_id(Selectors.IDs.RESPONSE).to_string(), "value"
            ),
        )
        def _set_selector(response: str) -> str:
            return response


# SingleFilters er alle filterne hvor det bare velges en verdi
class SingleFilters(SettingsGroupABC):
    """Settings class for picking response"""

    def __init__(
        self,
        table_provider: EnsembleTableProviderFactory,
        single_filters: List[str],
        single_filter_IDs: dict,
    ) -> None:
        super().__init__("Single Filters")
        self._table_provider = table_provider
        self._single_filters = single_filters
        self._single_filters_IDs = single_filter_IDs

    def layout(self) -> List[Component]:
        """Creates dropdowns for any data columns added as single value filters"""
        elements = []
        for selector_num, selector in enumerate(self._single_filters):
            values = self._table_provider.get_column_data([selector])[selector].unique()

            elements.append(
                wcc.Dropdown(
                    label=selector,
                    id={
                        "id": self.register_component_unique_id(
                            self._single_filters_IDs[selector_num]
                        ),
                        "name": selector,
                        "type": "single_filter",
                    },
                    options=[{"label": val, "value": val} for val in values],
                    value=values[0],
                    clearable=False,
                )
            )
        return elements


# MultiFIlters er alle filtrene som kan ha flere valg
class MultiFilters(SettingsGroupABC):
    def __init__(
        self,
        table_provider: EnsembleTableProviderFactory,
        multi_filters: List[str],
        multi_filter_IDs: dict,
    ) -> None:
        super().__init__("Multi Filters")
        self._table_provider = table_provider
        self._multi_filters = multi_filters
        self._multi_filters_IDs = multi_filter_IDs

    def layout(self) -> List[Component]:
        """Creates wcc.Selects for any data columns added as multi value filters"""
        elements = []
        for selector_num, selector in enumerate(self._multi_filters):
            values = self._table_provider.get_column_data([selector])[selector].unique()

            elements.append(
                wcc.Dropdown(
                    label=selector,
                    id={
                        "id": self.register_component_unique_id(
                            self._multi_filters_IDs[selector_num]
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
            return f"{self.TornadoPlotterFMU.IDs.TORNARDO_PLUGIN.get_plugin_uuid()}"

        return (
            f"{element}-{self.TornadoPlotterFMU.IDs.TORNARDO_PLUGIN.get_plugin_uuid()}"
        )


class ViewSettings(SettingsGroupABC):
    """Describtion"""

    class IDs:
        # pylint: disable=too-few-public-methods
        REFERENCE = "reference"
        SCALE = "scale"
        SENSITIVITEIS = "sensitivities"
        RESET_BUTTON = "reset-button"
        PLOT_OPTIONS = "plot-options"
        LABEL = "label"

    def __init__(
        self,
        realizations: List[str],  # design_matrix_df
        reference: str = "rms_seed",  # vet ikke helt hva dette er, men den settes ikke i orginalen så hmm
        allow_click: bool = False,
    ) -> None:
        super().__init__("Plottion Options")

        self.sensnames = list(realizations["SENSNAME"].unique())
        self.scales = [
            "Relative value (%)",
            "Relative value",
            "True value",
        ]
        self.plot_options = [
            {
                "label": "Fit all bars in figure",
                "value": "Fit all bars in figure",
            },
            {
                "label": "Remove sensitivites with no impact",
                "value": "Remove sensitivites with no impact",
            },
            {
                "label": "Show realization points",
                "value": "Show realization points",
            },
            {
                "label": "Color bars by sensitivity",
                "value": "Color bars by sensitivity",
            },
        ]
        self.label_options = [
            {"label": "No label", "value": "hide"},
            {
                "label": "Simple label",
                "value": "simple",
            },
            {
                "label": "Detailed label",
                "value": "detailed",
            },
        ]
        self.initial_reference = (
            reference if reference in self.sensnames else self.sensnames[0]
        )
        self.allow_click = allow_click

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(ViewSettings.IDs.REFERENCE),
                label="Reference",
                options=[{"label": r, "value": r} for r in self.sensnames],
                value=self.initial_reference,
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(ViewSettings.IDs.SCALE),
                label="Scale",
                options=[{"label": r, "value": r} for r in self.scales],
                value=self.scales[0],
                multi=False,
                clearable=False,
            ),  # mulig jeg skal endre denne til å være dropdown også, litt penere? og enklere å bruke for å velge flere
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(ViewSettings.IDs.SENSITIVITEIS),
                label="Select sensitivities",
                options=[{"label": r, "value": r} for r in self.sensnames],
                value=self.sensnames[0],
                multi=True,
            ),
            html.Button(
                id=self.register_component_unique_id(ViewSettings.IDs.RESET_BUTTON),
                title="Reset Selected Sesitivities",
                style={
                    "fontSize": "10px",
                    "marginTop": "10px",
                }
                if self.allow_click
                else {"display": "none"},
                children="Clear selected",
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(ViewSettings.IDs.PLOT_OPTIONS),
                label="Plot options",
                options=self.plot_options,
                value=[],
                labelStyle={"display": "block"},
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(ViewSettings.IDs.LABEL),
                label="Label",
                options=self.label_options,
                value="detailed",
                clearable=False,
            ),
        ]
