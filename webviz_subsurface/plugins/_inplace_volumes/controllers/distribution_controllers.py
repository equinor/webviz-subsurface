from typing import Callable
import pandas as pd
from pandas.api.types import is_numeric_dtype
import numpy as np
import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from dash_table.Format import Format
import plotly.express as px

import dash_html_components as html
from webviz_subsurface._abbreviations.number_formatting import table_statistics_base
from webviz_subsurface._abbreviations.volume_terminology import (
    volume_description,
    volume_unit,
)

from ..figures import create_figure


def distribution_controllers(app: dash.Dash, get_uuid: Callable, volumemodel, theme):
    @app.callback(
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "graph",
                "page": "Custom plotting",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "graph",
                "page": "1 plot / 1 table",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "table",
                "page": "Custom plotting",
            },
            "data",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "table",
                "page": "1 plot / 1 table",
            },
            "data",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "table",
                "page": "Custom plotting",
            },
            "columns",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "table",
                "page": "1 plot / 1 table",
            },
            "columns",
        ),
        Input(get_uuid("selections-inplace-dist"), "data"),
        State(get_uuid("page-selected-inplace-dist"), "data"),
        State(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "graph",
                "page": "Custom plotting",
            },
            "figure",
        ),
    )
    def _update_plots(selections, page_selected, figure):
        ctx = dash.callback_context.triggered[0]
        initial_callback = figure is None
        if not initial_callback and (
            page_selected not in ["1 plot / 1 table", "Custom plotting"]
            or "page-selected" in ctx["prop_id"]
        ):
            raise PreventUpdate

        print("updating", ctx["prop_id"])

        plot_groups = ["ENSEMBLE", "REAL"]
        for selection in ["Subplots", "Color by"]:
            if (
                selections[selection] is not None
                and selections[selection] not in plot_groups
            ):
                plot_groups.append(selections[selection])

        responses = {
            x
            for x in [selections["X Response"], selections["Y Response"]]
            if x is not None
        }
        for response in responses:
            if response not in plot_groups and response in volumemodel.selectors:
                plot_groups.append(response)

        dframe = volumemodel.dataframe.copy()
        dframe = filter_df(dframe, selections["filters"])

        parameters = [x for x in plot_groups if x not in dframe]
        if parameters:
            columns = parameters + ["REAL", "ENSEMBLE"]
            dframe = pd.merge(
                dframe, volumemodel.parameter_df[columns], on=["REAL", "ENSEMBLE"]
            )

        # Need to sum volume columns and take the average of property columns
        aggregations = {x: "sum" for x in volumemodel.volume_columns}
        aggregations.update({x: "mean" for x in volumemodel.property_columns})

        df_for_figure = dframe.groupby(plot_groups).agg(aggregations).reset_index()

        # pylint: disable=no-member
        figure = create_figure(
            plot_type=selections["Plot type"],
            data_frame=df_for_figure,
            x=selections["X Response"],
            y=selections["Y Response"],
            facet_col=selections["Subplots"],
            color=selections["Color by"],
            color_discrete_sequence=selections["Colorscale"],
            layout=dict(
                title=dict(
                    text=f"{volume_description(selections['X Response'])} [{volume_unit(selections['X Response'])}]",
                    x=0.5,
                    font=dict(size=18),
                ),
            ),
        )
        if (
            selections["Subplots"] is not None
            and not selections["xrange_subplots_matches"]
        ):
            figure.update_xaxes(matches=None)

        # Make tables
        if selections["sync_table"]:
            table_columns, table_data = (
                make_stattable(
                    df_for_figure, responses, plot_groups + parameters, volumemodel
                )
                if selections["Table type"] == "Statistics table"
                else make_table(df_for_figure[plot_groups + list(responses)])
            )
        else:
            table_groups = ["ENSEMBLE", "REAL"]
            if selections["Group by"] is not None:
                table_groups.extend(selections["Group by"])
            df_for_table = dframe.groupby(table_groups).agg(aggregations).reset_index()
            table_columns, table_data = (
                make_stattable(
                    df_for_table,
                    selections["table_responses"],
                    table_groups,
                    volumemodel,
                )
                if selections["Table type"] == "Statistics table"
                else make_table(dframe[table_groups + selections["table_responses"]])
            )

        return (figure, figure, table_data, table_data, table_columns, table_columns)

    @app.callback(
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "piechart": "per_region",
                "page": "Plots per zone/region",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "piechart": "per_zone",
                "page": "Plots per zone/region",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "barchart": "per_region",
                "page": "Plots per zone/region",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "barchart": "per_zone",
                "page": "Plots per zone/region",
            },
            "figure",
        ),
        Input(get_uuid("selections-inplace-dist"), "data"),
        State(get_uuid("page-selected-inplace-dist"), "data"),
    )
    def _update_plots_per_region_zone(selections, page_selected):
        if page_selected != "Plots per zone/region":
            raise PreventUpdate

        dframe = volumemodel.dataframe.copy()
        dframe = filter_df(dframe, selections["filters"])
        pie_figs = []
        bar_figs = []
        for selector in ["REGION", "ZONE"]:
            groups = ["ENSEMBLE", "REAL"]
            groups.append(selector)

            df_group = (
                dframe[[selections["X Response"]] + groups]
                .groupby(groups)
                .agg(
                    {
                        selections["X Response"]: "sum"
                        if selections["X Response"] in volumemodel.volume_columns
                        else "mean"
                    }
                )
                .reset_index()
            )

            df_merged = (
                df_group[[selections["X Response"], selector, "ENSEMBLE"]]
                .groupby([selector, "ENSEMBLE"])
                .mean()
                .reset_index()
            )

            # pylint: disable=no-member
            pie_figs.append(
                create_figure(
                    plot_type="pie",
                    data_frame=df_merged,
                    values=selections["X Response"],
                    names=selector,
                    title=f"{selections['X Response']} per {selector}",
                    color_discrete_sequence=selections["Colorscale"],
                    color=selector,
                )
            )
            bar_figs.append(
                create_figure(
                    plot_type="bar",
                    data_frame=df_merged,
                    x=selector,
                    y=selections["X Response"],
                    color_discrete_sequence=px.colors.diverging.BrBG_r,
                    color=selections["Color by"],
                ).update_xaxes(type="category", tickangle=45, tickfont_size=17)
            )

        return pie_figs[0], pie_figs[1], bar_figs[0], bar_figs[1]

    @app.callback(
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "plot",
                "page": "Cumulative mean/p10/p90",
            },
            "figure",
        ),
        Input(get_uuid("selections-inplace-dist"), "data"),
        State(get_uuid("page-selected-inplace-dist"), "data"),
    )
    def _update_plots_per_region_zone(selections, page_selected):
        if page_selected != "Cumulative mean/p10/p90":
            raise PreventUpdate

        dframe = volumemodel.dataframe.copy()
        dframe = filter_df(dframe, selections["filters"])

        groups = ["ENSEMBLE", "REAL"]
        dframe = (
            dframe[groups + [selections["X Response"]]]
            .groupby(groups)
            .agg(
                {
                    selections["X Response"]: "sum"
                    if selections["X Response"] in volumemodel.volume_columns
                    else "mean"
                }
            )
            .reset_index()
        )
        dframe.sort_values(by=["ENSEMBLE", "REAL"])
        dfs = []
        for calculation in ["mean", "p10", "p90"]:
            df_stat = dframe.copy()
            if calculation == "mean":
                df_stat[selections["X Response"]] = (
                    dframe[selections["X Response"]].expanding().mean()
                )
            if calculation == "p10":
                df_stat[selections["X Response"]] = (
                    dframe[selections["X Response"]].expanding().quantile(0.1)
                )
            if calculation == "p90":
                df_stat[selections["X Response"]] = (
                    dframe[selections["X Response"]].expanding().quantile(0.9)
                )
            df_stat["calculation"] = calculation
            dfs.append(df_stat)
        dframe = pd.concat(dfs)

        figure = create_figure(
            plot_type="line",
            data_frame=dframe,
            x="REAL",
            y=selections["X Response"],
            facet_col=selections["Subplots"],
            color="calculation",
            title=f"Cumulative mean/p10/p90 for {selections['X Response']} ",
            color_discrete_sequence=selections["Colorscale"],
        )
        if selections["Subplots"] is None:
            figure.update_xaxes(title="Realizations")

        return figure


def make_table(dframe: pd.DataFrame):
    columns = [
        {"id": col, "name": col, "type": "numeric", "format": Format(precision=3)}
        for col in dframe.columns
    ]
    return columns, dframe.iloc[::-1].to_dict("records")


def make_stattable(dframe: pd.DataFrame, responses: list, groups, volumemodel):
    groups = [x for x in groups if x != "REAL"]
    table_stats = (
        [("Response", {})] + [(group, {}) for group in groups] + table_statistics_base()
    )

    tables = []
    for response in responses:
        if not is_numeric_dtype(dframe[response]):
            continue
        for name, df_group in dframe.groupby(groups):

            values = df_group[response]
            data = {
                "Response": response,
                "Mean": values.mean(),
                "Stddev": values.std(),
                "P10": np.percentile(values, 90),
                "P90": np.percentile(values, 10),
                "Minimum": values.min(),
                "Maximum": values.max(),
            }
            for idx, group in enumerate(groups):
                data[group] = name if isinstance(name, str) == 1 else list(name)[idx]

            tables.append(data)

        if response in volumemodel.property_columns:
            for _, values in table_stats:
                if "format" in values:
                    values["format"] = Format(precision=3)

    columns = [{**{"name": i[0], "id": i[0]}, **i[1]} for i in table_stats]
    return columns, tables


def filter_df(dframe, filters):
    for filt, values in filters.items():
        dframe = dframe.loc[dframe[filt].isin(values)]

    return dframe
