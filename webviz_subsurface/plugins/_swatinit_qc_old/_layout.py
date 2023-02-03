from enum import Enum, auto
from typing import Any, Callable, List, Optional

import pandas as pd
import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import dash_table, dcc, html

from ._business_logic import SwatinitQcDataModel
from ._markdown import (
    check_swatinit_description,
    pc_columns_description,
    qc_flag_description,
)


# pylint: disable = too-few-public-methods
class LayoutElements(str, Enum):
    PLOT_WRAPPER = auto()
    PLOT_SELECTOR = auto()
    TABLE_WRAPPER = auto()
    PLOT_EQLNUM_SELECTOR = auto()
    TABLE_EQLNUM_SELECTOR = auto()
    FILTERS_CONTINOUS = auto()
    FILTERS_CONTINOUS_MAX_PC = auto()
    FILTERS_DISCRETE = auto()
    COLOR_BY = auto()
    MAX_POINTS = auto()
    HIGHLIGHT_ABOVE = auto()
    GROUPBY_EQLNUM = auto()
    SELECTED_TAB = auto()
    MAP_FIGURE = auto()
    MAIN_FIGURE = auto()


class LayoutStyle:
    MAIN_HEIGHT = "87vh"
    HEADER = {
        "font-size": "15px",
        "color": "black",
        "text-transform": "uppercase",
        "border-color": "black",
    }
    TABLE_HEADER = {"fontWeight": "bold"}
    TABLE_STYLE = {"max-height": MAIN_HEIGHT, "overflowY": "auto"}
    TABLE_CELL_WIDTH = 95
    TABLE_CELL_HEIGHT = "10px"
    TABLE_HIGHLIGHT = {"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"}
    TABLE_CSS = [
        {
            "selector": ".dash-spreadsheet tr",
            "rule": f"height: {TABLE_CELL_HEIGHT};",
        },
    ]


class Tabs:
    QC_PLOTS = "Water Initializaion QC plots"
    MAX_PC_SCALING = "Capillary pressure scaling"
    OVERVIEW = "Overview and Information"


def plugin_main_layout(get_uuid: Callable, datamodel: SwatinitQcDataModel) -> wcc.Tabs:

    return wcc.Tabs(
        id=get_uuid(LayoutElements.SELECTED_TAB),
        value=Tabs.OVERVIEW,
        children=[
            TabLayout(
                tab_label=Tabs.OVERVIEW,
                selections_layout=None,
                main_layout=OverviewTabLayout(get_uuid, datamodel).main_layout,
            ),
            TabLayout(
                tab_label=Tabs.QC_PLOTS,
                selections_layout=TabQqPlotLayout(
                    get_uuid, datamodel
                ).selections_layout,
                main_layout=html.Div(id=get_uuid(LayoutElements.PLOT_WRAPPER)),
            ),
            TabLayout(
                tab_label=Tabs.MAX_PC_SCALING,
                selections_layout=TabMaxPcInfoLayout(
                    get_uuid, datamodel
                ).selections_layout,
                main_layout=html.Div(id=get_uuid(LayoutElements.TABLE_WRAPPER)),
            ),
        ],
    )


class TabLayout(wcc.Tab):
    def __init__(
        self, tab_label: str, selections_layout: Optional[list], main_layout: list
    ) -> None:
        flex_children = []
        if selections_layout is not None:
            flex_children.append(
                wcc.Frame(
                    style={
                        "flex": 1,
                        "height": LayoutStyle.MAIN_HEIGHT,
                        "overflowY": "auto",
                    },
                    children=selections_layout,
                )
            )
        flex_children.append(
            wcc.Frame(
                style={"flex": 5, "height": LayoutStyle.MAIN_HEIGHT},
                color="white",
                highlight=False,
                children=main_layout,
            )
        )
        super().__init__(
            label=tab_label,
            value=tab_label,
            children=wcc.FlexBox(children=flex_children),
        )


class FullScreen(wcc.WebvizPluginPlaceholder):
    def __init__(self, children: List[Any]) -> None:
        super().__init__(buttons=["expand"], children=children)


class TabQqPlotLayout:
    class MainPlots(str, Enum):
        WATERFALL = auto()
        PROP_VS_DEPTH = auto()

    def __init__(self, get_uuid: Callable, datamodel: SwatinitQcDataModel) -> None:
        self.datamodel = datamodel
        self.get_uuid = get_uuid

    def main_layout(
        self,
        main_figure: go.Figure,
        map_figure: go.Figure,
        qc_volumes: dict,
    ) -> wcc.FlexBox:
        return wcc.FlexBox(
            children=[
                wcc.FlexColumn(
                    flex=4,
                    children=wcc.Graph(
                        style={"height": "85vh"},
                        id=self.get_uuid(LayoutElements.MAIN_FIGURE),
                        figure=main_figure,
                    ),
                ),
                wcc.FlexColumn(
                    flex=1,
                    children=[
                        FullScreen(
                            wcc.Graph(
                                responsive=True,
                                style={"height": "100%", "min-height": "45vh"},
                                id=self.get_uuid(LayoutElements.MAP_FIGURE),
                                figure=map_figure,
                            )
                        ),
                        self.info_box(qc_volumes, height="35vh"),
                    ],
                ),
            ]
        )

    @property
    def selections_layout(self) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    wcc.Dropdown(
                        label="Select QC-visualization:",
                        id=self.get_uuid(LayoutElements.PLOT_SELECTOR),
                        options=[
                            {
                                "label": "Waterfall plot for water vol changes",
                                "value": self.MainPlots.WATERFALL,
                            },
                            {
                                "label": "Reservoir properties vs Depth",
                                "value": self.MainPlots.PROP_VS_DEPTH,
                            },
                        ],
                        value=self.MainPlots.PROP_VS_DEPTH,
                        clearable=False,
                    ),
                    style={"margin-bottom": "15px"},
                ),
                wcc.Selectors(
                    label="Selections",
                    children=[
                        wcc.SelectWithLabel(
                            label="EQLNUM",
                            id=self.get_uuid(LayoutElements.PLOT_EQLNUM_SELECTOR),
                            options=[
                                {"label": ens, "value": ens}
                                for ens in self.datamodel.eqlnums
                            ],
                            value=self.datamodel.eqlnums[:1],
                            size=min(8, len(self.datamodel.eqlnums)),
                            multi=True,
                        ),
                        wcc.Dropdown(
                            label="Color by",
                            id=self.get_uuid(LayoutElements.COLOR_BY),
                            options=[
                                {"label": ens, "value": ens}
                                for ens in self.datamodel.color_by_selectors
                            ],
                            value="QC_FLAG",
                            clearable=False,
                        ),
                        wcc.Label("Max number of points:"),
                        dcc.Input(
                            id=self.get_uuid(LayoutElements.MAX_POINTS),
                            type="number",
                            value=5000,
                        ),
                    ],
                ),
                wcc.Selectors(
                    label="Filters",
                    children=[
                        wcc.SelectWithLabel(
                            label="QC_FLAG",
                            id={
                                "id": self.get_uuid(LayoutElements.FILTERS_DISCRETE),
                                "col": "QC_FLAG",
                            },
                            options=[
                                {"label": ens, "value": ens}
                                for ens in self.datamodel.qc_flag
                            ],
                            value=self.datamodel.qc_flag,
                            size=min(8, len(self.datamodel.qc_flag)),
                        ),
                        wcc.SelectWithLabel(
                            label="SATNUM",
                            id={
                                "id": self.get_uuid(LayoutElements.FILTERS_DISCRETE),
                                "col": "SATNUM",
                            },
                            options=[
                                {"label": ens, "value": ens}
                                for ens in self.datamodel.satnums
                            ],
                            value=self.datamodel.satnums,
                            size=min(8, len(self.datamodel.satnums)),
                        ),
                        range_filters(
                            self.get_uuid(LayoutElements.FILTERS_CONTINOUS),
                            self.datamodel,
                        ),
                    ],
                ),
            ],
        )

    @staticmethod
    def info_box(qc_vols: dict, height: str) -> html.Div:
        return html.Div(
            [
                wcc.Header("Information about selection", style=LayoutStyle.HEADER),
                html.Div(
                    "EQLNUMS:", style={"font-weight": "bold", "font-size": "15px"}
                ),
                html.Div(", ".join([str(x) for x in qc_vols["EQLNUMS"]])),
                html.Div(
                    "SATNUMS:", style={"font-weight": "bold", "font-size": "15px"}
                ),
                html.Div(", ".join([str(x) for x in qc_vols["SATNUMS"]])),
                html.Div(
                    html.Span("Reservoir Volume Difference:"),
                    style={"font-weight": "bold", "margin-top": "10px"},
                ),
                html.Div(
                    children=[
                        html.Div(line)
                        for line in [
                            f"Water Volume Diff: {qc_vols['WVOL_DIFF']/(10**6):.2f} Mrm3",
                            f"Water Volume Diff (%): {qc_vols['WVOL_DIFF_PERCENT']:.2f}",
                            f"HC Volume Diff (%): {qc_vols['HCVOL_DIFF_PERCENT']:.2f}",
                        ]
                    ],
                ),
            ],
            style={"height": height, "padding": "10px"},
        )


class TabMaxPcInfoLayout:
    def __init__(self, get_uuid: Callable, datamodel: SwatinitQcDataModel) -> None:
        self.datamodel = datamodel
        self.get_uuid = get_uuid

    def main_layout(
        self, dframe: pd.DataFrame, selectors: list, map_figure: go.Figure
    ) -> html.Div:
        return html.Div(
            children=[
                wcc.Header(
                    "Maximum capillary pressure scaling", style=LayoutStyle.HEADER
                ),
                wcc.FlexBox(
                    style={"margin-top": "10px", "height": "40vh"},
                    children=[
                        wcc.FlexColumn(
                            dcc.Markdown(pc_columns_description()),
                            flex=7,
                            style={"margin-right": "40px"},
                        ),
                        wcc.FlexColumn(
                            FullScreen(
                                wcc.Graph(
                                    style={"height": "100%", "min-height": "35vh"},
                                    figure=map_figure,
                                )
                            ),
                            flex=3,
                        ),
                    ],
                ),
                self.create_max_pc_table(dframe, text_columns=selectors),
            ]
        )

    @property
    def selections_layout(self) -> html.Div:
        return html.Div(
            children=[
                wcc.Selectors(
                    label="Selections",
                    children=[
                        html.Div(
                            wcc.RadioItems(
                                label="Split table by:",
                                id=self.get_uuid(LayoutElements.GROUPBY_EQLNUM),
                                options=[
                                    {"label": "SATNUM", "value": "SATNUM"},
                                    {"label": "SATNUM and EQLNUM", "value": "both"},
                                ],
                                value="SATNUM",
                            ),
                            style={"margin-bottom": "10px"},
                        ),
                        self.scaling_threshold,
                    ],
                ),
                wcc.Selectors(
                    label="Filters",
                    children=[
                        wcc.SelectWithLabel(
                            label="EQLNUM",
                            id=self.get_uuid(LayoutElements.TABLE_EQLNUM_SELECTOR),
                            options=[
                                {"label": ens, "value": ens}
                                for ens in self.datamodel.eqlnums
                            ],
                            value=self.datamodel.eqlnums,
                            size=min(8, len(self.datamodel.eqlnums)),
                            multi=True,
                        ),
                        range_filters(
                            self.get_uuid(LayoutElements.FILTERS_CONTINOUS_MAX_PC),
                            self.datamodel,
                        ),
                    ],
                ),
            ]
        )

    def create_max_pc_table(
        self, dframe: pd.DataFrame, text_columns: list
    ) -> dash_table:
        return DashTable(
            data=dframe.to_dict("records"),
            columns=[
                {
                    "name": i,
                    "id": i,
                    "type": "numeric" if i not in text_columns else "text",
                    "format": {"specifier": ".4~r"} if i not in text_columns else {},
                }
                for i in dframe.columns
            ],
            height="48vh",
            sort_action="native",
            fixed_rows={"headers": True},
            style_cell={
                "minWidth": LayoutStyle.TABLE_CELL_WIDTH,
                "maxWidth": LayoutStyle.TABLE_CELL_WIDTH,
                "width": LayoutStyle.TABLE_CELL_WIDTH,
            },
            style_data_conditional=[
                {
                    "if": {
                        "filter_query": f"{{{self.datamodel.COLNAME_THRESHOLD}}} > 0",
                    },
                    **LayoutStyle.TABLE_HIGHLIGHT,
                },
            ],
        )

    @property
    def scaling_threshold(self) -> html.Div:
        return html.Div(
            style={"margin-top": "10px"},
            children=[
                wcc.Label("Maximum PC_SCALING threshold"),
                html.Div(
                    dcc.Input(
                        id=self.get_uuid(LayoutElements.HIGHLIGHT_ABOVE),
                        type="number",
                        persistence=True,
                        persistence_type="session",
                    )
                ),
            ],
        )


class OverviewTabLayout:
    def __init__(self, get_uuid: Callable, datamodel: SwatinitQcDataModel):
        self.datamodel = datamodel
        self.get_uuid = get_uuid

    @property
    def main_layout(self) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    style={"height": "40vh", "overflow-y": "auto"},
                    children=[
                        wcc.FlexBox(
                            children=[
                                wcc.FlexColumn(
                                    [
                                        self.overview_report_volume_changes,
                                    ],
                                    flex=7,
                                    style={"margin-right": "20px"},
                                ),
                                wcc.FlexColumn(self.dataset_info, flex=3),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    style={"margin-top": "20px"},
                    children=[
                        wcc.Header("QC_FLAG descriptions", style=LayoutStyle.HEADER),
                        dcc.Markdown(qc_flag_description()),
                    ],
                ),
            ]
        )

    @property
    def information_dialog(self) -> html.Div:
        title = "Plugin and 'check_swatinit' information"
        return html.Div(
            style={"margin-bottom": "30px"},
            children=[
                html.Button(
                    title,
                    style={"width": "100%", "background-color": "white"},
                    id=self.get_uuid("info-button"),
                ),
                wcc.Dialog(
                    title=title,
                    id=self.get_uuid("info-dialog"),
                    max_width="md",
                    open=False,
                    children=dcc.Markdown(check_swatinit_description()),
                ),
            ],
        )

    @property
    def dataset_info(self) -> html.Div:
        max_pc, min_pc = self.datamodel.pc_scaling_min_max
        wvol, hcvol = self.datamodel.vol_diff_total

        number_style = {
            "font-weight": "bold",
            "font-size": "17px",
            "margin-left": "20px",
        }
        data = [
            ("HC Volume difference:", f"{hcvol:.2f} %"),
            ("Water Volume difference:", f"{wvol:.2f} %"),
            ("Maximum Capillary Pressure scaling:", f"{max_pc:.1f}"),
            ("Minimum Capillary Pressure scaling:", f"{min_pc:.3g}"),
        ]

        return wcc.Frame(
            style={"height": "90%"},
            children=[
                wcc.Header("Information", style=LayoutStyle.HEADER),
                self.information_dialog,
                wcc.Header("Key numbers", style=LayoutStyle.HEADER),
                html.Div(
                    [
                        html.Div([text, html.Span(num, style=number_style)])
                        for text, num in data
                    ]
                ),
            ],
        )

    @property
    def overview_report_volume_changes(self) -> html.Div:
        data, columns = self.datamodel.table_data_qc_vol_overview()
        label = (
            "Table showing volume changes from SWATINIT to SWAT at Reservoir conditions"
        )
        return html.Div(
            children=[
                html.Div(
                    html.Label(label, className="webviz-underlined-label"),
                    style={"margin-bottom": "20px"},
                ),
                DashTable(
                    data=data,
                    columns=columns,
                    style_data_conditional=[
                        {
                            "if": {"row_index": [0, len(data) - 1]},
                            **LayoutStyle.TABLE_HIGHLIGHT,
                        },
                    ],
                ),
            ],
        )


def range_filters(uuid: str, datamodel: SwatinitQcDataModel) -> html.Div:
    dframe = datamodel.dframe
    filters = []
    for col in datamodel.filters_continuous:
        min_val, max_val = dframe[col].min(), dframe[col].max()
        filters.append(
            wcc.RangeSlider(
                label="Depth range" if col == "Z" else col,
                id={"id": uuid, "col": col},
                min=min_val,
                max=max_val,
                value=[min_val, max_val],
                marks={str(val): {"label": f"{val:.2f}"} for val in [min_val, max_val]},
                tooltip={"always_visible": False},
            )
        )
    return html.Div(filters)


class DashTable(dash_table.DataTable):
    def __init__(
        self, data: List[dict], columns: List[dict], height: str = "none", **kwargs: Any
    ) -> None:
        super().__init__(
            data=data,
            columns=columns,
            style_table={"height": height, **LayoutStyle.TABLE_STYLE},
            style_as_list_view=True,
            css=LayoutStyle.TABLE_CSS,
            style_header=LayoutStyle.TABLE_HEADER,
            **kwargs,
        )
