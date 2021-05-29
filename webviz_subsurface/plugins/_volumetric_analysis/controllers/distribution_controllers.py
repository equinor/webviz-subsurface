from typing import Callable, Tuple, List
import pandas as pd
from pandas.api.types import is_numeric_dtype
import numpy as np
import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from dash_table.Format import Format
import dash_html_components as html
import dash_table
import plotly.express as px
import plotly.graph_objects as go

from webviz_subsurface._models import InplaceVolumesModel
from webviz_subsurface._abbreviations.volume_terminology import (
    volume_description,
    volume_unit,
)

from ..figures import create_figure

# pylint: disable=too-many-statements, too-many-locals, too-many-branches
def distribution_controllers(
    app: dash.Dash, get_uuid: Callable, volumemodel: InplaceVolumesModel
):
    @app.callback(
        Output(
            {"id": get_uuid("main-voldist"), "element": "graph", "page": ALL}, "figure"
        ),
        Output(
            {"id": get_uuid("main-voldist"), "wrapper": "table", "page": ALL},
            "children",
        ),
        Input(get_uuid("selections-voldist"), "data"),
        Input(
            {"id": get_uuid("main-voldist"), "element": "plot-table-select"}, "value"
        ),
        State(get_uuid("page-selected-voldist"), "data"),
        State({"id": get_uuid("main-voldist"), "element": "graph", "page": ALL}, "id"),
        State(
            {"id": get_uuid("main-voldist"), "wrapper": "table", "page": ALL},
            "id",
        ),
    )
    def _update_plots(
        selections: dict,
        plot_table_select: str,
        page_selected: str,
        figure_ids: list,
        table_wrapper_ids: list,
    ) -> Tuple[list, list, list]:
        ctx = dash.callback_context.triggered[0]
        if page_selected not in ["1p1t", "custom"]:
            raise PreventUpdate

        selections = selections[page_selected]

        table_clicked = "plot-table-select" in ctx["prop_id"]
        initial_callback = selections.get("update") is None
        if not initial_callback and not table_clicked:
            if not selections["update"]:
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
        else:
            figure = dash.no_update

        # Make tables
        if not (plot_table_select == "graph" and page_selected == "custom"):
            if selections["sync_table"]:
                table_wrapper_children = make_table_wrapper_children(
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
                    page_selected=page_selected,
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
                table_wrapper_children = make_table_wrapper_children(
                    dframe=df_for_table,
                    responses=selections["table_responses"],
                    groups=selections["Group by"],
                    volumemodel=volumemodel,
                    tabletype=selections["Table type"],
                    page_selected=page_selected,
                )
        else:
            table_wrapper_children = dash.no_update

        figures = []
        for fig_id in figure_ids:
            if fig_id["page"] == page_selected:
                figures.append(figure)
            else:
                figures.append(dash.no_update)

        table_wrappers = []
        for wrap_id in table_wrapper_ids:
            if wrap_id["page"] == page_selected:
                table_wrappers.append(table_wrapper_children)
            else:
                table_wrappers.append(dash.no_update)

        return (figures, table_wrappers)

    @app.callback(
        Output(
            {
                "id": get_uuid("main-voldist"),
                "chart": ALL,
                "selector": ALL,
                "page": "per_zr",
            },
            "figure",
        ),
        Input(get_uuid("selections-voldist"), "data"),
        State(get_uuid("page-selected-voldist"), "data"),
        State(
            {
                "id": get_uuid("main-voldist"),
                "chart": ALL,
                "selector": ALL,
                "page": "per_zr",
            },
            "id",
        ),
    )
    def _update_plots_per_region_zone(
        selections: dict,
        page_selected: str,
        figure_ids: List[dict],
    ) -> list:
        if page_selected != "per_zr":
            raise PreventUpdate

        selections = selections[page_selected]

        initial_callback = selections.get("update") is None
        if not initial_callback:
            if not selections["update"]:
                raise PreventUpdate

        dframe = volumemodel.dataframe.copy()
        dframe = filter_df(dframe, selections["filters"])

        figs = {}
        for selector in ["ZONE", "REGION", "FACIES"]:
            groups = ["ENSEMBLE", "REAL"]
            if selector in volumemodel.selectors:
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
                texttemplate = (
                    "%{text:.3s}"
                    if selections["X Response"] in volumemodel.volume_columns
                    else "%{text:.3g}"
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
                    ).update_traces(texttemplate=texttemplate, textposition="auto"),
                }

        output_figs = []
        for fig_id in figure_ids:
            output_figs.append(figs[fig_id["selector"]][fig_id["chart"]])
        return output_figs

    @app.callback(
        Output(
            {"id": get_uuid("main-voldist"), "element": "plot", "page": "conv"},
            "figure",
        ),
        Input(get_uuid("selections-voldist"), "data"),
        State(get_uuid("page-selected-voldist"), "data"),
    )
    def _update_convergence_plot(selections: dict, page_selected: str) -> go.Figure:
        if page_selected != "conv":
            raise PreventUpdate

        selections = selections[page_selected]

        initial_callback = selections.get("update") is None
        if not initial_callback:
            if not selections["update"]:
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


# pylint: disable=too-many-locals
def make_table_wrapper_children(
    dframe: pd.DataFrame,
    responses: list,
    groups: list,
    volumemodel: InplaceVolumesModel,
    tabletype: str,
    page_selected: str,
) -> Tuple[list, list]:

    groups = [x for x in groups if x != "REAL"] if groups is not None else []

    if tabletype == "Statistics table":
        statcols = ["Mean", "Stddev", "P10", "P90", "Minimum", "Maximum"]

        df_groups = dframe.groupby(groups) if groups else [(None, dframe)]

        data_properties = []
        data_volcols = []
        for response in responses:
            if not is_numeric_dtype(dframe[response]):
                continue
            for name, df_group in df_groups:
                values = df_group[response]
                data = {
                    "Response"
                    if response in volumemodel.volume_columns
                    else "Property": response,
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
                if response in volumemodel.volume_columns:
                    data_volcols.append(data)
                else:
                    data_properties.append(data)

        if page_selected == "custom":
            height = "43vh" if all([data_volcols, data_properties]) else "88vh"
        else:
            height = "22vh" if all([data_volcols, data_properties]) else "44vh"

        return html.Div(
            children=[
                html.Div(
                    style={"margin-bottom": "30px"},
                    children=create_data_table(
                        volumemodel=volumemodel,
                        columns=[
                            {"id": col, "name": col} for col in ["Response"] + groups
                        ]
                        + create_table_columns(
                            statcols, volumemodel, use_si_format=True
                        ),
                        data=data_volcols,
                        height=height,
                    ),
                ),
                create_data_table(
                    volumemodel=volumemodel,
                    columns=[{"id": col, "name": col} for col in ["Property"] + groups]
                    + create_table_columns(statcols, volumemodel, use_si_format=False),
                    data=data_properties,
                    height=height,
                ),
            ]
        )

    # if table type datatable
    dframe = (
        dframe[responses + groups].groupby(groups).mean().reset_index()
        if groups
        else dframe[responses].mean().to_frame().T
    )
    return html.Div(
        children=[
            create_data_table(
                volumemodel=volumemodel,
                columns=create_table_columns(dframe.columns, volumemodel),
                data=dframe.iloc[::-1].to_dict("records"),
                height="88vh" if page_selected == "custom" else "44vh",
            )
        ]
    )


def filter_df(dframe: pd.DataFrame, filters: list) -> pd.DataFrame:
    for filt, values in filters.items():
        dframe = dframe.loc[dframe[filt].isin(values)]
    return dframe


def create_table_columns(
    columns: list, volumemodel: InplaceVolumesModel, use_si_format: bool = None
) -> List[dict]:
    return [
        {
            "id": col,
            "name": col,
            "type": "numeric",
            "format": {"locale": {"symbol": ["", ""]}, "specifier": "$.4s"}
            if col in volumemodel.volume_columns or use_si_format
            else Format(precision=3),
        }
        for col in columns
    ]


# pylint: disable=inconsistent-return-statements
def create_data_table(
    volumemodel: InplaceVolumesModel,
    data: list,
    columns: list,
    height: str,
) -> dash_table.DataTable:
    if not data:
        return

    style_cell_conditional = [
        {"if": {"column_id": c}, "textAlign": "left"}
        for c in volumemodel.selectors + ["Response", "Property"]
    ]
    style_cell_conditional.extend(
        [
            {"if": {"column_id": c}, "width": "15%"}
            for c in volumemodel.selectors + ["Response", "Property"]
        ]
    )
    return dash_table.DataTable(
        sort_action="native",
        sort_mode="multi",
        filter_action="native",
        columns=columns,
        data=data,
        style_cell_conditional=style_cell_conditional,
        style_table={
            "height": height,
            "overflowY": "auto",
        },
    )
