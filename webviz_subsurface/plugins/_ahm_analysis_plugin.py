import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_config import WebvizPluginABC


class AssistedHistoryMatchingAnalysis(WebvizPluginABC):
    """### Parameter distribution change prior/posterior per observation
    Shows parameter change using a KS (Kolmogorov Smirnov test) matrix,
    and scatter plot/map for any given pair of parameters/observation."""

    def __init__(
        self, app, title: str = "Data analytics: what affects what", input_dir: str = ""
    ):

        super().__init__()

        self.title = title
        self.input_dir = str(input_dir)
        self.set_callbacks(app)

    @property
    def layout(self):
        return html.Div(
            [
                html.H1(self.title),
                html.Div(
                    children="""
        Give path to input data:
        """
                ),
                dcc.Input(
                    id=self.ids("inputpath_id"),
                    value=self.input_dir,
                    type="text",
                    debounce=True,
                    size=150,
                ),
                html.Div(
                    children="""
        Filter observations:
        """
                ),
                dcc.Input(
                    id=self.ids("filter1_id"), value="", type="text", debounce=True
                ),
                html.Div(
                    children="""
        Filter parameters:
        """
                ),
                dcc.Input(
                    id=self.ids("filter2_id"),
                    value="",
                    type="text",
                    debounce=True,
                ),
                html.Div(
                    children="""
        Selected output:
        """
                ),
                dcc.RadioItems(
                    id=self.ids("choice_id"),
                    options=[
                        {"label": "One by one observation", "value": "ONE"},
                        {"label": "All minus one observation", "value": "ALL"},
                    ],
                    value="ONE",
                    labelStyle={"display": "inline-block"},
                ),
                dcc.RadioItems(
                    id=self.ids("choice_hist_id"),
                    options=[
                        {
                            "label": "Show default parameters distribution",
                            "value": "DFLT",
                        },
                        {
                            "label": "Show transformed parameters distribution (if available)",
                            "value": "TRANS",
                        },
                    ],
                    value="DFLT",
                    labelStyle={"display": "inline-block"},
                ),
                html.Div(
                    children=[
                        html.Div(
                            id=self.ids("output_graph"),
                            style={
                                "width": "50%",
                                "display": "inline-block",
                                "height": 750,
                            },
                        ),
                        html.Div(
                            id=self.ids("click_data"),
                            style={
                                "width": "50%",
                                "display": "inline-block",
                                "height": 750,
                            },
                        ),
                    ],
                    style={"width": "100%", "display": "inline-block"},
                ),
                html.Div(
                    children=[
                        html.H4(
                            children="Table of 10 highest parameters change/update Ks",
                            style={"marginLeft": 50},
                        ),
                        html.Div(
                            id=self.ids("generate_table"),
                            style={"marginLeft": 50, "width": "80%"},
                        ),
                    ]
                ),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(
                component_id=self.ids("output_graph"), component_property="children"
            ),
            [
                Input(
                    component_id=self.ids("inputpath_id"), component_property="value"
                ),
                Input(component_id=self.ids("filter1_id"), component_property="value"),
                Input(component_id=self.ids("filter2_id"), component_property="value"),
                Input(component_id=self.ids("choice_id"), component_property="value"),
            ],
        )
        def _update_graph(inputdata, input_filter_obs, input_filter_param, choiceplot):
            """Renders KS matrix
            (how much a parameter is changed from prior to posterior"""
            # Checks if any input have been given
            if inputdata == "":
                return ""
            if inputdata[-1] != "/":
                inputdata = inputdata + "/"
            active_info = pd.read_csv(inputdata + "active_obs_info.csv", index_col=0)
            joint_ks = pd.read_csv(inputdata + "ks.csv", index_col=0).replace(
                np.nan, 0.0
            )
            input_filter_obs = set_inputfilter(input_filter_obs)
            input_filter_param = set_inputfilter(input_filter_param)

            listtoplot = get_listtoplot(joint_ks, choiceplot)
            joint_ks_sorted = joint_ks.filter(items=listtoplot).sort_index(axis=1)
            xx_data = list(
                joint_ks_sorted.filter(like=input_filter_obs, axis=1).columns
            )
            yy_data = list(
                joint_ks_sorted.filter(like=input_filter_param, axis=0).index
            )
            zz_data = get_zzdata(joint_ks_sorted, yy_data, xx_data, active_info)

            yall_obs_data = list(
                joint_ks_sorted.filter(like=input_filter_param, axis=0).index
            )
            zall_obs_data = joint_ks.loc[yall_obs_data, ["All_obs"]].to_numpy()

            return dcc.Graph(
                id=self.ids("heatmap_id"),
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
                            text=hovertext_list(xx_data, yy_data, zz_data, active_info),
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
                            text=hovertext_list(
                                ["All_obs"], yall_obs_data, zall_obs_data, active_info
                            ),
                            xaxis="x2",
                        ),
                    ],
                    "layout": go.Layout(
                        title="KS Matrix (parameters degree of change prior to posterior)",
                        xaxis=dict(
                            title="Observations",
                            ticks="",
                            domain=[0.0, 0.9],
                            showticklabels=True,
                            tickangle=30,
                            automargin=True,
                        ),
                        yaxis=dict(
                            title="Parameters",
                            ticks="",
                            showticklabels=True,
                            tickangle=-30,
                            automargin=True,
                        ),
                        xaxis2=dict(ticks="", domain=[0.95, 1.0]),
                        # margin=go.layout.Margin(l=250, r=0, t=40, b=150)
                        plot_bgcolor="grey",
                    ),
                },
                style={"height": 750},
                clickData={"points": [{"x": xx_data[0], "y": yy_data[0]}]},
            )

        @app.callback(
            Output(component_id=self.ids("click_data"), component_property="children"),
            [
                Input(
                    component_id=self.ids("inputpath_id"), component_property="value"
                ),
                Input(
                    component_id=self.ids("heatmap_id"), component_property="clickData"
                ),
                Input(
                    component_id=self.ids("choice_hist_id"), component_property="value"
                ),
            ],
        )
        def _display_click_data(inputdata, celldata, hist_display):
            """render a histogram of parameters distribution prior/posterior or
            an average delta map prior-posterior."""
            if inputdata == "":
                return ""
            if inputdata[-1] != "/":
                inputdata = inputdata + "/"
            obs = celldata["points"][0]["x"]
            param = celldata["points"][0]["y"]
            active_info = pd.read_csv(inputdata + "active_obs_info.csv", index_col=0)
            if "FIELD" in param:
                fieldparam = param.replace("FIELD_", "")
                inputdata = (
                    inputdata.replace("scalar_", "field_")
                    + "/delta_field"
                    + fieldparam
                    + ".csv"
                )
                mygrid_ok_short = pd.read_csv(inputdata)
                maxinput = mygrid_ok_short.filter(like="Mean_").max(axis=1)
                deltadata = "Mean_D_" + obs
                return dcc.Graph(
                    id="2Dmap_avgdelta",
                    figure=px.scatter(
                        mygrid_ok_short,
                        x="X_UTME",
                        y="Y_UTMN",
                        color=deltadata,
                        range_color=[0, maxinput.max()],
                        color_continuous_scale="Rainbow",  # size=sizeby,
                        opacity=0.9,  # size_max=size_max,
                        title="Mean_delta_posterior-prior " + obs + " ," + param,
                        hover_data=[
                            "X_UTME",
                            "Y_UTMN",
                            "Z_TVDSS",
                            "IX",
                            "JY",
                            deltadata,
                        ],
                        height=750,
                    ),
                )
            post_df = pd.read_csv(inputdata + obs + ".csv")
            prior_df = pd.read_csv(inputdata + "prior.csv")
            if hist_display == "TRANS":
                paraml = [ele for ele in prior_df.keys() if "_" + param in ele]
                if paraml != []:
                    param = paraml[0]
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=prior_df[param], name="prior", nbinsx=10))
            fig.add_trace(go.Histogram(x=post_df[param], name="update", nbinsx=10))
            fig.update_layout(
                title="Parameter distribution for observation "
                + obs
                + " ("
                + str(active_info.at["ratio", obs])
                + ")",
                bargap=0.2,
                bargroupgap=0.1,
                xaxis=dict(title=param),
            )
            return dcc.Graph(id="lineplots", style={"height": 750}, figure=fig)

        @app.callback(
            Output(
                component_id=self.ids("generate_table"), component_property="children"
            ),
            [
                Input(
                    component_id=self.ids("inputpath_id"), component_property="value"
                ),
                Input(component_id=self.ids("choice_id"), component_property="value"),
            ],
        )
        def _generatetable(inputdata, choiceplot, max_rows=10):
            """Generate output table of data in KS matrix plot"""
            if inputdata == "":
                return ""
            if inputdata[-1] != "/":
                inputdata = inputdata + "/"
            misfit_info = pd.read_csv(inputdata + "misfit_obs_info.csv", index_col=0)
            active_info = pd.read_csv(inputdata + "active_obs_info.csv", index_col=0)
            joint_ks = pd.read_csv(inputdata + "ks.csv", index_col=0).replace(
                np.nan, 0.0
            )
            list_ok = list(joint_ks.filter(like="All_obs", axis=1).columns)
            listtoplot = [ele for ele in joint_ks.columns if ele not in list_ok]
            if choiceplot == "ALL":
                listtoplot = list_ok

            ks_filter = get_ks_filter(listtoplot, active_info, misfit_info, joint_ks)

            ks_filter_ok = ks_filter.sort_values(by="Ks_value", ascending=False)

            return dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in ks_filter_ok.columns],
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
                data=ks_filter_ok.to_dict("records"),
                sort_action="native",
                filter_action="native",
                page_action="native",
                page_current=0,
                page_size=max_rows,
            )


def hovertext_list(xx_data, yy_data, zz_data, active_info):
    """define hovertext info"""
    hovertext = list()
    for parami, paramy in enumerate(yy_data):
        hovertext.append(list())
        for obsi, obsx in enumerate(xx_data):
            hovertext[-1].append(
                "Obs ("
                + str(active_info.at["ratio", obsx])
                + "): {}<br />Param: {}<br />Ks: {}".format(
                    obsx, paramy, zz_data[parami][obsi]
                )
            )
    return hovertext


def get_ks_filter(listtoplot, active_info, misfit_info, joint_ks):
    """generate KS dataframe filtered"""
    ks_filter = pd.DataFrame(
        columns=["Ks_value", "Obs", "Param", "Active Obs", "Avg Obs misfit"]
    )
    i = 0
    for keyss in listtoplot:
        for indk in joint_ks[keyss]:
            active_obs_info = active_info.at["ratio", keyss].split(" ")
            index_label = joint_ks[joint_ks[keyss] == indk].index.tolist()
            ks_filter.loc[i] = [
                indk,
                keyss,
                index_label,
                int(active_obs_info[0]),
                misfit_info.at["misfit", keyss],
            ]
            i = i + 1
    return ks_filter


def get_listtoplot(joint_ks, choiceplot):
    """generate correct observations to plot based on choice made"""
    list_ok = list(joint_ks.filter(like="All_obs", axis=1).columns)
    listtoplot = [ele for ele in joint_ks.columns if ele not in list_ok]
    if choiceplot == "ALL":
        list_ok.remove("All_obs")
        listtoplot = list_ok
    return listtoplot


def get_zzdata(joint_ks_sorted, yy_data, xx_data, active_info):
    """generate input values to heatmap,
    shows as missing data when 0active observations"""
    zz_data = joint_ks_sorted.loc[yy_data, xx_data].to_numpy()
    for yid in range(len(yy_data)):
        for xid, xxd in enumerate(xx_data):
            active_obs_info = active_info.at["ratio", xxd].split(" ")
            if active_obs_info[0] == "0":
                zz_data[yid][xid] = None
    return zz_data


def set_inputfilter(input_filter):
    """set the input filter to show all data if empty"""
    if input_filter == "":
        input_filter = "_"
    return input_filter
