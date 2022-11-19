from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import webviz_core_components as wcc
from dash import Dash, Input, Output, dash_table, dcc, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore


class AssistedHistoryMatchingAnalysis(WebvizPluginABC):
    """Visualize parameter distribution change prior to posterior \
    per observation group in an assisted history matching process.
    This is done by using a \
    [KS (Kolmogorov Smirnov) test](https://en.wikipedia.org/wiki/Kolmogorov%E2%80%93Smirnov_test) \
    matrix, and scatter plot/map for any given pair of parameter/observation. \
    KS values are between 0 and 1. \
    The closer to zero the KS value is, the smaller the change in parameter distribution \
    between prior/posterior and vice-versa. \
    The top 10 biggest parameters change are also shown in a table.

    ---

    * **`input_dir`:** Path to the directory where the `csv` files created \
        by the `AHM_ANALYSIS` ERT postprocess workflow are stored
    * **`ks_filter`:** optional argument to filter output to the data table based on ks value, \
        only values above entered value will be displayed in the data table. \
        This can be used if needed to speed-up vizualization of cases with \
        high number of parameters and/or observations group. Default value is 0.0.

    ---


    ?> The input_dir  \
    is where the results (csv files) from \
    the ERT `AHM_ANALYSIS` worflow are stored.
    ?> The ks_filter value should typically be between 0 and 0.5.

    """

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        input_dir: Path,
        ks_filter: float = 0.0,
    ):

        super().__init__()

        self.input_dir = input_dir
        self.theme = webviz_settings.theme
        self.ks_filter = ks_filter

        self.set_callbacks(app)

    @property
    def layout(self):
        return html.Div(
            id=self.uuid("main-div"),
            children=[
                wcc.FlexBox(
                    children=[
                        wcc.Frame(
                            style={"flex": 1, "style": "45vh"},
                            children=[
                                wcc.Selectors(
                                    label="Filters",
                                    children=[
                                        wcc.Label(
                                            children="Filter observations:",
                                            style={"display": "block"},
                                        ),
                                        dcc.Input(
                                            id=self.uuid("filter1_id"),
                                            value="",
                                            type="text",
                                            debounce=True,
                                        ),
                                        wcc.Label(
                                            children="Filter parameters:",
                                            style={"display": "block"},
                                        ),
                                        dcc.Input(
                                            id=self.uuid("filter2_id"),
                                            value="",
                                            type="text",
                                            debounce=True,
                                        ),
                                    ],
                                ),
                                wcc.Selectors(
                                    label="Selected output:",
                                    children=wcc.RadioItems(
                                        id=self.uuid("choice_id"),
                                        options=[
                                            {
                                                "label": "One by one observation",
                                                "value": "ONE",
                                            },
                                            {
                                                "label": "All minus one observation",
                                                "value": "ALL",
                                            },
                                        ],
                                        value="ONE",
                                    ),
                                ),
                                wcc.Selectors(
                                    label="Parameter distribution:",
                                    children=dcc.Checklist(
                                        id=self.uuid("choice_hist_id"),
                                        options=[
                                            {
                                                "label": "Transformed dist. (if available)",
                                                "value": "TRANS",
                                            },
                                        ],
                                        value=[],
                                    ),
                                ),
                            ],
                        ),
                        wcc.Frame(
                            color="white",
                            highlight=False,
                            style={"flex": 3},
                            children=[
                                html.Div(
                                    id=self.uuid("output_graph"),
                                ),
                            ],
                        ),
                        wcc.Frame(
                            color="white",
                            highlight=False,
                            style={"flex": 3},
                            children=[
                                html.Div(
                                    id=self.uuid("click_data"),
                                ),
                            ],
                        ),
                    ]
                ),
                html.Div(
                    children=[
                        html.H4(
                            children="Table of ten highest parameters change/update Ks",
                        ),
                        html.Div(
                            id=self.uuid("generate_table"),
                        ),
                    ]
                ),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("output_graph"), component_property="children"),
            Input(self.uuid("filter1_id"), component_property="value"),
            Input(self.uuid("filter2_id"), component_property="value"),
            Input(self.uuid("choice_id"), component_property="value"),
        )
        def _update_graph(input_filter_obs, input_filter_param, choiceplot):
            """Renders KS matrix (how much a parameter is changed from prior to posterior"""
            active_info = read_csv(
                get_path(self.input_dir / "active_obs_info.csv"), index_col=0
            )
            joint_ks = read_csv(
                get_path(self.input_dir / "ks.csv"), index_col=0
            ).replace(np.nan, 0.0)
            input_filter_obs = _set_inputfilter(input_filter_obs)
            input_filter_param = _set_inputfilter(input_filter_param)

            listtoplot = _get_listtoplot(joint_ks, choiceplot)
            joint_ks_sorted = joint_ks.filter(items=listtoplot).sort_index(axis=1)
            xx_data = list(
                joint_ks_sorted.filter(like=input_filter_obs, axis=1).columns
            )
            yy_data = list(
                joint_ks_sorted.filter(like=input_filter_param, axis=0).index
            )
            zz_data = _get_zzdata(joint_ks_sorted, yy_data, xx_data, active_info)

            if not xx_data or not yy_data:
                raise PreventUpdate

            yall_obs_data = list(
                joint_ks_sorted.filter(like=input_filter_param, axis=0).index
            )
            zall_obs_data = joint_ks.loc[yall_obs_data, ["All_obs"]].to_numpy()

            return wcc.Graph(
                id=self.uuid("heatmap_id"),
                figure={
                    "data": [
                        go.Heatmap(
                            x=xx_data,
                            y=yy_data,
                            z=zz_data,
                            type="heatmap",
                            colorscale="YlGnBu",
                            zmin=0,
                            zmax=1,
                            hoverinfo="text",
                            text=_hovertext_list(
                                xx_data, yy_data, zz_data, active_info
                            ),
                        ),
                        go.Heatmap(
                            x=["All_obs"],
                            y=yall_obs_data,
                            z=zall_obs_data,
                            type="heatmap",
                            colorscale="YlGnBu",
                            zmin=0,
                            zmax=1,
                            hoverinfo="text",
                            text=_hovertext_list(
                                ["All_obs"], yall_obs_data, zall_obs_data, active_info
                            ),
                            xaxis="x2",
                        ),
                    ],
                    "layout": self.theme.create_themed_layout(
                        {
                            "title": "KS Matrix (degree of parameter change prior to posterior)",
                            "xaxis": {
                                "title": "Observations",
                                "ticks": "",
                                "domain": [0.0, 0.9],
                                "showticklabels": True,
                                "tickangle": 30,
                                "automargin": True,
                            },
                            "yaxis": {
                                "title": "Parameters",
                                "ticks": "",
                                "showticklabels": True,
                                "tickangle": -30,
                                "automargin": True,
                            },
                            "xaxis2": {"ticks": "", "domain": [0.95, 1.0]},
                            "plot_bgcolor": "grey",
                        }
                    ),
                },
                style={"height": "45vh"},
                clickData={"points": [{"x": xx_data[0], "y": yy_data[0]}]},
            )

        @app.callback(
            Output(self.uuid("click_data"), component_property="children"),
            Input(self.uuid("heatmap_id"), component_property="clickData"),
            Input(self.uuid("choice_hist_id"), component_property="value"),
            prevent_initial_call=True,
        )
        def _display_click_data(celldata, hist_display):
            """render a histogram of parameters distribution prior/posterior or
            an average delta map prior-posterior."""
            obs = celldata["points"][0]["x"]
            param = celldata["points"][0]["y"]
            active_info = read_csv(
                get_path(self.input_dir / "active_obs_info.csv"), index_col=0
            )
            if "FIELD" in param:
                fieldparam = param.replace("FIELD_", "")
                mygrid_ok_short = read_csv(
                    get_path(
                        Path(str(self.input_dir).replace("scalar_", "field_"))
                        / f"delta_field{fieldparam}.csv"
                    )
                )
                maxinput = mygrid_ok_short.filter(like="Mean_").max(axis=1)
                deltadata = "Mean_D_" + obs
                return wcc.Graph(
                    id="2Dmap_avgdelta",
                    figure=px.scatter(
                        mygrid_ok_short,
                        x="X_UTME",
                        y="Y_UTMN",
                        color=deltadata,
                        range_color=[0, maxinput.max()],
                        color_continuous_scale="Rainbow",
                        opacity=0.9,
                        title=f"Mean_delta_posterior-prior {obs}, {param}",
                        hover_data=[
                            "X_UTME",
                            "Y_UTMN",
                            "Z_TVDSS",
                            "IX",
                            "JY",
                            deltadata,
                        ],
                    ),
                )
            post_df = read_csv(get_path(self.input_dir / f"{obs}.csv"))
            prior_df = read_csv(get_path(self.input_dir / "prior.csv"))
            if "TRANS" in hist_display:
                paraml = [ele for ele in prior_df.keys() if f"_{param}" in ele]
                if paraml != []:
                    param = paraml[0]
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=prior_df[param], name="prior", nbinsx=10))
            fig.add_trace(go.Histogram(x=post_df[param], name="update", nbinsx=10))
            fig.update_layout(
                self.theme.create_themed_layout(
                    {
                        "title": (
                            "Parameter distribution for observation "
                            f"{obs} ({active_info.at['ratio', obs]})"
                        ),
                        "bargap": 0.2,
                        "bargroupgap": 0.1,
                        "xaxis": {"title": param},
                    }
                )
            )

            return wcc.Graph(id="lineplots", style={"height": "45vh"}, figure=fig)

        @app.callback(
            Output(self.uuid("generate_table"), component_property="children"),
            Input(self.uuid("choice_id"), component_property="value"),
        )
        def _generatetable(choiceplot, max_rows=10):
            """Generate output table of data in KS matrix plot"""
            misfit_info = read_csv(
                get_path(self.input_dir / "misfit_obs_info.csv"), index_col=0
            )
            list_ok = list(misfit_info.filter(like="All_obs", axis=1).columns)
            listtoplot = [ele for ele in misfit_info.columns if ele not in list_ok]
            if choiceplot == "ALL":
                listtoplot = list_ok
            active_info = read_csv(
                get_path(self.input_dir / "active_obs_info.csv"),
                index_col=0,
            )

            joint_ks = read_csv(
                get_path(self.input_dir / "ks.csv"),
                index_col=0,
            ).replace(np.nan, 0.0)
            ks_filtered = _get_ks_filtered(
                listtoplot, active_info, misfit_info, joint_ks, self.ks_filter
            )

            ks_filtered = ks_filtered.sort_values(by="Ks_value", ascending=False)

            return dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in ks_filtered.columns],
                editable=True,
                style_data_conditional=[
                    {
                        "if": {
                            "filter_query": "{Active Obs}=0",
                            "column_id": "Active Obs",
                        },
                        "backgroundColor": "grey",
                        "color": "white",
                    },
                ],
                data=ks_filtered.to_dict("records"),
                sort_action="native",
                filter_action="native",
                page_action="native",
                page_current=0,
                page_size=max_rows,
            )

    @property
    def tour_steps(self) -> List[Dict[str, str]]:
        return [
            {
                "id": self.uuid("main-div"),
                "content": (
                    "This dashboard helps to analyze the update step performed "
                    "during assisted history match using the ensemble smoother method. "
                    "This can give insight into which parameters are updated due to a "
                    "specific observation type, and also which observations are causing an "
                    "update in a specific parameter. KS refers to "
                    "Kolmogorov–Smirnov."
                ),
            },
            {
                "id": self.uuid("filter1_id"),
                "content": (
                    "By entering text in this field, you will be able to filter the "
                    "observations (e.g. entering 'WBP' will include only observations "
                    "containing that string)."
                ),
            },
            {
                "id": self.uuid("filter2_id"),
                "content": (
                    "Give option to filter on parameters, similarly to how it is done "
                    "for observations."
                ),
            },
            {
                "id": self.uuid("choice_hist_id"),
                "content": (
                    "Give option for plotting parameter prior/posterior distribution. "
                    "Some parameters may have transformed equivalent like LOG10"
                ),
            },
            {
                "id": self.uuid("output_graph"),
                "content": "Renders KS matrix value between 0 and 1",
            },
            {
                "id": self.uuid("click_data"),
                "content": (
                    "Render a histogram of parameters distribution prior/posterior "
                    "or an average delta map prior-posterior"
                ),
            },
            {
                "id": self.uuid("generate_table"),
                "content": "Generate output table of data in KS matrix plot",
            },
        ]

    def add_webvizstore(self):
        scalar_csv_files = list(self.input_dir.glob("*"))
        field_csv_files = list(
            Path(str(self.input_dir).replace("scalar_", "field_")).glob("*")
        )
        return [
            (
                get_path,
                [{"path": path} for path in scalar_csv_files + field_csv_files],
            )
        ]


def _hovertext_list(xx_data, yy_data, zz_data, active_info):
    """Define hovertext info"""
    hovertext = []
    for parami, paramy in enumerate(yy_data):
        hovertext.append([])
        for obsi, obsx in enumerate(xx_data):
            hovertext[-1].append(
                f"Obs ({active_info.at['ratio', obsx]}): "
                f"{obsx}<br>Param: {paramy}<br>Ks: {zz_data[parami][obsi]}"
            )
    return hovertext


def _get_ks_filtered(listtoplot, active_info, misfit_info, joint_ks, filter_value):
    """Generate filtered KS dataframe"""
    ks_filtered = pd.DataFrame()
    for obs in listtoplot:
        tmp_ks_filter = pd.DataFrame()
        tmp_ks_filter["Ks_value"] = joint_ks[joint_ks[obs] >= filter_value][obs]
        tmp_ks_filter["Observation"] = obs
        tmp_ks_filter["Parameter"] = list(joint_ks[joint_ks[obs] >= filter_value].index)
        tmp_ks_filter["Active Obs"] = active_info[obs].to_numpy()[0]
        tmp_ks_filter["Avg Obs misfit"] = misfit_info[obs].to_numpy()[0]
        tmp_ks_filter.reset_index(
            level=None, drop=True, inplace=True, col_level=0, col_fill=""
        )
        ks_filtered = pd.concat([ks_filtered, tmp_ks_filter], ignore_index=True)
    return ks_filtered


def _get_listtoplot(joint_ks, choiceplot):
    """Generate correct observations to plot based on choice made"""
    list_ok = list(joint_ks.filter(like="All_obs", axis=1).columns)
    listtoplot = [ele for ele in joint_ks.columns if ele not in list_ok]
    if choiceplot == "ALL":
        list_ok.remove("All_obs")
        listtoplot = list_ok
    return listtoplot


def _get_zzdata(joint_ks_sorted, yy_data, xx_data, active_info):
    """Generate input values to heatmap,
    shows as missing data when 0active observations
    """
    zz_data = joint_ks_sorted.loc[yy_data, xx_data].to_numpy()
    for yid in range(len(yy_data)):
        for xid, xxd in enumerate(xx_data):
            active_obs_info = active_info.at["ratio", xxd].split(" ")
            if active_obs_info[0] == "0":
                zz_data[yid][xid] = None
    return zz_data


def _set_inputfilter(input_filter: str) -> str:
    """Set the input filter to show all data if empty"""
    return "_" if input_filter == "" else input_filter


@webvizstore
def get_path(path) -> Path:
    return Path(path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def read_csv(path: Path, index_col: Optional[int] = None) -> pd.DataFrame:
    return pd.read_csv(path, index_col=index_col)
