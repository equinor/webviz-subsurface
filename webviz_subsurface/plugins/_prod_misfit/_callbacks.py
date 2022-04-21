from typing import Callable, Dict, List, Union

import dash
import webviz_core_components as wcc
from dash.dependencies import Input, Output

from .._simulation_time_series.types.provider_set import ProviderSet
from ._layout import LayoutElements
from .utils import make_dataframes as makedf
from .utils import make_figures as makefigs


# pylint: disable = too-many-arguments, too-many-locals
def plugin_callbacks(
    app: dash.Dash,
    get_uuid: Callable,
    input_provider_set: ProviderSet,
    ens_vectors: Dict[str, List[str]],
    ens_realizations: Dict[str, List[int]],
    well_collections: Dict[str, List[str]],
    weight_reduction_factor_oil: float,
    weight_reduction_factor_wat: float,
    weight_reduction_factor_gas: float,
) -> None:

    # --------------------------------------------
    # --- prod misfit ---
    # --------------------------------------------
    @app.callback(
        Output(get_uuid(LayoutElements.PROD_MISFIT_GRAPH), "children"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_ENSEMBLE_NAMES), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_DATES), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_PHASES), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_WELL_NAMES), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_WELL_COLLECTIONS), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_WELL_COMBINE_TYPE), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_REALIZATIONS), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_COLORBY), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_SORTING), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_FIGHEIGHT), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_OBS_ERROR_WEIGHT), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_EXPONENT), "value"),
        # Input(get_uuid(LayoutElements.PROD_MISFIT_NORMALIZATION), "value"),
        # prevent_initial_call=True,
    )
    def _update_prod_misfit_graph(
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
        # misfit_normalization: bool,
    ) -> Union[str, List[wcc.Graph]]:

        if not ensemble_names:
            return "No ensembles selected"

        well_names = _get_well_names_combined(
            well_collections,
            selector_well_collection_names,
            selector_well_names,
            selector_well_combine_type,
        )

        dframe = makedf.get_df_diff(
            makedf.get_df_smry(
                input_provider_set,
                ensemble_names,
                ens_vectors,
                ens_realizations,
                selector_realizations,
                well_names,
                selector_phases,
                selector_dates,
            ),
            obs_error_weight,
            weight_reduction_factor_oil,
            weight_reduction_factor_wat,
            weight_reduction_factor_gas,
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

    # --------------------------------------------
    # --- well coverage ---
    # --------------------------------------------
    @app.callback(
        Output(get_uuid(LayoutElements.WELL_COVERAGE_GRAPH), "children"),
        Input(get_uuid(LayoutElements.WELL_COVERAGE_ENSEMBLE_NAMES), "value"),
        Input(get_uuid(LayoutElements.WELL_COVERAGE_DATES), "value"),
        Input(get_uuid(LayoutElements.WELL_COVERAGE_PHASES), "value"),
        Input(get_uuid(LayoutElements.WELL_COVERAGE_WELL_NAMES), "value"),
        Input(get_uuid(LayoutElements.WELL_COVERAGE_WELL_COLLECTIONS), "value"),
        Input(get_uuid(LayoutElements.WELL_COVERAGE_WELL_COMBINE_TYPE), "value"),
        Input(get_uuid(LayoutElements.WELL_COVERAGE_REALIZATIONS), "value"),
        Input(get_uuid(LayoutElements.WELL_COVERAGE_COLORBY), "value"),
        Input(get_uuid(LayoutElements.WELL_COVERAGE_PLOT_TYPE), "value"),
        Input(get_uuid(LayoutElements.WELL_COVERAGE_FIGHEIGHT), "value"),
        Input(get_uuid(LayoutElements.WELL_COVERAGE_BOXMODE), "value"),
        Input(get_uuid(LayoutElements.WELL_COVERAGE_BOXPLOT_POINTS), "value"),
        # prevent_initial_call=True,
    )
    def _update_well_coverage_graph(
        ensemble_names: List[str],
        selector_dates: List[str],
        selector_phases: List[str],
        selector_well_names: List[str],
        selector_well_collection_names: List[str],
        selector_well_combine_type: str,
        selector_realizations: List[int],
        colorby: str,
        plot_type: str,
        figheight: int,
        boxmode: str,
        boxplot_points: str,
    ) -> Union[str, List[wcc.Graph]]:

        if not ensemble_names:
            return "No ensembles selected"

        well_names = _get_well_names_combined(
            well_collections,
            selector_well_collection_names,
            selector_well_names,
            selector_well_combine_type,
        )

        if plot_type in ["diffplot", "rel_diffplot"]:
            relative_diff = plot_type == "rel_diffplot"
            dframe = makedf.get_df_diff(
                makedf.get_df_smry(
                    input_provider_set,
                    ensemble_names,
                    ens_vectors,
                    ens_realizations,
                    selector_realizations,
                    well_names,
                    selector_phases,
                    selector_dates,
                ),
                relative_diff=relative_diff,
            )
            figures = makefigs.coverage_diffplot(
                dframe,
                selector_phases,
                colorby,
                vector_type="well",
                figheight=figheight,
                boxmode=boxmode,
                boxplot_points=boxplot_points,
            )
        if plot_type == "crossplot":
            dframe = makedf.get_df_smry(
                input_provider_set,
                ensemble_names,
                ens_vectors,
                ens_realizations,
                selector_realizations,
                well_names,
                selector_phases,
                selector_dates,
            )
            figures = makefigs.coverage_crossplot(
                dframe,
                selector_phases,
                colorby,
                vector_type="well",
                figheight=figheight,
                boxplot_points=boxplot_points,
            )

        return figures

    # --------------------------------------------
    # --- heatmap ---
    # --------------------------------------------
    @app.callback(
        Output(get_uuid(LayoutElements.HEATMAP_GRAPH), "children"),
        Input(get_uuid(LayoutElements.HEATMAP_ENSEMBLE_NAMES), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_DATES), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_PHASES), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_WELL_NAMES), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_WELL_COLLECTIONS), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_WELL_COMBINE_TYPE), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_REALIZATIONS), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_FILTER_LARGEST), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_PLOT_TYPE), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_FIGHEIGHT), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_SCALE_COL_RANGE), "value"),
        # prevent_initial_call=True,
    )
    def _update_heatmap_graph(
        ensemble_names: List[str],
        selector_dates: list,
        selector_phases: list,
        selector_well_names: list,
        selector_well_collection_names: list,
        selector_well_combine_type: str,
        selector_realizations: list,
        selector_filter_largest: int,
        selector_plot_type: str,
        selector_figheight: int,
        selector_scale_col_range: float,
    ) -> Union[str, List[wcc.Graph]]:

        if not ensemble_names:
            return "No ensembles selected"

        well_names = _get_well_names_combined(
            well_collections,
            selector_well_collection_names,
            selector_well_names,
            selector_well_combine_type,
        )

        relative_diff = selector_plot_type == "rel_diffplot"
        dframe = makedf.get_df_diff_stat(
            makedf.get_df_diff(
                makedf.get_df_smry(
                    input_provider_set,
                    ensemble_names,
                    ens_vectors,
                    ens_realizations,
                    selector_realizations,
                    well_names,
                    selector_phases,
                    selector_dates,
                ),
                relative_diff=relative_diff,
            )
        )

        figures = makefigs.heatmap_plot(
            dframe,
            selector_phases,
            vector_type="well",
            filter_largest=selector_filter_largest,
            figheight=selector_figheight,
            scale_col_range=selector_scale_col_range,
        )
        return figures


# ----------------------
# --- help functions ---
# ----------------------


def _get_well_names_combined(
    well_collections: Dict[str, List[str]],
    selected_collection_names: list,
    selected_wells: list,
    combine_type: str = "intersection",
) -> List[str]:
    """Return union or intersection of well list and well collection lists."""

    selected_collection_wells = []
    for collection_name in selected_collection_names:
        selected_collection_wells.extend(well_collections[collection_name])
    selected_collection_wells = list(set(selected_collection_wells))
    if combine_type == "intersection":
        # find intersection of selector wells and selector well collections
        well_names_combined = [
            well for well in selected_wells if well in selected_collection_wells
        ]
    else:
        # find union of selector wells and selector well collections
        well_names_combined = list(selected_collection_wells)
        well_names_combined.extend(selected_wells)
        well_names_combined = list(set(well_names_combined))

    return well_names_combined
