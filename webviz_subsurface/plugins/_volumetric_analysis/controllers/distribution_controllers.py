from typing import Callable, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, html, no_update
from dash.exceptions import PreventUpdate
from pandas.api.types import is_numeric_dtype

from webviz_subsurface._abbreviations.volume_terminology import (
    volume_description,
    volume_unit,
)
from webviz_subsurface._figures import create_figure
from webviz_subsurface._models import InplaceVolumesModel

from ..utils.table_and_figure_utils import (
    create_data_table,
    create_table_columns,
    fluid_annotation,
)
from ..utils.utils import move_to_end_of_list, update_relevant_components


# pylint: disable=too-many-statements, too-many-branches
def distribution_controllers(
    get_uuid: Callable, volumemodel: InplaceVolumesModel
) -> None:
    @callback(
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
            figure = no_update

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
            table_wrapper_children = no_update

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

    @callback(
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

        table_groups = (
            ["ENSEMBLE", "REAL"]
            if selections["Table type"] == "Statistics table"
            else ["ENSEMBLE"]
        )
        if selections["Group by"] is not None:
            table_groups.extend(
                [x for x in selections["Group by"] if x not in table_groups]
            )
        dframe = volumemodel.get_df(filters=selections["filters"], groups=table_groups)

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

    @callback(
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

    @callback(
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
                        name if not isinstance(name, tuple) else list(name)[idx]
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
                        selectors=volumemodel.selectors,
                        columns=create_table_columns(
                            columns=move_to_end_of_list(
                                "FLUID_ZONE", [col] + groups + statcols
                            ),
                            text_columns=[col] + groups,
                            use_si_format=statcols if col == "Response" else None,
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

    dframe = dframe[move_to_end_of_list("FLUID_ZONE", dframe.columns)]
    return html.Div(
        style={"margin-top": "20px"},
        children=[
            create_data_table(
                selectors=volumemodel.selectors,
                columns=create_table_columns(
                    columns=dframe.columns, use_si_format=volumemodel.volume_columns
                ),
                data=dframe.iloc[::-1].to_dict("records"),
                height=f"{view_height}vh",
                table_id={"table_id": f"{page_selected}-meantable"},
            )
        ],
    )
