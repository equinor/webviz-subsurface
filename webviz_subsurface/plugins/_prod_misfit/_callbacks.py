import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import dash
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from webviz_config import EncodedFile, WebvizPluginABC
from webviz_config._theme_class import WebvizConfigTheme
from webviz_subsurface_components import ExpressionInfo, ExternalParseData

from webviz_subsurface._providers import Frequency
from webviz_subsurface._providers.ensemble_summary_provider.ensemble_summary_provider import (
    EnsembleSummaryProvider,
)
from webviz_subsurface._utils.unique_theming import unique_colors

from ._layout import LayoutElements
from .types.provider_set import ProviderSet
from .utils import make_dataframes as makedf
from .utils import make_figures as makefigs

# from ._property_serialization import GraphFigureBuilder


# pylint: disable = too-many-arguments, too-many-branches, too-many-locals, too-many-statements
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
        prevent_initial_call=True,
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
    ) -> List[wcc.Graph]:

        start_time = time.time()

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
        print(dframe)

        figures = makefigs.prod_misfit_plot(
            dframe,
            selector_phases,
            colorby,
            sorting,
            figheight,
            misfit_exponent,
            # misfit_normalization,
        )
        logging.debug(
            f"\n--- Prod misfit callback --- Total time: {time.time() - start_time} seconds.\n"
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
        prevent_initial_call=True,
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
    ) -> List[wcc.Graph]:

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
            print(boxmode, dframe)
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

    # # --------------------------------------------
    # # --- group coverage ---
    # # --------------------------------------------
    # @app.callback(
    #     Output(get_uuid("group_coverage-graph"), "children"),
    #     Input(get_uuid("group_coverage-ensemble_names"), "value"),
    #     Input(get_uuid("group_coverage-dates"), "value"),
    #     Input(get_uuid("group_coverage-phases"), "value"),
    #     Input(get_uuid("group_coverage-group_names"), "value"),
    #     Input(get_uuid("group_coverage-colorby"), "value"),
    #     Input(get_uuid("group_coverage-plot_type"), "value"),
    #     # prevent_initial_call=True,
    # )
    # def _update_group_coverage_graph(
    #     ensemble_names: List[str],
    #     dates: list,
    #     phases: list,
    #     group_names: list,
    #     colorby: str,
    #     plot_type: str,
    # ) -> List[wcc.Graph]:

    #     if plot_type == "crossplot":
    #         dframe = self.df_stat.copy()
    #     else:
    #         dframe = self.df_diff_stat.copy()

    #     # --- apply date filter
    #     dframe = dframe.loc[dframe["DATE"].isin(dates)]

    #     # --- apply ensemble filter
    #     dframe = dframe.loc[dframe["ENSEMBLE"].isin(ensemble_names)]

    #     # --- apply group filter
    #     dframe = dframe.loc[dframe["WELL"].isin(group_names)]

    #     if plot_type == "crossplot":
    #         figures = update_coverage_crossplot(
    #             dframe,
    #             phases,
    #             colorby,
    #             vector_type="group",
    #         )
    #     else:
    #         figures = update_coverage_diff_plot(
    #             dframe,
    #             phases,
    #             colorby,
    #             vector_type="group",
    #         )
    #     return figures

    # --------------------------------------------
    # --- heatmap ---
    # --------------------------------------------
    @app.callback(
        Output(get_uuid(LayoutElements.HEATMAP_GRAPH), "children"),
        Input(get_uuid(LayoutElements.HEATMAP_ENSEMBLE_NAMES), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_DATES), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_PHASES), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_WELL_NAMES), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_REALIZATIONS), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_FILTER_LARGEST), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_FIGHEIGHT), "value"),
        Input(get_uuid(LayoutElements.HEATMAP_SCALE_COL_RANGE), "value"),
        # prevent_initial_call=True,
    )
    def _update_heatmap_graph(
        ensemble_names: List[str],
        selector_dates: list,
        selector_phases: list,
        selector_well_names: list,
        selector_realizations: list,
        selector_filter_largest: int,
        selector_figheight: int,
        selector_scale_col_range: float,
    ) -> List[wcc.Graph]:

        # if plot_type in ["diffplot", "rel_diffplot"]:
        plot_type = "diffplot"
        relative_diff = plot_type == "rel_diffplot"
        dframe = makedf.get_df_diff(
            makedf.get_df_smry(
                input_provider_set,
                ensemble_names,
                ens_vectors,
                ens_realizations,
                selector_realizations,
                selector_well_names,
                selector_phases,
                selector_dates,
            ),
            relative_diff=relative_diff,
        )

        # dframe = self.df_diff_stat.copy()

        # # --- apply date filter
        # dframe = dframe.loc[dframe["DATE"].isin(dates)]

        # # --- apply ensemble filter
        # dframe = dframe.loc[dframe["ENSEMBLE"].isin(ensemble_names)]

        # # --- apply well filter
        # dframe = dframe.loc[dframe["WELL"].isin(well_names)]

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
    selected_collection_wells = set(selected_collection_wells)

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
