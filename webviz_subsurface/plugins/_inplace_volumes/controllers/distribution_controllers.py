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


def distribution_controllers(app: dash.Dash, get_uuid: Callable, volumemodel, theme):
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
        ctx = dash.callback_context.triggered[0]
        initial_callback = figure is None
        if not initial_callback and (
            page_selected not in ["1p1t", "custom"] or "page-selected" in ctx["prop_id"]
        ):
            raise PreventUpdate

        print("updating", ctx["prop_id"])

        plot_groups = ["ENSEMBLE", "REAL"]
        data_groupers = [selections["Subplots"], selections["Color by"]]
        for selection in data_groupers:
            if selection is not None and selection not in plot_groups:
                plot_groups.append(selection)

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

        parameters = [x for x in set(plot_groups + list(responses)) if x not in dframe]
        if parameters:
            columns = parameters + ["REAL", "ENSEMBLE"]
            dframe = pd.merge(
                dframe, volumemodel.parameter_df[columns], on=["REAL", "ENSEMBLE"]
            )

        # Need to sum volume columns and take the average of property columns
        aggregations = {
            col: agg
            for col, agg in volumemodel.aggregations.items()
            if col in dframe.columns
        }

        print(dframe)
        df_for_figure = dframe.groupby(plot_groups).agg(aggregations).reset_index()

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

        print(plot_groups)
        print(plot_table_select, page_selected)
        # Make tables
        if not (plot_table_select == "plot" and page_selected == "custom"):
            if selections["sync_table"]:
                table_columns, table_data = make_table(
                    dframe=df_for_figure,
                    responses=list(responses),
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
                "piechart": "per_region",
                "page": "per_zr",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "piechart": "per_zone",
                "page": "per_zr",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "barchart": "per_region",
                "page": "per_zr",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "barchart": "per_zone",
                "page": "per_zr",
            },
            "figure",
        ),
        Input(get_uuid("selections-inplace-dist"), "data"),
        State(get_uuid("page-selected-inplace-dist"), "data"),
    )
    def _update_plots_per_region_zone(selections, page_selected):
        if page_selected != "per_zr":
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
                    text=selections["X Response"],
                    xaxis=dict(type="category", tickangle=45, tickfont_size=17),
                ).update_traces(texttemplate="%{text:.2s}", textposition="auto")
            )

        return pie_figs[0], pie_figs[1], bar_figs[0], bar_figs[1]

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

        groups = ["ENSEMBLE", "REAL"]
        if selections["Subplots"] is not None and selections["Subplots"] not in groups:
            groups.append(selections["Subplots"])

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
            .sort_values(by=["ENSEMBLE", "REAL"])
        )

        dfs = []
        for calculation in ["mean", "p10", "p90"]:
            df_stat = dframe.copy()

            if selections["Subplots"] is not None:
                df_group = df_stat.groupby([selections["Subplots"]])
                df_groups = []
                for _, df in df_group:
                    df[selections["X Response"]] = (
                        (df[selections["X Response"]].expanding().mean())
                        if calculation == "mean"
                        else df[selections["X Response"]]
                        .expanding()
                        .quantile(0.1 if calculation == "p10" else 0.9)
                    )
                    df_groups.append(df)
                df_stat = pd.concat(df_groups)

            else:
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
        [("Response", {})] + [(group, {}) for group in groups] + table_statistics_base()
    )
    print(table_statistics_base())
    print(responses)
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

            if response in volumemodel.property_columns:
                for _, values in table_stats:
                    if "format" in values:
                        values["format"] = Format(precision=3)

        columns = [{**{"name": i[0], "id": i[0]}, **i[1]} for i in table_stats]
    else:
        dframe = (
            dframe[responses + groups].groupby(groups).mean().reset_index()
            if groups
            else dframe[responses].mean().to_frame().T
        )
        columns = [
            {"id": col, "name": col, "type": "numeric", "format": Format(precision=3)}
            for col in dframe.columns
        ]
        tables = dframe.iloc[::-1].to_dict("records")
    return columns, tables


def filter_df(dframe, filters):
    for filt, values in filters.items():
        dframe = dframe.loc[dframe[filt].isin(values)]

    return dframe
