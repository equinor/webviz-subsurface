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
            {"id": get_uuid("main-inplace-dist"), "element": "graph", "layout": ALL},
            "figure",
        ),
        Output(
            {"id": get_uuid("main-inplace-dist"), "element": "table", "layout": ALL},
            "data",
        ),
        Output(
            {"id": get_uuid("main-inplace-dist"), "element": "table", "layout": ALL},
            "columns",
        ),
        Input(get_uuid("filter-inplace-dist"), "data"),
        Input(get_uuid("selections-inplace-dist"), "data"),
        Input(get_uuid("page-selected-inplace-dist"), "data"),
        State(
            {"id": get_uuid("main-inplace-dist"), "element": "graph", "layout": "1x1"},
            "figure",
        ),
    )
    def _update_plots(filters, selections, page_selected, figure):
        if (
            selections is None
            or filters is None
            or page_selected == "Plots per zone/region"
        ):
            raise PreventUpdate

        ctx = dash.callback_context.triggered[0]

        dframe = volumemodel.dataframe.copy()
        dframe = filter_df(dframe, filters)

        responses = {
            x
            for x in [selections["X Response"], selections["Y Response"]]
            if x is not None
        }
        groups = ["ENSEMBLE", "REAL"]

        for selection in ["Subplots", "Color by"]:
            if (
                selections[selection] is not None
                and selections[selection] not in groups
            ):
                groups.append(selections[selection])
        for response in responses:
            if response not in groups and response in volumemodel.selectors:
                groups.append(response)

        parameters = [x for x in groups if x not in dframe]
        if parameters:
            columns = parameters + ["REAL", "ENSEMBLE"]
            dframe = pd.merge(
                dframe, volumemodel.parameter_df[columns], on=["REAL", "ENSEMBLE"]
            )

        columns = volumemodel.volume_columns + volumemodel.property_columns
        # Need to sum volume columns and take the average of property columns
        aggregations = {x: "sum" for x in volumemodel.volume_columns}
        aggregations.update({x: "mean" for x in volumemodel.property_columns})

        dframe = (
            dframe[columns + groups].groupby(groups).agg(aggregations).reset_index()
        )
        dframe.sort_values(by=["ENSEMBLE", "REAL"])

        columns, table_data = (
            make_stattable(dframe, responses, groups + parameters, volumemodel)
            if selections["Table type"] == "Statistics table"
            else make_table(dframe)
        )

        # pylint: disable=no-member
        figure = create_figure(
            plot_type=selections["Plot type"],
            data_frame=dframe,
            x=selections["X Response"],
            y=selections["Y Response"],
            facet_col=selections["Subplots"],
            color=selections["Color by"],
            color_discrete_sequence=px.colors.qualitative.G10_r,
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

        return ([figure] * 2, [table_data] * 2, [columns] * 2)

    @app.callback(
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "pie_chart",
                "layout": "per_region",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "pie_chart",
                "layout": "per_zone",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "bar_chart",
                "layout": "per_region",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "bar_chart",
                "layout": "per_zone",
            },
            "figure",
        ),
        Input(get_uuid("filter-inplace-dist"), "data"),
        Input(get_uuid("selections-inplace-dist"), "data"),
        Input(get_uuid("page-selected-inplace-dist"), "data"),
    )
    def _update_plots_per_region_zone(filters, selections, page_selected):
        if page_selected != "Plots per zone/region":
            raise PreventUpdate

        dframe = volumemodel.dataframe.copy()
        dframe = filter_df(dframe, filters)
        pie_figs = []
        bar_figs = []
        for selector in ["REGION", "ZONE"]:
            groups = ["ENSEMBLE", "REAL"]
            groups.append(selector)
            # Need to sum volume columns and take the average of property columns

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
                    color_discrete_sequence=px.colors.qualitative.G10_r,
                    color=selector,
                    opacity=0.85,
                )
            )
            bar_figs.append(
                create_figure(
                    plot_type="bar",
                    data_frame=df_merged,
                    x=selector,
                    y=selections["X Response"],
                    color_discrete_sequence=px.colors.qualitative.G10_r,
                    color="ENSEMBLE",
                ).update_xaxes(type="category")
            )

        return pie_figs[0], pie_figs[1], bar_figs[0], bar_figs[1]


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

    if dframe.empty:
        return html.Span(
            "No data left after filtering",
            style={
                "fontSize": "10em",
            },
        )
    return dframe
