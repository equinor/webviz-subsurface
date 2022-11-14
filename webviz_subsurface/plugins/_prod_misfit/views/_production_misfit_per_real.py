from typing import Dict, List, Union

import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)

from .._plugin_ids import PluginIds
from ..utils import make_dataframes as makedf
from ..utils import make_figures as makefigs
from ._view_functions import _get_well_names_combined


class PlotSettingsMisfit(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        COLORBY = "colorby"
        SORTING_RANKING = "sorting-ranking"
        FIG_LAYOUT_HEIGHT = "fig-layout-height"

    def __init__(self) -> None:
        super().__init__("Plot Settings")

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Color by",
                id=self.register_component_unique_id(PlotSettingsMisfit.Ids.COLORBY),
                options=[
                    {
                        "label": "Total misfit",
                        "value": "misfit",
                    },
                    {"label": "Phases", "value": "phases"},
                    {"label": "Date", "value": "date"},
                    {"label": "None", "value": None},
                ],
                value="phases",
                multi=False,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Sorting/ranking",
                id=self.register_component_unique_id(
                    PlotSettingsMisfit.Ids.SORTING_RANKING
                ),
                options=[
                    {
                        "label": "None",
                        "value": None,
                    },
                    {
                        "label": "Ascending",
                        "value": "total ascending",
                    },
                    {
                        "label": "Descending",
                        "value": "total descending",
                    },
                ],
                value="total ascending",
                multi=False,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Fig layout - height",
                id=self.register_component_unique_id(
                    PlotSettingsMisfit.Ids.FIG_LAYOUT_HEIGHT
                ),
                options=[
                    {
                        "label": "Very small",
                        "value": 250,
                    },
                    {
                        "label": "Small",
                        "value": 350,
                    },
                    {
                        "label": "Medium",
                        "value": 450,
                    },
                    {
                        "label": "Large",
                        "value": 700,
                    },
                    {
                        "label": "Very large",
                        "value": 1000,
                    },
                ],
                value=450,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
        ]


class MisfitOptions(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        MISFIT_WEIGHT = "misfit-weight"
        MISFIT_EXPONENT = "misfit-exponent"

    def __init__(self) -> None:
        super().__init__("Misfit options")

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Misfit weight",
                id=self.register_component_unique_id(MisfitOptions.Ids.MISFIT_WEIGHT),
                options=[
                    {
                        "label": "Phase weights",
                        "value": -1.0,
                    },
                    {"label": "None", "value": 0.0},
                    {
                        "label": "10% obs error (min=1000)",
                        "value": 0.10,
                    },
                    {
                        "label": "20% obs error (min=1000)",
                        "value": 0.20,
                    },
                ],
                value=-1.0,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Misfit exponent",
                id=self.register_component_unique_id(MisfitOptions.Ids.MISFIT_EXPONENT),
                options=[
                    {
                        "label": "Linear sum",
                        "value": 1.0,
                    },
                    {
                        "label": "Squared sum",
                        "value": 2.0,
                    },
                ],
                value=1.0,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
        ]


class MisfitPerRealView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        PLOT_SETTINGS = "plot-settings"
        MISFIT_OPTIONS = "misfit-options"
        MAIN_COLUMN = "main-column"

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        input_provider_set: EnsembleSummaryProviderSet,
        ens_vectors: Dict[str, List[str]],
        ens_realizations: Dict[str, List[int]],
        well_collections: Dict[str, List[str]],
        weight_reduction_factor_oil: float,
        weight_reduction_factor_wat: float,
        weight_reduction_factor_gas: float,
    ) -> None:
        super().__init__("Production misfit per real")

        self.input_provider_set = input_provider_set
        self.ens_vectors = ens_vectors
        self.ens_realizations = ens_realizations
        self.well_collections = well_collections
        self.weight_reduction_factor_oil = weight_reduction_factor_oil
        self.weight_reduction_factor_wat = weight_reduction_factor_wat
        self.weight_reduction_factor_gas = weight_reduction_factor_gas

        self.add_settings_group(
            PlotSettingsMisfit(), MisfitPerRealView.Ids.PLOT_SETTINGS
        )
        self.add_settings_group(MisfitOptions(), MisfitPerRealView.Ids.MISFIT_OPTIONS)
        self.main_column = self.add_column(MisfitPerRealView.Ids.MAIN_COLUMN)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(MisfitPerRealView.Ids.MAIN_COLUMN)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLES), "data"
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_DATES), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_PHASE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_WELLS), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_WELL_COLLECTIONS),
                "data",
            ),
            Input(
                self.get_store_unique_id(
                    PluginIds.Stores.SELECTED_COMBINE_WELLS_COLLECTION
                ),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_REALIZATIONS), "data"
            ),
            Input(
                self.settings_group(MisfitPerRealView.Ids.PLOT_SETTINGS)
                .component_unique_id(PlotSettingsMisfit.Ids.COLORBY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(MisfitPerRealView.Ids.PLOT_SETTINGS)
                .component_unique_id(PlotSettingsMisfit.Ids.SORTING_RANKING)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(MisfitPerRealView.Ids.PLOT_SETTINGS)
                .component_unique_id(PlotSettingsMisfit.Ids.FIG_LAYOUT_HEIGHT)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(MisfitPerRealView.Ids.MISFIT_OPTIONS)
                .component_unique_id(MisfitOptions.Ids.MISFIT_WEIGHT)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(MisfitPerRealView.Ids.MISFIT_OPTIONS)
                .component_unique_id(MisfitOptions.Ids.MISFIT_EXPONENT)
                .to_string(),
                "value",
            ),
        )
        def _update_plots(
            ensemble_names: List[str],
            selector_dates: list,
            selector_phases: list,
            selector_well_names: list,
            selector_well_collection_names: list,
            selector_well_combine_type: str,
            selector_realizations: List[int],
            colorby: str,
            sorting: str,
            figheight: int,
            obs_error_weight: float,
            misfit_exponent: float,
        ) -> Union[str, List[Component]]:

            if not ensemble_names:
                return "No ensembles selected"

            well_names = _get_well_names_combined(
                self.well_collections,
                selector_well_collection_names,
                selector_well_names,
                selector_well_combine_type,
            )

            dframe = makedf.get_df_diff(
                makedf.get_df_smry(
                    self.input_provider_set,
                    ensemble_names,
                    self.ens_vectors,
                    self.ens_realizations,
                    selector_realizations,
                    well_names,
                    selector_phases,
                    selector_dates,
                ),
                obs_error_weight,
                self.weight_reduction_factor_oil,
                self.weight_reduction_factor_wat,
                self.weight_reduction_factor_gas,
                misfit_exponent,
            )

            figures = makefigs.prod_misfit_plot(
                dframe,
                selector_phases,
                colorby,
                sorting,
                figheight,
                misfit_exponent,
                # misfit_normalization,
            )

            return figures
