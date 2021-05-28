from typing import Callable
import pandas as pd
from pandas.api.types import is_numeric_dtype
import numpy as np
import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from dash_table.Format import Format
import plotly.express as px

from webviz_subsurface._abbreviations.number_formatting import table_statistics_base
from webviz_subsurface._abbreviations.volume_terminology import (
    volume_description,
    volume_unit,
)

from ..figures import create_figure


def distribution_controllers(app: dash.Dash, get_uuid: Callable, volumemodel):
    @app.callback(
        Output(
            {"id": get_uuid("main-inplace-dist"), "element": "graph", "page": ALL},
            "figure",
        ),
        Output(
            {"id": get_uuid("main-inplace-dist"), "element": "table", "page": ALL},
            "data",
        ),
        Output(
            {"id": get_uuid("main-inplace-dist"), "element": "table", "page": ALL},
            "columns",
        ),
        Input(get_uuid("selections-inplace-dist"), "data"),
        State(get_uuid("page-selected-inplace-dist"), "data"),
        State(
            {"id": get_uuid("main-inplace-dist"), "element": "plot-table-select"},
            "value",
        ),
        State(
            {"id": get_uuid("main-inplace-dist"), "element": "graph", "page": "custom"},
            "figure",
        ),
        State(
            {"id": get_uuid("main-inplace-dist"), "element": "table", "page": "custom"},
            "data",
        ),
        State(
            {"id": get_uuid("main-inplace-dist"), "element": "table", "page": "custom"},
            "columns",
        ),
    )
    def _update_plots(
        selections, page_selected, plot_table_select, figure, table_data, table_columns
    ):
        initial_callback = figure is None
        if not initial_callback and page_selected not in ["1p1t", "custom"]:
            raise PreventUpdate

        plot_groups = ["ENSEMBLE", "REAL"]
        parameters = []
        for item in ["Subplots", "Color by", "X Response", "Y Response"]:
            if selections[item] is not None:
                if selections[item] in volumemodel.selectors:
                    plot_groups.append(selections[item])
                if selections[item] in volumemodel.parameters:
                    parameters.append(selections[item])
        plot_groups = list(set(plot_groups))

        dframe = volumemodel.dataframe.copy()

        if parameters:
            columns = parameters + ["REAL", "ENSEMBLE"]
            dframe = pd.merge(
                dframe, volumemodel.parameter_df[columns], on=["REAL", "ENSEMBLE"]
            )
        dframe = filter_df(dframe, selections["filters"])

        # Need to sum volume columns and take the average of property columns
        aggregations = {x: "sum" for x in volumemodel.volume_columns}
        aggregations.update({x: "mean" for x in parameters})

        df_for_figure = dframe.groupby(plot_groups).agg(aggregations).reset_index()
        df_for_figure = volumemodel.compute_property_columns(df_for_figure)

        if not (plot_table_select == "table" and page_selected == "custom"):
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
                        text=(
                            f"{volume_description(selections['X Response'])}"
                            f"[{volume_unit(selections['X Response'])}]"
                        ),
                        x=0.5,
                        font=dict(size=18),
                    ),
                ),
                yaxis=dict(showticklabels=True),
            )
            if selections["Subplots"] is not None:
                if not selections["X axis matches"]:
                    figure.update_xaxes({"matches": None})
                if not selections["Y axis matches"]:
                    figure.update_yaxes({"matches": None})

        # Make tables
        if not (plot_table_select == "graph" and page_selected == "custom"):
            if selections["sync_table"]:
                table_columns, table_data = make_table(
                    dframe=df_for_figure,
                    responses=list(
                        {
                            x
                            for x in [
                                selections["X Response"],
                                selections["Y Response"],
                            ]
                            if x is not None
                        }
                    ),
                    groups=plot_groups,
                    volumemodel=volumemodel,
                    tabletype=selections["Table type"],
                )
            else:
                table_groups = ["ENSEMBLE", "REAL"]
                if selections["Group by"] is not None:
                    table_groups.extend(
                        [x for x in selections["Group by"] if x not in table_groups]
                    )
                df_for_table = (
                    dframe.groupby(table_groups).agg(aggregations).reset_index()
                )
                df_for_table = volumemodel.compute_property_columns(df_for_table)
                table_columns, table_data = make_table(
                    dframe=df_for_table,
                    responses=selections["table_responses"],
                    groups=selections["Group by"],
                    volumemodel=volumemodel,
                    tabletype=selections["Table type"],
                )

        return ([figure] * 2, [table_data] * 2, [table_columns] * 2)

    @app.callback(
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "chart": ALL,
                "selector": ALL,
                "page": "per_zr",
            },
            "figure",
        ),
        Input(get_uuid("selections-inplace-dist"), "data"),
        State(get_uuid("page-selected-inplace-dist"), "data"),
        State(
            {
                "id": get_uuid("main-inplace-dist"),
                "chart": ALL,
                "selector": ALL,
                "page": "per_zr",
            },
            "id",
        ),
    )
    def _update_plots_per_region_zone(selections, page_selected, figure_ids):
        if page_selected != "per_zr":
            raise PreventUpdate

        dframe = volumemodel.dataframe.copy()
        dframe = filter_df(dframe, selections["filters"])

        figs = {}
        for selector in ["REGION", "ZONE"]:
            groups = ["ENSEMBLE", "REAL"]
            groups.append(selector)

            aggregations = {x: "sum" for x in volumemodel.volume_columns}
            df_group = dframe.groupby(groups).agg(aggregations).reset_index()
            df_group = volumemodel.compute_property_columns(df_group)

            # find mean over realizations
            df_merged = (
                df_group.groupby([x for x in groups if x != "REAL"])
                .mean()
                .reset_index()
            )

            # pylint: disable=no-member
            figs[selector] = {
                "pie": create_figure(
                    plot_type="pie",
                    data_frame=df_merged,
                    values=selections["X Response"],
                    names=selector,
                    title=f"{selections['X Response']} per {selector}",
                    color_discrete_sequence=selections["Colorscale"],
                    color=selector,
                ),
                "bar": create_figure(
                    plot_type="bar",
                    data_frame=df_merged,
                    x=selector,
                    y=selections["X Response"],
                    color_discrete_sequence=px.colors.diverging.BrBG_r,
                    color=selections["Color by"],
                    text=selections["X Response"],
                    xaxis=dict(type="category", tickangle=45, tickfont_size=17),
                ).update_traces(texttemplate="%{text:.2s}", textposition="auto"),
            }

        output_figs = []
        for fig_id in figure_ids:
            output_figs.append(figs[fig_id["selector"]][fig_id["chart"]])
        return output_figs

    @app.callback(
        Output(
            {"id": get_uuid("main-inplace-dist"), "element": "plot", "page": "conv"},
            "figure",
        ),
        Input(get_uuid("selections-inplace-dist"), "data"),
        State(get_uuid("page-selected-inplace-dist"), "data"),
    )
    def _update_convergence_plot(selections, page_selected):
        if page_selected != "conv":
            raise PreventUpdate

        dframe = volumemodel.dataframe.copy()
        dframe = filter_df(dframe, selections["filters"])
        if dframe.empty:
            return []

        subplots = selections["Subplots"] if selections["Subplots"] is not None else []
        groups = ["ENSEMBLE", "REAL"]
        if subplots and subplots not in groups:
            groups.append(subplots)

        aggregations = {x: "sum" for x in volumemodel.volume_columns}
        dframe = dframe.groupby(groups).agg(aggregations).reset_index()
        dframe = volumemodel.compute_property_columns(dframe)
        dframe = dframe.sort_values(by=["ENSEMBLE", "REAL"])

        dfs = []
        df_groups = dframe.groupby(subplots) if subplots else [(None, dframe)]
        for _, df in df_groups:
            for calculation in ["mean", "p10", "p90"]:
                df_stat = df.copy()
                df_stat[selections["X Response"]] = (
                    (df_stat[selections["X Response"]].expanding().mean())
                    if calculation == "mean"
                    else df_stat[selections["X Response"]]
                    .expanding()
                    .quantile(0.1 if calculation == "p10" else 0.9)
                )
                df_stat["calculation"] = calculation
                dfs.append(df_stat)
        dframe = pd.concat(dfs)

        figure = (
            create_figure(
                plot_type="line",
                data_frame=dframe,
                x="REAL",
                y=selections["X Response"],
                facet_col=selections["Subplots"],
                color="calculation",
                title=f"Convergence plot of mean/p10/p90 for {selections['X Response']} ",
                yaxis=dict(showticklabels=True),
            )
            .update_traces(line_width=3.5)
            .update_traces(line=dict(color="black"), selector={"name": "mean"})
            .update_traces(
                line=dict(color="firebrick", dash="dash"),
                selector={"name": "p10"},
            )
            .update_traces(
                line=dict(color="royalblue", dash="dash"), selector={"name": "p90"}
            )
        )

        if selections["Subplots"] is not None:
            if not selections["X axis matches"]:
                figure.update_xaxes({"matches": None})
            if not selections["Y axis matches"]:
                figure.update_yaxes(dict(matches=None))
        return figure


def make_table(dframe: pd.DataFrame, responses: list, groups, volumemodel, tabletype):

    groups = [x for x in groups if x != "REAL"] if groups is not None else []
    table_stats = (
        [("Response", {})]
        + [(group, {}) for group in groups]
        + [
            stat
            for x in ["Mean", "Stddev", "P90", "P10", "Minimum", "Maximum"]
            for stat in table_statistics_base()
            if stat[0] == x
        ]
    )

    if tabletype == "Statistics table":
        df_groups = dframe.groupby(groups) if groups else [(None, dframe)]
        tables = []
        for response in responses:
            if not is_numeric_dtype(dframe[response]):
                continue
            for name, df_group in df_groups:
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
                    data[group] = (
                        name if isinstance(name, str) == 1 else list(name)[idx]
                    )
                tables.append(data)

        columns = [{**{"name": i[0], "id": i[0]}, **i[1]} for i in table_stats]

    else:
        dframe = (
            dframe[responses + groups].groupby(groups).mean().reset_index()
            if groups
            else dframe[responses].mean().to_frame().T
        )
        columns = [
            {
                "id": col,
                "name": col,
                "type": "numeric",
                "format": {"locale": {"symbol": ["", ""]}, "specifier": "$.4s"}
                if col in volumemodel.volume_columns
                else Format(precision=3),
            }
            for col in dframe.columns
        ]
        tables = dframe.iloc[::-1].to_dict("records")
    return columns, tables


def filter_df(dframe, filters):
    for filt, values in filters.items():
        dframe = dframe.loc[dframe[filt].isin(values)]
    return dframe
