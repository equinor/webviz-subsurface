from typing import Dict, List, TypedDict, Union

import pandas as pd
import webviz_core_components as wcc
from dash import html
from dash.development.base_component import Component
from webviz_config.common_cache import CACHE
from webviz_config.utils import StrEnum


class ColorBy(StrEnum):
    ENSEMBLE = "ENSEMBLE"
    PVTNUM = "PVTNUM"


class LayoutAttributes(TypedDict):
    x_axis_title: str
    y_axis_title: str
    df_column: str
    show_scatter_values: bool
    show_border_values: bool
    show_border_markers: bool


def filter_data_frame(
    data_frame: pd.DataFrame, ensembles: List[str], pvtnums: List[int]
) -> pd.DataFrame:

    data_frame = data_frame.copy()
    data_frame = data_frame.loc[data_frame["ENSEMBLE"].isin(ensembles)]
    data_frame = data_frame.loc[data_frame["PVTNUM"].isin(pvtnums)]
    return data_frame.fillna(0)


def create_hovertext(
    keyword: str,
    constant_group: str,
    group: str,
    color_by: ColorBy,
    realization: str,
    ratio_value: float,
) -> str:
    rs_v = (
        f"Rs = {ratio_value}, "
        if keyword == "PVTO"
        else f"Rv = {ratio_value}"
        if keyword == "PVTG"
        else ""
    )
    pvt_num = group if color_by == ColorBy.PVTNUM else constant_group
    ensemble = group if color_by == ColorBy.ENSEMBLE else constant_group

    return (
        f"{rs_v}Pvtnum: {pvt_num}<br />Realization: {realization}, Ensemble: {ensemble}"
    )


def create_traces(
    data_frame: pd.DataFrame,
    color_by: ColorBy,
    colors: Dict[str, List[str]],
    phase: str,
    column_name: str,
    show_scatter_values: bool,
    show_border_values: bool,
    show_border_markers: bool = False,
) -> List[dict]:
    """Renders line traces for individual realizations"""
    # pylint: disable-msg=too-many-locals
    # pylint: disable=too-many-nested-blocks
    # pylint: disable=too-many-branches

    traces = []
    hovertext: Union[List[str], str]
    border_value_pressure: Dict[str, list] = {}
    border_value_dependent: Dict[str, list] = {}

    dim_column_name = "RATIO"

    if phase == "OIL":
        data_frame = data_frame.loc[
            (data_frame["KEYWORD"] == "PVTO") | (data_frame["KEYWORD"] == "PVDO")
        ]
    elif phase == "GAS":
        data_frame = data_frame.loc[
            (data_frame["KEYWORD"] == "PVTG") | (data_frame["KEYWORD"] == "PVDG")
        ]
        dim_column_name = "PRESSURE"
    else:
        data_frame = data_frame.loc[data_frame["KEYWORD"] == "PVTW"]
        dim_column_name = "PRESSURE"

    data_frame = data_frame.sort_values(
        ["PRESSURE", "VOLUMEFACTOR", "VISCOSITY"],
        ascending=[True, True, True],
    )

    constant_group = (
        data_frame["PVTNUM"].iloc[0]
        if color_by == ColorBy.ENSEMBLE
        else data_frame["ENSEMBLE"].iloc[0]
    )

    for (group, grouped_data_frame) in data_frame.groupby(color_by):
        for set_no, set_value in enumerate(
            grouped_data_frame[dim_column_name].unique()
        ):
            for realization_no, (realization, realization_data_frame) in enumerate(
                grouped_data_frame.groupby("REAL")
            ):
                if group not in border_value_pressure:
                    border_value_pressure[group] = []
                    border_value_dependent[group] = []
                try:
                    border_value_pressure[group].append(
                        realization_data_frame.loc[
                            realization_data_frame[dim_column_name] == set_value
                        ]["PRESSURE"].iloc[0]
                    )
                    if column_name == "VISCOSITY":
                        if phase == "OIL":
                            border_value_dependent[group].append(
                                realization_data_frame[
                                    (
                                        realization_data_frame[dim_column_name]
                                        == set_value
                                    )
                                ]["VISCOSITY"].iloc[0]
                            )
                        else:
                            border_value_dependent[group].append(
                                realization_data_frame[
                                    (
                                        realization_data_frame[dim_column_name]
                                        == set_value
                                    )
                                ]["VISCOSITY"].max()
                            )
                    else:
                        border_value_dependent[group].append(
                            realization_data_frame.loc[
                                realization_data_frame[dim_column_name] == set_value
                            ][column_name].iloc[0]
                        )
                except IndexError as exc:
                    raise IndexError(
                        "This error is most likely due to PVT differences between "
                        "realizations within the same ensemble. This is currently not "
                        "supported."
                    ) from exc

                if show_scatter_values:
                    if phase == "GAS":
                        hovertext = [
                            create_hovertext(
                                realization_data_frame["KEYWORD"].iloc[0],
                                constant_group,
                                group,
                                color_by,
                                realization,
                                realization_data_frame.loc[
                                    (realization_data_frame["PRESSURE"] == y)
                                    & (realization_data_frame[column_name] == x)
                                ]["RATIO"].iloc[0],
                            )
                            for x, y in zip(
                                realization_data_frame.loc[
                                    realization_data_frame["PRESSURE"] == set_value
                                ][column_name],
                                realization_data_frame.loc[
                                    realization_data_frame["PRESSURE"] == set_value
                                ].PRESSURE,
                            )
                        ]
                    else:
                        hovertext = create_hovertext(
                            realization_data_frame["KEYWORD"].iloc[0],
                            constant_group,
                            group,
                            color_by,
                            realization,
                            set_value,
                        )

                    traces.extend(
                        [
                            {
                                "type": "scatter",
                                "x": realization_data_frame.loc[
                                    realization_data_frame[dim_column_name] == set_value
                                ]["PRESSURE"],
                                "y": realization_data_frame.loc[
                                    realization_data_frame[dim_column_name] == set_value
                                ][column_name],
                                "xaxis": "x",
                                "yaxis": "y",
                                "hovertext": hovertext,
                                "name": group,
                                "legendgroup": group,
                                "marker": {
                                    "color": colors.get(
                                        group, colors[list(colors.keys())[-1]]
                                    )
                                },
                                "showlegend": realization_no == 0 and set_no == 0,
                            }
                        ]
                    )
    if show_border_values:
        for group, group_border_value_pressure in border_value_pressure.items():
            traces.extend(
                [
                    {
                        "type": "scatter",
                        "mode": ("lines+markers" if show_border_markers else "lines"),
                        "x": group_border_value_pressure,
                        "y": border_value_dependent[group],
                        "xaxis": "x",
                        "yaxis": "y",
                        "legendgroup": group,
                        "line": {
                            "width": 1,
                            "color": colors.get(group, colors[list(colors.keys())[-1]]),
                        },
                        "showlegend": not show_scatter_values,
                    }
                ]
            )
    return traces


def create_graph(
    data_frame: pd.DataFrame,
    color_by: ColorBy,
    colors: Dict[str, List[str]],
    phase: str,
    plot: str,
    plot_title: str,
    theme: dict,
    graph_height: float,
) -> Component:
    layout_attributes: Dict[str, LayoutAttributes] = (
        {
            "fvf": {
                "x_axis_title": rf"Pressure [{data_frame['PRESSURE_UNIT'].iloc[0]}]",
                "y_axis_title": rf"[{data_frame['VOLUMEFACTOR_UNIT'].iloc[0]}]",
                "df_column": "VOLUMEFACTOR",
                "show_scatter_values": True,
                "show_border_values": True,
                "show_border_markers": False,
            },
            "viscosity": {
                "x_axis_title": rf"Pressure [{data_frame['PRESSURE_UNIT'].iloc[0]}]",
                "y_axis_title": rf"[{data_frame['VISCOSITY_UNIT'].iloc[0]}]",
                "df_column": "VISCOSITY",
                "show_scatter_values": True,
                "show_border_values": True,
                "show_border_markers": False,
            },
            "density": {
                "x_axis_title": rf"Pressure [{data_frame['PRESSURE_UNIT'].iloc[0]}]",
                "y_axis_title": rf"[{data_frame['DENSITY_UNIT'].iloc[0]}]",
                "df_column": "DENSITY",
                "show_scatter_values": True,
                "show_border_values": True,
                "show_border_markers": False,
            },
            "ratio": {
                "x_axis_title": rf"Pressure [{data_frame['PRESSURE_UNIT'].iloc[0]}]",
                "y_axis_title": rf"[{data_frame['RATIO_UNIT'].iloc[0]}]",
                "df_column": "DENSITY",
                "show_scatter_values": False,
                "show_border_values": True,
                "show_border_markers": True,
            },
        }
        if not data_frame.empty
        else {}
    )

    return wcc.FlexBox(
        style={
            "height": f"{graph_height}vh",
            "min-width": "20vh",
            "text-align": "center",
            "padding": "2%",
            # "flex": "1 1 46%",
        },
        children=(
            [
                html.Span(plot_title, style={"font-weight": "bold"}),
                wcc.Graph(
                    style={"height": f"{graph_height}vh"},
                    figure={
                        "layout": plot_layout(
                            color_by,
                            theme,
                            layout_attributes[plot]["x_axis_title"],
                            layout_attributes[plot]["y_axis_title"],
                        ),
                        "data": create_traces(
                            data_frame,
                            color_by,
                            colors,
                            phase,
                            layout_attributes[plot]["df_column"],
                            layout_attributes[plot]["show_scatter_values"],
                            layout_attributes[plot]["show_border_values"],
                            layout_attributes[plot]["show_border_markers"],
                        ),
                    }
                    if not data_frame.empty and plot in layout_attributes
                    else {},
                ),
            ]
        ),
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_layout(
    color_by: ColorBy,
    theme: dict,
    x_unit: str,
    y_unit: str,
) -> dict:
    layout = {}
    layout.update(theme)
    layout["legend"] = {"title": {"text": color_by.lower().capitalize()}}
    layout.update(
        {
            "xaxis": {
                "automargin": True,
                "zeroline": False,
                "anchor": "y",
                "domain": [0.0, 1.0],
                "title": {
                    "text": x_unit,
                    "standoff": 15,
                },
                "showticklabels": True,
                "showgrid": True,
            },
            "yaxis": {
                "automargin": True,
                "ticks": "",
                "zeroline": False,
                "anchor": "x",
                "domain": [0.0, 1.0],
                "title": {
                    "text": y_unit,
                },
                "type": "linear",
                "showgrid": True,
            },
            "margin": {"t": 20, "b": 0},
            "plot_bgcolor": "rgba(0,0,0,0)",
            "hovermode": "closest",
        }
    )
    return layout
