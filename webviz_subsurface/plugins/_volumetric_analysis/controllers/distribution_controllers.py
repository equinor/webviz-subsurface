from typing import Callable, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, html
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
from ..utils.utils import move_to_end_of_list, to_ranges
from ..views.distribution_main_layout import (
    convergence_plot_layout,
    custom_plotting_layout,
    plots_per_zone_region_layout,
)


# pylint: disable=too-many-statements
def distribution_controllers(
    get_uuid: Callable, volumemodel: InplaceVolumesModel
) -> None:
    @callback(
        Output({"id": get_uuid("main-voldist"), "page": "custom"}, "children"),
        Input(get_uuid("selections"), "data"),
        State(get_uuid("page-selected"), "data"),
    )
    def _update_page_custom(selections: dict, page_selected: str) -> tuple:

        if page_selected != "custom":
            raise PreventUpdate

        selections = selections[page_selected]
        if not selections["update"]:
            raise PreventUpdate

        selected_data = [
            selections[x]
            for x in ["Subplots", "Color by", "X Response", "Y Response"]
            if selections[x] is not None
        ]
        groups = ["REAL"]
        parameters = []
        for item in selected_data:
            if item in volumemodel.selectors and item not in groups:
                groups.append(item)
            if item in volumemodel.parameters and item not in parameters:
                parameters.append(item)

        # for bo/bg the data should be grouped on fluid zone
        if any(x in selected_data for x in ["BO", "BG"]) and "FLUID_ZONE" not in groups:
            if "BO" in selected_data and "BG" in selected_data:
                return html.Div(
                    "Can't plot BO against BG", style={"margin-top": "40px"}
                )
            selections["filters"]["FLUID_ZONE"] = [
                "oil" if "BO" in selected_data else "gas"
            ]

        dframe = volumemodel.get_df(
            filters=selections["filters"], groups=groups, parameters=parameters
        )

        if dframe.empty:
            return html.Div(
                "No data left after filtering", style={"margin-top": "40px"}
            )

        df_for_figure = (
            dframe
            if not (selections["Plot type"] == "bar" and not "REAL" in selected_data)
            else dframe.groupby([x for x in groups if x != "REAL"]).mean().reset_index()
        )
        figure = (
            create_figure(
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
                boxmode=selections["barmode"],
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
            )
            .add_annotation(fluid_annotation(selections))
            .update_xaxes({"matches": None} if not selections["X axis matches"] else {})
            .update_yaxes({"matches": None} if not selections["Y axis matches"] else {})
            .update_xaxes(
                {"type": "category", "tickangle": 45, "tickfont_size": 12}
                if selections["X Response"] in volumemodel.selectors
                else {}
            )
        )

        return custom_plotting_layout(
            figure=figure,
            tables=make_tables(
                dframe=dframe,
                responses=list({selections["X Response"], selections["Y Response"]}),
                groups=groups,
                volumemodel=volumemodel,
                page_selected=page_selected,
                selections=selections,
                table_type="Statistics table",
                view_height=37,
            )
            if selections["bottom_viz"] == "table"
            else None,
        )

    @callback(
        Output({"id": get_uuid("main-table"), "page": "table"}, "children"),
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

        return make_tables(
            dframe=dframe,
            responses=selections["table_responses"],
            groups=selections["Group by"],
            view_height=85,
            table_type=selections["Table type"],
            volumemodel=volumemodel,
            page_selected=page_selected,
            selections=selections,
        )

    @callback(
        Output({"id": get_uuid("main-voldist"), "page": "per_zr"}, "children"),
        Input(get_uuid("selections"), "data"),
        State(get_uuid("page-selected"), "data"),
    )
    def _update_page_per_zr(selections: dict, page_selected: str) -> list:
        if page_selected != "per_zr":
            raise PreventUpdate

        selections = selections[page_selected]
        if not selections["update"]:
            raise PreventUpdate

        figs = []
        selectors = [
            x
            for x in ["ZONE", "REGION", "FACIES", "FIPNUM", "SET"]
            if x in volumemodel.selectors
        ]
        color = selections["Color by"] is not None
        for selector in selectors:
            groups = list({selector, selections["Color by"]}) if color else [selector]
            dframe = volumemodel.get_df(filters=selections["filters"], groups=groups)
            piefig = (
                (
                    create_figure(
                        plot_type="pie",
                        data_frame=dframe,
                        values=selections["X Response"],
                        names=selector,
                        color_discrete_sequence=selections["Colorscale"],
                        color=selector,
                    )
                    .update_traces(marker_line=dict(color="#000000", width=1))
                    .update_layout(margin=dict(l=10, b=10))
                )
                if not color
                else []
            )
            barfig = create_figure(
                plot_type="bar",
                data_frame=dframe,
                x=selector,
                y=selections["X Response"],
                title=f"{selections['X Response']} per {selector}",
                barmode="overlay" if selector == selections["Color by"] else "group",
                layout={"bargap": 0.05},
                color_discrete_sequence=selections["Colorscale"],
                color=selections["Color by"],
                text=selections["X Response"],
                xaxis=dict(type="category", tickangle=45, tickfont_size=17, title=None),
            ).update_traces(
                texttemplate=(
                    "%{text:.3s}"
                    if selections["X Response"] in volumemodel.volume_columns
                    else "%{text:.3g}"
                ),
                textposition="auto",
            )

            if selections["X Response"] not in volumemodel.hc_responses:
                barfig.add_annotation(fluid_annotation(selections))
            figs.append([piefig, barfig])
        return plots_per_zone_region_layout(figs)

    @callback(
        Output({"id": get_uuid("main-voldist"), "page": "conv"}, "children"),
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

        if dframe.empty:
            return html.Div(
                "No data left after filtering", style={"margin-top": "40px"}
            )

        dfs = []
        df_groups = dframe.groupby(subplots) if subplots else [(None, dframe)]
        for _, df in df_groups:
            for calculation in ["mean", "p10", "p90"]:
                df_stat = df.reset_index(drop=True).copy()
                df_stat[selections["X Response"]] = (
                    (df_stat[selections["X Response"]].expanding().mean())
                    if calculation == "mean"
                    else df_stat[selections["X Response"]]
                    .expanding()
                    .quantile(0.1 if calculation == "p90" else 0.9)
                )
                df_stat["calculation"] = calculation
                df_stat["index"] = df_stat.index + 1
                dfs.append(df_stat)
        if dfs:
            dframe = pd.concat(dfs)

        title = (
            f"<b>Convergence plot of mean/p10/p90 for {selections['X Response']} </b>"
            "  -  shaded areas indicates failed/filtered out realizations"
        )

        figure = (
            create_figure(
                plot_type="line",
                data_frame=dframe,
                x="REAL",
                y=selections["X Response"],
                facet_col=selections["Subplots"],
                color="calculation",
                custom_data=["calculation", "index"],
                title=title,
                yaxis=dict(showticklabels=True),
            )
            .update_traces(
                hovertemplate=(
                    f"{selections['X Response']} %{{y}} <br>"
                    f"%{{customdata[0]}} for realizations {dframe['REAL'].min()}-%{{x}}<br>"
                    "Realization count: %{customdata[1]} <extra></extra>"
                ),
                line_width=3.5,
            )
            .update_traces(line_color="black", selector={"name": "mean"})
            .update_traces(
                line=dict(color="firebrick", dash="dash"), selector={"name": "p10"}
            )
            .update_traces(
                line=dict(color="royalblue", dash="dash"), selector={"name": "p90"}
            )
            .update_xaxes({"matches": None} if not selections["X axis matches"] else {})
            .update_yaxes({"matches": None} if not selections["Y axis matches"] else {})
        )
        if selections["X Response"] not in volumemodel.hc_responses:
            figure.add_annotation(fluid_annotation(selections))

        missing_reals = [
            x
            for x in range(dframe["REAL"].min(), dframe["REAL"].max())
            if x not in dframe["REAL"].unique()
        ]
        if missing_reals:
            for real_range in to_ranges(missing_reals):
                figure.add_vrect(
                    x0=real_range[0] - 0.5,
                    x1=real_range[1] + 0.5,
                    fillcolor="gainsboro",
                    layer="below",
                    opacity=0.4,
                    line_width=0,
                )

        return convergence_plot_layout(figure=figure)


# pylint: disable=too-many-locals
def make_tables(
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
        statcols = ["Mean", "Stddev", "P90", "P10", "Min", "Max"]
        groups = [x for x in groups if x != "REAL"]
        responses = [x for x in responses if x != "REAL" and x is not None]
        df_groups = dframe.groupby(groups) if groups else [(None, dframe)]

        data_properties = []
        data_volcols = []
        for response in responses:
            if not is_numeric_dtype(dframe[response]):
                continue
            for name, df in df_groups:
                values = df[response]
                data = {
                    "Mean": values.mean(),
                    "Stddev": values.std(),
                    "P10": np.nanpercentile(values, 90),
                    "P90": np.nanpercentile(values, 10),
                    "Min": values.min(),
                    "Max": values.max(),
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
                    data["Response"] = response
                    data_volcols.append(data)
                else:
                    data["Property"] = response
                    data_properties.append(data)

        if data_volcols and data_properties:
            view_height = view_height / 2

        return [
            create_data_table(
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
            )
            for col, data in zip(
                ["Response", "Property"], [data_volcols, data_properties]
            )
        ]

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
    return [
        create_data_table(
            selectors=volumemodel.selectors,
            columns=create_table_columns(
                columns=dframe.columns, use_si_format=volumemodel.volume_columns
            ),
            data=dframe.iloc[::-1].to_dict("records"),
            height=f"{view_height}vh",
            table_id={"table_id": f"{page_selected}-meantable"},
        )
    ]
