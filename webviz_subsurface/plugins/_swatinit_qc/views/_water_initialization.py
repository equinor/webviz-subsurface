from typing import Dict, List, Optional, Tuple, Union

from typing import Any, Callable, List, Optional

import pandas as pd
import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import dash_table, dcc, html

import pandas as pd
from dash import (
    ClientsideFunction,
    Input,
    Output,
    State,
    callback,
    callback_context,
    clientside_callback,
)
from dash.exceptions import PreventUpdate
from webviz_config import WebvizSettings
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_plugin_subclasses import ViewABC

import webviz_subsurface
from webviz_subsurface._components.tornado._tornado_bar_chart import TornadoBarChart
from webviz_subsurface._components.tornado._tornado_data import TornadoData
from webviz_subsurface._components.tornado._tornado_table import TornadoTable

from .._plugin_ids import PlugInIDs


class TabQqPlotLayout(ViewABC):
    class IDs:
        WATERFALL = "waterfall"
        PROP_VS_DEPTH = "prop-vs-depth"

    def __init__(self, datamodel: SwatinitQcDataModel) -> None:
        super().__init__()
        self.datamodel = datamodel

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
