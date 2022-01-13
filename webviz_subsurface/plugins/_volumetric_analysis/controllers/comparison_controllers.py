from typing import Callable, Optional, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, callback, callback_context, dash_table, html
from dash.exceptions import PreventUpdate

from webviz_subsurface._figures import create_figure
from webviz_subsurface._models import InplaceVolumesModel

from ..utils.table_and_figure_utils import (
    add_correlation_line,
    create_data_table,
    create_table_columns,
)
from ..utils.utils import move_to_end_of_list
from ..views.comparison_layout import (
    comparison_qc_plots_layout,
    comparison_table_layout,
)


# pylint: disable=too-many-locals
def comparison_controllers(
    get_uuid: Callable,
    volumemodel: InplaceVolumesModel,
) -> None:
    @callback(
        Output({"id": get_uuid("main-src-comp"), "wrapper": "table"}, "children"),
        Input(get_uuid("selections"), "data"),
        Input({"id": get_uuid("main-src-comp"), "element": "display-option"}, "value"),
        State(get_uuid("page-selected"), "data"),
    )
    def _update_page_src_comp(
        selections: dict,
        display_option: str,
        page_selected: str,
    ) -> html.Div:
        ctx = callback_context.triggered[0]

        if page_selected != "src-comp":
            raise PreventUpdate

        selections = selections[page_selected]
        if not "display-option" in ctx["prop_id"]:
            if not selections["update"]:
                raise PreventUpdate

        return comparison_callback(
            compare_on="SOURCE",
            volumemodel=volumemodel,
            selections=selections,
            display_option=display_option,
        )

    @callback(
        Output({"id": get_uuid("main-ens-comp"), "wrapper": "table"}, "children"),
        Input(get_uuid("selections"), "data"),
        Input({"id": get_uuid("main-ens-comp"), "element": "display-option"}, "value"),
        State(get_uuid("page-selected"), "data"),
    )
    def _update_page_ens_comp(
        selections: dict,
        display_option: str,
        page_selected: str,
    ) -> html.Div:
        ctx = callback_context.triggered[0]

        if page_selected != "ens-comp":
            raise PreventUpdate

        selections = selections[page_selected]
        if not "display-option" in ctx["prop_id"]:
            if not selections["update"]:
                raise PreventUpdate

        return comparison_callback(
            compare_on="SENSNAME_CASE"
            if selections["compare_on"] == "Sensitivity"
            else "ENSEMBLE",
            volumemodel=volumemodel,
            selections=selections,
            display_option=display_option,
        )


def comparison_callback(
    compare_on: str,
    volumemodel: InplaceVolumesModel,
    selections: dict,
    display_option: str,
) -> html.Div:
    if selections["value1"] == selections["value2"]:
        return html.Div("Comparison between equal data")

    # Handle None in highlight criteria input
    for key in ["Accept value", "Ignore <"]:
        selections[key] = selections[key] if selections[key] is not None else 0

    groupby = selections["Group by"] if selections["Group by"] is not None else []
    group_on_fluid = "FLUID_ZONE" in groupby
    # for hc responses and bo/bg the data should be grouped
    # on fluid zone to avoid misinterpretations
    if (
        selections["Response"] in volumemodel.hc_responses + ["BO", "BG"]
        and "FLUID_ZONE" not in groupby
    ):
        groupby.append("FLUID_ZONE")

    if display_option == "multi-response table":
        # select max one hc_response for a cleaner table
        responses = [selections["Response"]] + [
            col
            for col in volumemodel.responses
            if col not in volumemodel.hc_responses and col != selections["Response"]
        ]
        df = create_comparison_df(
            volumemodel,
            compare_on=compare_on,
            selections=selections,
            responses=responses,
            abssort_on=f"{selections['Response']} diff (%)",
            groups=groupby,
        )
        if df.empty:
            return html.Div("No data left after filtering")

        return comparison_table_layout(
            table=create_comaprison_table(
                tabletype=display_option,
                df=df,
                groupby=groupby,
                selections=selections,
                compare_on=compare_on,
                volumemodel=volumemodel,
            ),
            table_type=display_option,
            selections=selections,
            filter_info="SOURCE" if compare_on != "SOURCE" else "ENSEMBLE",
        )

    if compare_on == "SOURCE" or "REAL" in groupby:
        diffdf_real = create_comparison_df(
            volumemodel,
            compare_on=compare_on,
            selections=selections,
            responses=[selections["Response"]],
            groups=groupby + (["REAL"] if "REAL" not in groupby else []),
            rename_diff_col=True,
        )

    if "REAL" not in groupby:
        diffdf_group = create_comparison_df(
            volumemodel,
            compare_on=compare_on,
            selections=selections,
            responses=[selections["Response"]],
            groups=groupby,
            rename_diff_col=True,
        )
        if compare_on == "SOURCE" and not diffdf_group.empty:
            # Add column with number of highlighted realizations
            diffdf_group["💡 reals"] = diffdf_group.apply(
                lambda row: find_higlighted_real_count(row, diffdf_real, groupby),
                axis=1,
            )

    df = diffdf_group if "REAL" not in groupby else diffdf_real
    if df.empty:
        return html.Div("No data left after filtering")

    if display_option == "single-response table":
        return comparison_table_layout(
            table=create_comaprison_table(
                tabletype=display_option,
                df=df,
                groupby=groupby,
                selections=selections,
                use_si_format=selections["Response"] in volumemodel.volume_columns,
                compare_on=compare_on,
            ),
            table_type=display_option,
            selections=selections,
            filter_info="SOURCE" if compare_on != "SOURCE" else "ENSEMBLE",
        )

    if display_option == "plots":
        if "|" in selections["value1"]:
            ens1, sens1 = selections["value1"].split("|")
            ens2, sens2 = selections["value2"].split("|")
            value1, value2 = (sens1, sens2) if ens1 == ens2 else (ens1, ens2)
        else:
            value1, value2 = selections["value1"], selections["value2"]

        resp1 = f"{selections['Response']} {value1}"
        resp2 = f"{selections['Response']} {value2}"

        scatter_corr = create_scatterfig(
            df=df, x=resp1, y=resp2, selections=selections, groupby=groupby
        )
        scatter_corr = add_correlation_line(
            figure=scatter_corr, xy_min=df[resp1].min(), xy_max=df[resp1].max()
        )
        scatter_diff_vs_response = create_scatterfig(
            df=df,
            x=resp1,
            y=selections["Diff mode"],
            selections=selections,
            groupby=groupby,
            diff_mode=selections["Diff mode"],
        )
        scatter_diff_vs_real = (
            create_scatterfig(
                df=diffdf_real,
                x="REAL",
                y=selections["Diff mode"],
                selections=selections,
                groupby=groupby,
                diff_mode=selections["Diff mode"],
            )
            if compare_on == "SOURCE"
            else None
        )
        barfig_non_highlighted = create_barfig(
            df=df[df["highlighted"] == "yes"],
            groupby=groupby
            if group_on_fluid
            else [x for x in groupby if x != "FLUID_ZONE"],
            diff_mode=selections["Diff mode"],
            colorcol=resp1,
        )

    return comparison_qc_plots_layout(
        scatter_diff_vs_real,
        scatter_corr,
        scatter_diff_vs_response,
        barfig_non_highlighted,
    )


def create_comparison_df(
    volumemodel: InplaceVolumesModel,
    compare_on: str,
    responses: list,
    selections: dict,
    groups: list,
    abssort_on: str = "diff (%)",
    rename_diff_col: bool = False,
) -> pd.DataFrame:

    resp = selections["Response"]
    adiitional_groups = [
        x for x in ["SOURCE", "ENSEMBLE", "SENSNAME_CASE"] if x in volumemodel.selectors
    ]
    groups = groups + adiitional_groups
    df = volumemodel.get_df(selections["filters"], groups=groups)

    # filter dataframe and set values to compare against
    if not "|" in selections["value1"]:
        value1, value2 = selections["value1"], selections["value2"]
        df = df[df[compare_on].isin([value1, value2])]
    else:
        ens1, sens1 = selections["value1"].split("|")
        ens2, sens2 = selections["value2"].split("|")
        if ens1 == ens2:
            compare_on = "SENSNAME_CASE"
        value1, value2 = (sens1, sens2) if ens1 == ens2 else (ens1, ens2)

        df = df[
            ((df["ENSEMBLE"] == ens1) & (df["SENSNAME_CASE"] == sens1))
            | ((df["ENSEMBLE"] == ens2) & (df["SENSNAME_CASE"] == sens2))
        ]

    # if no data left, or one of the selected SOURCE/ENSEMBLE is not present
    # in the dataframe after filtering, return empty dataframe
    if df.empty or any(x not in df[compare_on].values for x in [value1, value2]):
        return pd.DataFrame()

    df = df.loc[:, groups + responses].pivot_table(
        columns=compare_on,
        index=[x for x in groups if x not in [compare_on, "SENSNAME_CASE"]],
    )
    responses = [x for x in responses if x in df]
    for col in responses:
        df[col, "diff"] = df[col][value2] - df[col][value1]
        df[col, "diff (%)"] = ((df[col][value2] / df[col][value1]) - 1) * 100
        df.loc[df[col]["diff"] == 0, (col, "diff (%)")] = 0
    df = df[responses].replace([np.inf, -np.inf], np.nan).reset_index()

    # remove rows where the selected response is nan
    # can happen for properties where the volume columns are 0
    df = df.loc[~((df[resp][value1].isna()) & (df[resp][value2].isna()))]
    if selections["Remove zeros"]:
        df = df.loc[~((df[resp]["diff"] == 0) & (df[resp][value1] == 0))]

    df["highlighted"] = compute_highlighted_col(df, resp, value1, selections)
    df.columns = df.columns.map(" ".join).str.strip(" ")

    # remove BO∕BG columns if they are nan and drop SOURCE/ENSMEBLE column
    dropcols = [
        x for x in df.columns[df.isna().all()] if x.split(" ")[0] in ["BO", "BG"]
    ] + adiitional_groups
    df = df[[x for x in df.columns if x not in dropcols]]

    if rename_diff_col:
        df = df.rename(columns={f"{resp} diff": "diff", f"{resp} diff (%)": "diff (%)"})
    df = add_fluid_zone_column(df, selections["filters"])
    return df.sort_values(by=[abssort_on], key=abs, ascending=False)


def compute_highlighted_col(
    df: pd.DataFrame, response: str, value1: str, selections: dict
) -> np.ndarray:
    highlight_mask = (df[response][value1] > selections["Ignore <"]) & (
        df[response]["diff (%)"].abs() > selections["Accept value"]
    )
    return np.where(highlight_mask, "yes", "no")


def find_higlighted_real_count(
    row: pd.Series, df_per_real: pd.DataFrame, groups: list
) -> str:
    query = " & ".join([f"{col}=='{row[col]}'" for col in groups])
    result = df_per_real.query(query) if groups else df_per_real
    return str(len(result[result["highlighted"] == "yes"]))


def create_comaprison_table(
    tabletype: str,
    df: pd.DataFrame,
    groupby: list,
    selections: dict,
    compare_on: str,
    use_si_format: Optional[bool] = None,
    volumemodel: Optional[InplaceVolumesModel] = None,
) -> dash_table.DataTable:

    diff_mode_percent = selections["Diff mode"] == "diff (%)"

    if selections["Remove non-highlighted"]:
        df = df.loc[df["highlighted"] == "yes"]
        if df.empty:
            return html.Div(
                [
                    html.Div("All data outside highlight criteria!"),
                    html.Div(
                        "To see the data turn off setting 'Display only highlighted data'"
                    ),
                ]
            )

    if tabletype == "multi-response table":
        diff_cols = [x for x in df.columns if x.endswith(selections["Diff mode"])]
        rename_dict = {x: x.split(" ")[0] for x in diff_cols}
        df = df[groupby + diff_cols + ["highlighted"]].rename(columns=rename_dict)
        df = add_fluid_zone_column(df, selections["filters"])

        columns = create_table_columns(
            columns=move_to_end_of_list("FLUID_ZONE", df.columns),
            text_columns=groupby,
            use_si_format=volumemodel.volume_columns
            if volumemodel is not None and not diff_mode_percent
            else None,
            use_percentage=list(df.columns) if diff_mode_percent else None,
        )
    else:
        columns = create_table_columns(
            columns=move_to_end_of_list("FLUID_ZONE", df.columns),
            text_columns=groupby,
            use_si_format=list(df.columns) if use_si_format else None,
            use_percentage=["diff (%)"],
        )

    return create_data_table(
        selectors=groupby,
        columns=columns,
        height="80vh",
        data=df.to_dict("records"),
        table_id={"table_id": f"{compare_on}-comp-table"},
        style_cell={"textAlign": "center"},
        style_data_conditional=[
            {
                "if": {"filter_query": "{highlighted} = 'yes'"},
                "backgroundColor": "rgb(230, 230, 230)",
                "fontWeight": "bold",
            },
        ],
        style_cell_conditional=[
            {"if": {"column_id": "highlighted"}, "display": "None"}
        ],
    )


def create_scatterfig(
    df: pd.DataFrame,
    x: str,
    y: str,
    selections: dict,
    groupby: list,
    diff_mode: Optional[str] = None,
) -> go.Figure:

    highlight_colors = {"yes": "#FF1243", "no": "#80B7BC"}
    colorby = (
        selections["Color by"]
        if selections["Color by"] == "highlighted"
        else groupby[0]
    )
    df[colorby] = df[colorby].astype(str)

    fig = (
        create_figure(
            plot_type="scatter",
            data_frame=df,
            x=x,
            y=y,
            color_discrete_sequence=px.colors.qualitative.Dark2,
            color_discrete_map=highlight_colors if colorby == "highlighted" else None,
            color=colorby,
            hover_data=groupby,
        )
        .update_traces(marker_size=10)
        .update_layout(margin={"l": 20, "r": 20, "t": 20, "b": 20})
    )
    if len(df) == 1:
        fig.update_xaxes(range=[df[x].mean() * 0.95, df[x].mean() * 1.05])
    if diff_mode is not None:
        fig.update_yaxes(range=find_diff_plot_range(df, diff_mode, selections))
        if diff_mode == "diff (%)" and y == diff_mode:
            fig.add_hline(y=selections["Accept value"], line_dash="dot").add_hline(
                y=-selections["Accept value"], line_dash="dot"
            )
    return fig


def find_diff_plot_range(df: pd.DataFrame, diff_mode: str, selections: dict) -> list:
    """
    Find plot range for diff axis. If axis focus is selected
    the range will center around the non-acepted data points.
    An 10% extension is added to the axis
    """
    if selections["Axis focus"] and "yes" in df["highlighted"].values:
        df = df[df["highlighted"] == "yes"]

    low = min(df[diff_mode].min(), -selections["Accept value"])
    high = max(df[diff_mode].max(), selections["Accept value"])
    extend = (high - low) * 0.1
    return [low - extend, high + extend]


def create_barfig(
    df: pd.DataFrame, groupby: list, diff_mode: str, colorcol: str
) -> Union[None, go.Figure]:
    if df.empty:
        return None
    return (
        create_figure(
            plot_type="bar",
            data_frame=df,
            x=df[groupby].astype(str).agg(" ".join, axis=1) if groupby else ["Total"],
            y=diff_mode,
            color_continuous_scale="teal_r",
            color=df[colorcol],
            hover_data={col: True for col in groupby},
            opacity=1,
        )
        .update_layout(
            margin={"l": 20, "r": 20, "t": 5, "b": 5},
            bargap=0.15,
            paper_bgcolor="rgba(0,0,0,0)",
        )
        .update_xaxes(title_text=None, tickangle=45, ticks="outside")
        .update_yaxes(zeroline=True, zerolinecolor="black")
    )


def add_fluid_zone_column(dframe: pd.DataFrame, filters: dict) -> pd.DataFrame:
    if "FLUID_ZONE" not in dframe and "FLUID_ZONE" in filters:
        dframe["FLUID_ZONE"] = (" + ").join(filters["FLUID_ZONE"])
    return dframe
