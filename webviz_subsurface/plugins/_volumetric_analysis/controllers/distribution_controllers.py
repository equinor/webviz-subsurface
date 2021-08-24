from typing import Callable, List, Optional
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
import webviz_core_components as wcc
from webviz_config import WebvizConfigTheme
from webviz_subsurface._components.tornado._tornado_data import TornadoData
from webviz_subsurface._components.tornado._tornado_bar_chart import TornadoBarChart
from webviz_subsurface._components.tornado._tornado_table import TornadoTable
from webviz_subsurface._models import InplaceVolumesModel
from webviz_subsurface._abbreviations.volume_terminology import (
    volume_description,
    volume_unit,
)
from webviz_subsurface._figures import create_figure
from ..utils.utils import update_relevant_components


# pylint: disable=too-many-statements, too-many-locals, too-many-branches
def distribution_controllers(
    app: dash.Dash,
    get_uuid: Callable,
    volumemodel: InplaceVolumesModel,
    theme: WebvizConfigTheme,
) -> None:
    @app.callback(
        Output(
            {"id": get_uuid("main-voldist"), "element": "graph", "page": ALL}, "figure"
        ),
        Output(
            {"id": get_uuid("main-voldist"), "wrapper": "table", "page": ALL},
            "children",
        ),
        Input(get_uuid("selections"), "data"),
        Input(
            {"id": get_uuid("main-voldist"), "element": "plot-table-select"}, "value"
        ),
        State(get_uuid("page-selected"), "data"),
        State({"id": get_uuid("main-voldist"), "element": "graph", "page": ALL}, "id"),
        State({"id": get_uuid("main-voldist"), "wrapper": "table", "page": ALL}, "id"),
    )
    def _update_page_1p1t_and_custom(
        selections: dict,
        plot_table_select: str,
        page_selected: str,
        figure_ids: list,
        table_wrapper_ids: list,
    ) -> tuple:

        if page_selected not in ["1p1t", "custom"]:
            raise PreventUpdate

        selections = selections[page_selected]
        if not selections["update"]:
            raise PreventUpdate

        groups = ["REAL"]
        parameters = []
        responses = []
        for item in ["Subplots", "Color by", "X Response", "Y Response"]:
            if selections[item] is not None:
                if (
                    selections[item] in volumemodel.selectors
                    and selections[item] not in groups
                ):
                    groups.append(selections[item])
                if (
                    selections[item] in volumemodel.parameters
                    and selections[item] not in parameters
                ):
                    parameters.append(selections[item])
                if (
                    item in ["X Response", "Y Response"]
                    and selections[item] not in responses
                ):
                    responses.append(selections[item])

        dframe = volumemodel.get_df(
            filters=selections["filters"], groups=groups, parameters=parameters
        )

        if not (plot_table_select == "table" and page_selected == "custom"):
            df_for_figure = (
                dframe
                if not (selections["Plot type"] == "bar" and groups != ["REAL"])
                else dframe.groupby([x for x in groups if x != "REAL"])
                .mean()
                .reset_index()
            )
            figure = create_figure(
                plot_type=selections["Plot type"],
                data_frame=df_for_figure,
                x=selections["X Response"],
                y=selections["Y Response"],
                nbins=selections["hist_bins"],
                facet_col=selections["Subplots"],
                color=selections["Color by"],
                color_discrete_sequence=selections["Colorscale"],
                color_continuous_scale=selections["Colorscale"],
                barmode=selections["barmode"],
                layout=dict(
                    title=dict(
                        text=(
                            f"{volume_description(selections['X Response'])}"
                            + (
                                f" [{volume_unit(selections['X Response'])}]"
                                if selections["X Response"]
                                in volumemodel.volume_columns
                                else ""
                            )
                        ),
                        x=0.5,
                        xref="paper",
                        font=dict(size=18),
                    ),
                ),
                yaxis=dict(showticklabels=True),
            ).add_annotation(fluid_annotation(selections))

            if selections["X Response"] in volumemodel.selectors:
                figure.update_xaxes(
                    dict(type="category", tickangle=45, tickfont_size=12)
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
            table_wrapper_children = make_table_wrapper_children(
                dframe=dframe,
                responses=responses,
                groups=groups,
                volumemodel=volumemodel,
                page_selected=page_selected,
                selections=selections,
                table_type="Statistics table",
                view_height=42 if page_selected == "1p1t" else 86,
            )
        else:
            table_wrapper_children = dash.no_update

        return tuple(
            update_relevant_components(
                id_list=id_list,
                update_info=[
                    {
                        "new_value": val,
                        "conditions": {"page": page_selected},
                    }
                ],
            )
            for val, id_list in zip(
                [figure, table_wrapper_children], [figure_ids, table_wrapper_ids]
            )
        )

    @app.callback(
        Output(
            {"id": get_uuid("main-table"), "wrapper": "table", "page": "table"},
            "children",
        ),
        Input(get_uuid("selections"), "data"),
        State(get_uuid("page-selected"), "data"),
    )
    def _update_page_tables(
        selections: dict,
        page_selected: str,
    ) -> list:

        if page_selected != "table":
            raise PreventUpdate

        selections = selections[page_selected]
        if not selections["update"]:
            raise PreventUpdate

        table_groups = ["ENSEMBLE", "REAL"]
        if selections["Group by"] is not None:
            table_groups.extend(
                [x for x in selections["Group by"] if x not in table_groups]
            )
        dframe = volumemodel.get_df(
            filters=selections["filters"],
            groups=table_groups,
        )

        return make_table_wrapper_children(
            dframe=dframe,
            responses=selections["table_responses"],
            groups=selections["Group by"],
            view_height=88,
            table_type=selections["Table type"],
            volumemodel=volumemodel,
            page_selected=page_selected,
            selections=selections,
        )

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
        Input(get_uuid("selections"), "data"),
        State(get_uuid("page-selected"), "data"),
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
    def _update_page_per_zr(
        selections: dict,
        page_selected: str,
        figure_ids: List[dict],
    ) -> list:
        if page_selected != "per_zr":
            raise PreventUpdate

        selections = selections[page_selected]
        if not selections["update"]:
            raise PreventUpdate

        figs = {}
        for selector in [x["selector"] for x in figure_ids]:
            dframe = volumemodel.get_df(
                filters=selections["filters"], groups=[selector]
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
                    data_frame=dframe,
                    values=selections["X Response"],
                    names=selector,
                    title=f"{selections['X Response']} per {selector}",
                    color_discrete_sequence=selections["Colorscale"],
                    color=selector,
                )
                .update_traces(marker_line=dict(color="#000000", width=1))
                .update_layout(margin=dict(l=10, b=10)),
                "bar": create_figure(
                    plot_type="bar",
                    data_frame=dframe,
                    x=selector,
                    y=selections["X Response"],
                    color_discrete_sequence=px.colors.diverging.BrBG_r,
                    color=selections["Color by"],
                    text=selections["X Response"],
                    xaxis=dict(
                        type="category", tickangle=45, tickfont_size=17, title=None
                    ),
                )
                .update_traces(texttemplate=texttemplate, textposition="auto")
                .add_annotation(fluid_annotation(selections)),
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
        Input(get_uuid("selections"), "data"),
        State(get_uuid("page-selected"), "data"),
    )
    def _update_page_conv(selections: dict, page_selected: str) -> go.Figure:
        if page_selected != "conv":
            raise PreventUpdate

        selections = selections[page_selected]
        if not selections["update"]:
            raise PreventUpdate

        subplots = selections["Subplots"] if selections["Subplots"] is not None else []
        groups = ["REAL"]
        if subplots and subplots not in groups:
            groups.append(subplots)

        dframe = volumemodel.get_df(filters=selections["filters"], groups=groups)
        dframe = dframe.sort_values(by=["REAL"])

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
                    .quantile(0.1 if calculation == "p90" else 0.9)
                )
                df_stat["calculation"] = calculation
                dfs.append(df_stat)
        if dfs:
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
            .add_annotation(fluid_annotation(selections))
        )

        if selections["Subplots"] is not None:
            if not selections["X axis matches"]:
                figure.update_xaxes({"matches": None})
            if not selections["Y axis matches"]:
                figure.update_yaxes(dict(matches=None))
        return figure

    @app.callback(
        Output(
            {
                "id": get_uuid("main-tornado"),
                "element": "bulktornado",
                "page": "tornado",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-tornado"),
                "element": "inplacetornado",
                "page": "tornado",
            },
            "figure",
        ),
        Output(
            {
                "id": get_uuid("main-tornado"),
                "wrapper": "table",
                "page": "tornado",
            },
            "children",
        ),
        Input(get_uuid("selections"), "data"),
        State(get_uuid("page-selected"), "data"),
    )
    def _update_page_tornado(selections: dict, page_selected: str) -> go.Figure:

        if page_selected != "tornado":
            raise PreventUpdate

        selections = selections[page_selected]
        if not selections["update"]:
            raise PreventUpdate

        filters = selections["filters"].copy()

        figures = []
        tables = []
        for plot_id in ["left", "right"]:
            response = selections[f"Response {plot_id}"]
            sensfilter = selections[f"Sensitivities {plot_id}"]

            if selections["Reference"] not in sensfilter:
                sensfilter.append(selections["Reference"])

            filters.update(SENSNAME=sensfilter)

            groups = ["REAL", "ENSEMBLE", "SENSNAME", "SENSCASE", "SENSTYPE"]
            df_for_tornado = volumemodel.get_df(filters=filters, groups=groups)
            df_for_tornado.rename(columns={response: "VALUE"}, inplace=True)

            tornado_data = TornadoData(
                dframe=df_for_tornado,
                reference=selections["Reference"],
                response_name=response,
                scale=selections["Scale"],
                cutbyref=bool(selections["Remove no impact"]),
            )
            figure = TornadoBarChart(
                tornado_data=tornado_data,
                plotly_theme=theme.plotly_theme,
                label_options=selections["labeloptions"],
                number_format="#.3g",
                use_true_base=selections["Scale"] == "True",
                show_realization_points=bool(selections["real_scatter"]),
            ).figure

            figure.update_xaxes(
                gridwidth=1,
                gridcolor="whitesmoke",
                showgrid=True,
                side="bottom",
                title=None,
            ).update_layout(
                title=dict(
                    text=f"Tornadoplot for {response} <br>"
                    + f"Fluid zone: {(' + ').join(selections['filters']['FLUID_ZONE'])}",
                    font=dict(size=18),
                ),
                margin={"t": 70},
                hovermode="closest",
            ).update_traces(
                hovertemplate="REAL: %{text}<extra></extra>",
                selector={"type": "scatter"},
            )

            figures.append(figure)

            tornado_table = TornadoTable(tornado_data=tornado_data)
            table_data = tornado_table.as_plotly_table
            for data in table_data:
                data["Reference"] = tornado_data.reference_average
            tables.append(table_data)

        return (
            figures[0],
            figures[1],
            html.Div(
                children=[
                    html.Div(
                        style={"margin-top": "20px"},
                        children=create_data_table(
                            volumemodel=volumemodel,
                            columns=tornado_table.columns
                            + create_table_columns(
                                columns=["Reference"],
                                format_columns=["Reference"],
                                use_si_format=True,
                            ),
                            data=table,
                            height="20vh",
                            table_id={"table_id": f"{page_selected}-table{idx}"},
                        ),
                    )
                    for idx, table in enumerate(tables)
                ]
            ),
        )


# pylint: disable=too-many-locals
def make_table_wrapper_children(
    dframe: pd.DataFrame,
    responses: list,
    volumemodel: InplaceVolumesModel,
    selections: dict,
    table_type: str,
    view_height: float,
    page_selected: str,
    groups: Optional[list] = None,
) -> html.Div:

    groups = groups if groups is not None else []

    if table_type == "Statistics table":
        statcols = ["Mean", "Stddev", "P90", "P10", "Minimum", "Maximum"]
        groups = [x for x in groups if x != "REAL"]
        df_groups = dframe.groupby(groups) if groups else [(None, dframe)]

        data_properties = []
        data_volcols = []
        for response in responses:
            if not is_numeric_dtype(dframe[response]):
                continue
            for name, df in df_groups:
                values = df[response]
                data = {
                    "Response"
                    if response in volumemodel.volume_columns
                    else "Property": response,
                    "Mean": values.mean(),
                    "Stddev": values.std(),
                    "P10": np.nanpercentile(values, 90),
                    "P90": np.nanpercentile(values, 10),
                    "Minimum": values.min(),
                    "Maximum": values.max(),
                }
                if "FLUID_ZONE" not in groups:
                    data.update(
                        FLUID_ZONE=(" + ").join(selections["filters"]["FLUID_ZONE"])
                    )

                for idx, group in enumerate(groups):
                    data[group] = (
                        name if isinstance(name, str) == 1 else list(name)[idx]
                    )
                if response in volumemodel.volume_columns:
                    data_volcols.append(data)
                else:
                    data_properties.append(data)

        if data_volcols and data_properties:
            view_height = view_height / 2

        return html.Div(
            children=[
                html.Div(
                    style={"margin-top": "20px"},
                    children=create_data_table(
                        volumemodel=volumemodel,
                        columns=create_table_columns(
                            columns=[col]
                            + [x for x in groups if x != "FLUID_ZONE"]
                            + statcols
                            + ["FLUID_ZONE"],
                            format_columns=statcols,
                            use_si_format=col == "Response",
                        ),
                        data=data,
                        height=f"{view_height}vh",
                        table_id={"table_id": f"{page_selected}-{col}"},
                    ),
                )
                for col, data in zip(
                    ["Response", "Property"], [data_volcols, data_properties]
                )
            ]
        )

    # if table type Mean table
    groupby_real = (
        selections["Group by"] is not None and "REAL" in selections["Group by"]
    )
    if "REAL" in groups and not groupby_real:
        groups.remove("REAL")

    columns = responses + [x for x in groups if x not in responses]
    dframe = (
        dframe[columns].groupby(groups).mean().reset_index()
        if groups
        else dframe[responses].mean().to_frame().T
    )

    if "FLUID_ZONE" not in dframe:
        dframe["FLUID_ZONE"] = (" + ").join(selections["filters"]["FLUID_ZONE"])

    dframe = dframe[[x for x in dframe.columns if x != "FLUID_ZONE"] + ["FLUID_ZONE"]]
    return html.Div(
        children=[
            create_data_table(
                volumemodel=volumemodel,
                columns=create_table_columns(
                    columns=dframe.columns,
                    format_columns=dframe.columns,
                    volumemodel=volumemodel,
                ),
                data=dframe.iloc[::-1].to_dict("records"),
                height=f"{view_height}vh",
                table_id={"table_id": f"{page_selected}-meantable"},
            )
        ]
    )


def create_table_columns(
    columns: list,
    volumemodel: Optional[InplaceVolumesModel] = None,
    format_columns: Optional[list] = None,
    use_si_format: Optional[bool] = None,
) -> List[dict]:

    format_columns = format_columns if format_columns is not None else []

    table_columns = []
    for col in columns:
        data = {"id": col, "name": col}
        if col in format_columns:
            data.update(
                {
                    "type": "numeric",
                    "format": {"locale": {"symbol": ["", ""]}, "specifier": "$.4s"}
                    if use_si_format
                    or volumemodel is not None
                    and col in volumemodel.volume_columns
                    else Format(precision=3),
                }
            )
        table_columns.append(data)
    return table_columns


# pylint: disable=inconsistent-return-statements
def create_data_table(
    volumemodel: InplaceVolumesModel,
    columns: list,
    height: str,
    data: List[dict],
    table_id: dict,
) -> dash_table.DataTable:

    if not data:
        return []

    style_cell_conditional = [
        {"if": {"column_id": c}, "textAlign": "left"}
        for c in [x for x in volumemodel.selectors if x != "FLUID_ZONE"]
        + ["Response", "Property", "Sensitivity"]
    ]
    style_cell_conditional.extend(
        [
            {"if": {"column_id": c}, "width": "10%"}
            for c in volumemodel.selectors + ["Response", "Property", "Sensitivity"]
        ]
    )
    style_data_conditional = fluid_table_style()

    return wcc.WebvizPluginPlaceholder(
        id={"request": "table_data", "table_id": table_id["table_id"]},
        buttons=["expand", "download"],
        children=dash_table.DataTable(
            id=table_id,
            sort_action="native",
            sort_mode="multi",
            filter_action="native",
            columns=columns,
            data=data,
            style_as_list_view=True,
            style_cell_conditional=style_cell_conditional,
            style_data_conditional=style_data_conditional,
            style_table={
                "height": height,
                "overflowY": "auto",
            },
        ),
    )


def fluid_table_style() -> list:
    fluid_colors = {
        "oil": "#007079",
        "gas": "#FF1243",
        "water": "#ADD8E6",
    }
    return [
        {
            "if": {
                "filter_query": "{FLUID_ZONE} = " + f"'{fluid}'",
                "column_id": "FLUID_ZONE",
            },
            "color": color,
            "fontWeight": "bold",
        }
        for fluid, color in fluid_colors.items()
    ]


def fluid_annotation(selections: dict) -> dict:
    fluid_text = (" + ").join(selections["filters"]["FLUID_ZONE"])
    return dict(
        visible=bool(selections["Fluid annotation"])
        and selections["Subplots"] != "FLUID_ZONE",
        x=1,
        y=1,
        xref="paper",
        yref="paper",
        showarrow=False,
        text="Fluid zone<br>" + fluid_text,
        font=dict(size=15, color="black"),
        bgcolor="#E8E8E8",
    )
