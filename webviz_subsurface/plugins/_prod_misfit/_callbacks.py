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

# from ._property_serialization import GraphFigureBuilder


# pylint: disable = too-many-arguments, too-many-branches, too-many-locals, too-many-statements
def plugin_callbacks(
    app: dash.Dash,
    get_uuid: Callable,
    input_provider_set: ProviderSet,
    ens_vectors: Dict[str, List[str]],
    ens_realizations: Dict[str, List[int]],
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
        Input(get_uuid(LayoutElements.PROD_MISFIT_REALIZATIONS), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_COLORBY), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_SORTING), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_FIGHEIGHT), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_OBS_ERROR_WEIGHT), "value"),
        Input(get_uuid(LayoutElements.PROD_MISFIT_EXPONENT), "value"),
        # Input(get_uuid(LayoutElements.PROD_MISFIT_NORMALIZATION), "value"),
    )
    def _update_prod_misfit_graph(
        ensemble_names: List[str],
        selector_dates: list,
        selector_phases: list,
        selector_well_names: list,
        selector_realizations: List[int],
        colorby: str,
        sorting: str,
        figheight: int,
        obs_error_weight: float,
        misfit_exponent: float,
        # misfit_normalization: bool,
    ) -> List[wcc.Graph]:

        start_time = time.time()

        dframe = _get_df_diff(
            _get_df_smry(
                input_provider_set,
                ensemble_names,
                ens_vectors,
                ens_realizations,
                selector_realizations,
                selector_well_names,
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

        figures = update_prod_misfit_plot(
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

    # # --------------------------------------------
    # # --- well coverage ---
    # # --------------------------------------------
    # @app.callback(
    #     Output(get_uuid("well_coverage-graph"), "children"),
    #     Input(get_uuid("well_coverage-ensemble_names"), "value"),
    #     Input(get_uuid("well_coverage-dates"), "value"),
    #     Input(get_uuid("well_coverage-phases"), "value"),
    #     Input(get_uuid("well_coverage-well_names"), "value"),
    #     Input(get_uuid("well_coverage-colorby"), "value"),
    #     Input(get_uuid("well_coverage-plot_type"), "value"),
    # )
    # def _update_well_coverage_graph(
    #     ensemble_names: List[str],
    #     dates: list,
    #     phases: list,
    #     well_names: list,
    #     colorby: str,
    #     plot_type: str,
    # ) -> List[wcc.Graph]:

    #     if plot_type == "boxplot":
    #         dframe = self.df_diff.copy()
    #     elif plot_type == "crossplot":
    #         dframe = self.df_stat.copy()
    #     else:
    #         dframe = self.df_diff_stat.copy()

    #     # --- apply date filter
    #     dframe = dframe.loc[dframe["DATE"].isin(dates)]

    #     # --- apply ensemble filter
    #     dframe = dframe.loc[dframe["ENSEMBLE"].isin(ensemble_names)]

    #     # --- apply well filter
    #     # dframe = dframe.loc[dframe["WELL"].isin(well_names)]

    #     if plot_type == "boxplot":
    #         figures = update_coverage_boxplot(
    #             dframe,
    #             phases,
    #             colorby,
    #             vector_type="well",
    #         )
    #     elif plot_type == "crossplot":
    #         figures = update_coverage_crossplot(
    #             dframe,
    #             phases,
    #             colorby,
    #             vector_type="well",
    #         )
    #     else:
    #         figures = update_coverage_diff_plot(
    #             dframe,
    #             phases,
    #             colorby,
    #             vector_type="well",
    #         )
    #     return figures

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

    # # --------------------------------------------
    # # --- heatmap ---
    # # --------------------------------------------
    # @app.callback(
    #     Output(get_uuid("heatmap-graph"), "children"),
    #     Input(get_uuid("heatmap-ensemble_names"), "value"),
    #     Input(get_uuid("heatmap-dates"), "value"),
    #     Input(get_uuid("heatmap-phases"), "value"),
    #     Input(get_uuid("heatmap-well_names"), "value"),
    #     Input(get_uuid("heatmap-filter_largest"), "value"),
    #     Input(get_uuid("heatmap-figheight"), "value"),
    #     Input(get_uuid("heatmap-scale_col_range"), "value"),
    #     # prevent_initial_call=True,
    # )
    # def _update_heatmap_graph(
    #     ensemble_names: List[str],
    #     dates: list,
    #     phases: list,
    #     well_names: list,
    #     filter_largest: int,
    #     figheight: int,
    #     scale_col_range: float,
    # ) -> List[wcc.Graph]:

    #     dframe = self.df_diff_stat.copy()

    #     # --- apply date filter
    #     dframe = dframe.loc[dframe["DATE"].isin(dates)]

    #     # --- apply ensemble filter
    #     dframe = dframe.loc[dframe["ENSEMBLE"].isin(ensemble_names)]

    #     # --- apply well filter
    #     dframe = dframe.loc[dframe["WELL"].isin(well_names)]

    #     figures = update_heatmap_plot(
    #         dframe,
    #         phases,
    #         vector_type="well",
    #         filter_largest=filter_largest,
    #         figheight=figheight,
    #         scale_col_range=scale_col_range,
    #     )
    #     return figures


# -------------------
def _get_df_smry(
    input_provider_set: ProviderSet,
    ensemble_names: List[str],
    ens_vectors: Dict[str, List[str]],
    ens_realizations: Dict[str, List[int]],
    selector_realizations: List[int],
    selector_well_names: List[str],
    selector_phases: List[str],
    selector_dates: str,
) -> pd.DataFrame:
    """Return dataframe filtered on ensemble names, realizations, well names,
    phases and dates selectors."""

    start_time = time.time()

    filtered_vector_types = []
    if "Oil" in selector_phases:
        filtered_vector_types.append("WOPT")
    if "Water" in selector_phases:
        filtered_vector_types.append("WWPT")
    if "Gas" in selector_phases:
        filtered_vector_types.append("WGPT")

    dfs = []
    for ens_name in ensemble_names:

        filtered_vectors = []
        filtered_realizations = []

        for vector in ens_vectors[ens_name]:
            if (
                vector.split(":")[0] in filtered_vector_types
                and vector.split(":")[1] in selector_well_names
            ):
                hvector = vector.split(":")[0] + "H:" + vector.split(":")[1]
                filtered_vectors.append(vector)
                filtered_vectors.append(hvector)
        # logging.debug(f"Filtered vectors:\n{filtered_vectors}")

        filtered_realizations = [
            real
            for real in ens_realizations[ens_name]
            if real in set(selector_realizations)
        ]
        logging.debug(f"Filtered realizations:\n{filtered_realizations}")

        df = pd.DataFrame()
        if filtered_vectors and filtered_realizations:
            df = input_provider_set.provider(ens_name).get_vectors_df(
                filtered_vectors, None, filtered_realizations
            )

            # df["DATE"] = df["DATE"].dt.strftime("%Y-%m-%d")
            df = df.astype({"DATE": "string"})
            df.DATE = df.DATE.str[:10]
            df = df.loc[df["DATE"].isin(selector_dates)]  # --- apply date filter

            df["ENSEMBLE"] = ens_name

        dfs.append(df)

    logging.debug(
        f"\n--- get_df_smry --- Total time: {time.time() - start_time} seconds.\n"
    )

    return pd.concat(dfs)


# --------------------------------
def _get_df_diff(
    df_smry: pd.DataFrame,
    obs_error_weight: float,
    weight_reduction_factor_oil: float,
    weight_reduction_factor_wat: float,
    weight_reduction_factor_gas: float,
    misfit_exponent: float = 1.0,
) -> pd.DataFrame:
    """Return dataframe with diff (sim-obs) for all data.
    Return empty dataframe if no realizations included."""

    start_time = time.time()

    df_diff = df_smry[["ENSEMBLE", "DATE", "REAL"]].copy()

    for col in df_smry.columns:
        if "PT:" in col:
            simvector = col
            vectortype, wellname = simvector.split(":")[0], simvector.split(":")[1]
            obsvector = vectortype + "H:" + wellname
            diff_col_name = "DIFF_" + vectortype + ":" + wellname
            if obs_error_weight > 0:
                # obs error, including a lower bound (diminish very low values)
                obs_error = (obs_error_weight * df_smry[obsvector]).clip(1000)
                df_diff[diff_col_name] = (
                    (df_smry[simvector] - df_smry[obsvector]) / obs_error
                ) ** misfit_exponent
            elif obs_error_weight < 0:
                if vectortype == "WOPT":
                    weight_reduction = weight_reduction_factor_oil
                if vectortype == "WWPT":
                    weight_reduction = weight_reduction_factor_wat
                if vectortype == "WGPT":
                    weight_reduction = weight_reduction_factor_gas
                df_diff[diff_col_name] = (
                    (df_smry[simvector] - df_smry[obsvector]) / (weight_reduction)
                ) ** misfit_exponent
            else:
                df_diff[diff_col_name] = (
                    (df_smry[simvector] - df_smry[obsvector])
                ) ** misfit_exponent

    # df_diff = df_diff.astype({"DATE": "string"})

    logging.debug(
        f"\n--- _get_df__diff --- Total time: {time.time() - start_time} seconds.\n"
    )
    return df_diff


# -------------------------------
def update_prod_misfit_plot(
    df_diff: pd.DataFrame,
    phases: list,
    colorby: str,
    sorting: str = None,
    figheight: int = 450,
    misfit_exponent: float = 1.0,
    normalize: bool = False,
) -> List[wcc.Graph]:
    """Create plot of misfit per realization. One plot per ensemble.
    Misfit is absolute value of |sim - obs|, weighted by obs_error"""

    misfit_plot_start_time = time.time()
    int_n = 0

    logging.debug("--- Updating production misfit plot ---")
    max_misfit, min_misfit = 0, 0
    figures = []

    for ens_name, ensdf in df_diff.groupby("ENSEMBLE"):

        # --- drop columns (realizations) with no data
        ensdf = ensdf.dropna(axis="columns")

        all_columns = list(ensdf)  # column names

        df_misfit = ensdf[["ENSEMBLE", "DATE", "REAL"]].copy()
        df_misfit = df_misfit.astype({"REAL": "string"})
        df_misfit["TOTAL_MISFIT"] = 0

        plot_phases = []
        color_phases = {}

        # -------------------------
        if "Oil" in phases:
            oil_columns = [x for x in all_columns if x.startswith("DIFF_WOPT")]
            df_misfit["OIL_MISFIT"] = ensdf[oil_columns].abs().sum(axis=1)
            if normalize:
                df_misfit["OIL_MISFIT"] = df_misfit["OIL_MISFIT"] / len(oil_columns)
            df_misfit["OIL_MISFIT"] = df_misfit["OIL_MISFIT"] ** (1 / misfit_exponent)
            df_misfit["TOTAL_MISFIT"] = (
                df_misfit["TOTAL_MISFIT"] + df_misfit["OIL_MISFIT"]
            )
            plot_phases.append("OIL_MISFIT")
            color_phases["OIL_MISFIT"] = "#2ca02c"
        # -------------------------
        if "Water" in phases:
            wat_columns = [x for x in all_columns if x.startswith("DIFF_WWPT")]
            df_misfit["WAT_MISFIT"] = ensdf[wat_columns].abs().sum(axis=1)
            if normalize:
                df_misfit["WAT_MISFIT"] = df_misfit["WAT_MISFIT"] / len(wat_columns)
            df_misfit["WAT_MISFIT"] = df_misfit["WAT_MISFIT"] ** (1 / misfit_exponent)
            df_misfit["TOTAL_MISFIT"] = (
                df_misfit["TOTAL_MISFIT"] + df_misfit["WAT_MISFIT"]
            )
            plot_phases.append("WAT_MISFIT")
            color_phases["WAT_MISFIT"] = "#1f77b4"
        # -------------------------
        if "Gas" in phases:
            gas_columns = [x for x in all_columns if x.startswith("DIFF_WGPT")]
            df_misfit["GAS_MISFIT"] = ensdf[gas_columns].abs().sum(axis=1)
            if normalize:
                df_misfit["GAS_MISFIT"] = df_misfit["GAS_MISFIT"] / len(gas_columns)
            df_misfit["GAS_MISFIT"] = df_misfit["GAS_MISFIT"] ** (1 / misfit_exponent)
            df_misfit["TOTAL_MISFIT"] = (
                df_misfit["TOTAL_MISFIT"] + df_misfit["GAS_MISFIT"]
            )
            plot_phases.append("GAS_MISFIT")
            color_phases["GAS_MISFIT"] = "#d62728"
        # -------------------------

        int_n += 1
        logging.debug(
            f"\n--- update_prod_misfit_plot --- {ens_name} "
            f"Intermediate time {int_n}: {time.time() - misfit_plot_start_time} seconds."
        )

        if (
            max_misfit == min_misfit == 0
        ):  # caclulate min-max ranges from first ensemble
            for _, df_date in df_misfit.groupby("DATE"):
                max_misfit = max_misfit + df_date["TOTAL_MISFIT"].max()
                min_misfit = min_misfit + df_date["TOTAL_MISFIT"].min()
        mean_misfit = df_misfit["TOTAL_MISFIT"].mean()

        color: Any = px.NO_COLOR
        color_discrete_map: Optional[dict] = None
        if colorby == "misfit":
            color = "TOTAL_MISFIT"
        elif colorby == "Date":
            color = "DATE"
        elif colorby == "Phases":
            color = None
            color_discrete_map = color_phases

        fig = px.bar(
            df_misfit,
            x="REAL",
            y=plot_phases,
            title=ens_name,
            # range_y=[min_misfit * 0.25, max_misfit * 1.05],
            range_y=[0, max_misfit * 1.05],
            color=color,
            color_discrete_map=color_discrete_map,
            range_color=[min_misfit * 0.20, max_misfit * 1.00],
            color_continuous_scale=px.colors.sequential.amp,
        )
        if sorting:
            fig.update_layout(xaxis={"categoryorder": sorting})
        fig.update_xaxes(showticklabels=False)
        fig.update_xaxes(title_text="Realization (hover to see values)")
        fig.update_yaxes(title_text="Cumulative misfit")
        fig.add_hline(mean_misfit)
        fig.add_annotation(average_arrow_annotation(mean_misfit))
        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        # fig.update_layout(coloraxis_colorbar_thickness=20)
        # fig.update(layout_coloraxis_showscale=False)

        figures.append(wcc.Graph(figure=fig, style={"height": figheight}))

        int_n += 1
        logging.debug(
            f"\n--- update_prod_misfit_plot --- {ens_name} "
            f"Intermediate time {int_n}: {time.time() - misfit_plot_start_time} seconds."
        )

    logging.debug(
        "\n--- update_prod_misfit_plot ---"
        f"Total time: {time.time() - misfit_plot_start_time} seconds.\n"
    )
    return figures


# --------------------------------
def average_arrow_annotation(mean_value: np.float64, yref: str = "y") -> Dict[str, Any]:
    decimals = 0
    if mean_value < 0.001:
        decimals = 5
    elif mean_value < 0.01:
        decimals = 4
    elif mean_value < 0.1:
        decimals = 3
    elif mean_value < 10:
        decimals = 2
    elif mean_value < 100:
        decimals = 1

    text = f"Total average: {mean_value:,.{decimals}f}"

    return {
        "x": 0.5,
        "y": mean_value,
        "xref": "paper",
        "yref": yref,
        "text": text,
        "showarrow": True,
        "align": "center",
        "arrowhead": 2,
        "arrowsize": 1,
        "arrowwidth": 1,
        "arrowcolor": "#636363",
        "ax": 20,
        "ay": -25,
    }
