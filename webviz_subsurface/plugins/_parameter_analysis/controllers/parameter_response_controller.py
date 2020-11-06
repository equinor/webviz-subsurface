from typing import Tuple, Union
from itertools import chain

import numpy as np
import pandas as pd
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import dash
import dash_core_components as dcc
import plotly.express as px
import plotly.graph_objects as go

from ..utils.colors import find_intermediate_color
from ..figures.correlation_figure import CorrelationFigure
from ..utils.colors import hex_to_rgb, rgb_to_hex


# pylint: disable=too-many-statements,
def parameter_response_controller(parent, app):
    @app.callback(
        Output(parent.uuid("vector-vs-time-graph"), "figure"),
        Output(parent.uuid("vector-vs-param-scatter"), "figure"),
        Output(parent.uuid("vector-corr-graph"), "figure"),
        Output(parent.uuid("param-corr-graph"), "figure"),
        Input({"id": parent.uuid("ensemble-selector"), "tab": "response"}, "value"),
        Input(parent.uuid("vector-select"), "children"),
        Input({"id": parent.uuid("parameter-select"), "tab": "response"}, "value"),
        Input(parent.uuid("date-selected"), "children"),
        Input({"id": parent.uuid("vtype-filter"), "tab": "response"}, "value"),
        Input(
            {
                "id": parent.uuid("vitem-filter"),
                "tab": "response",
                "vtype": ALL,
            },
            "value",
        ),
        Input({"id": parent.uuid("plot-options"), "tab": "response"}, "value"),
        State(parent.uuid("vector-vs-time-graph"), "figure"),
        State(parent.uuid("param-corr-graph"), "figure"),
        State(parent.uuid("vector-corr-graph"), "figure"),
        State(parent.uuid("vector-vs-param-scatter"), "figure"),
    )
    # pylint: disable=too-many-locals, too-many-arguments
    def _update_graphs(
        ensemble: str,
        vector: str,
        parameter: Union[None, dict],
        date: str,
        vector_type_filter: list,
        vector_item_filters: list,
        options: str,
        timeseries_fig: dict,
        corr_p_fig: dict,
        corr_v_fig: dict,
        scatter_fig: dict,
    ) -> Tuple[dict, dict, dict, dict]:
        """
        Main callback to update plots. Initially all plots are generated,
        while only relevant plots are updated in subsequent callbacks
        """

        if (
            dash.callback_context.triggered is None
            or dash.callback_context.triggered[0]["prop_id"] == "."
            or vector is None
        ):
            raise PreventUpdate
        ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

        color = options["color"] if options["color"] is not None else "#007079"
        daterange = parent.vmodel.daterange_for_plot(vector=vector)

        # Make timeseries graph
        if (
            relevant_ctx_for_plot(parent, ctx, plot="timeseries_fig")
            or timeseries_fig is None
        ):
            timeseries_fig = update_timeseries_graph(
                parent.vmodel,
                ensemble,
                vector,
                xaxisrange=[min(daterange[0], date), max(daterange[1], date)],
                real_filter=None,
            )

        vectors_filtered = filter_vectors(
            parent, vector_type_filter, vector_item_filters
        )
        if vector not in vectors_filtered:
            vectors_filtered.append(vector)

        merged_df = merge_parameter_and_vector_df(
            parent, ensemble, vectors_filtered, date
        )

        # Make correlation figure for vector
        if options["autocompute_corr"] and (
            relevant_ctx_for_plot(parent, ctx, plot="vector_correlation")
            or corr_v_fig is None
        ):
            corr_v_fig = make_correlation_figure(
                merged_df, response=vector, corrwith=parent.pmodel.parameters
            ).figure

        # Get clicked parameter correlation bar or largest bar initially
        parameter = (
            parameter if parameter is not None else corr_v_fig["data"][0]["y"][-1]
        )
        corr_v_fig = color_corr_bars(corr_v_fig, parameter, color, options["opacity"])

        # Make correlation figure for parameter
        if options["autocompute_corr"] and (
            relevant_ctx_for_plot(parent, ctx, plot="parameter_correlation")
            or corr_p_fig is None
        ):
            corr_p_fig = make_correlation_figure(
                merged_df, response=parameter, corrwith=vectors_filtered
            ).figure

        corr_p_fig = color_corr_bars(corr_p_fig, vector, color, options["opacity"])

        # Create scatter plot of vector vs parameter
        if relevant_ctx_for_plot(parent, ctx, plot="scatter") or scatter_fig is None:
            scatter_fig = update_scatter_graph(merged_df, vector, parameter, color)

        scatter_fig = scatter_fig_color_update(scatter_fig, color, options["opacity"])

        # Order realizations sorted on value of parameter and color traces
        df_value_norm = parent.pmodel.get_real_and_value_df(
            ensemble, parameter=parameter, normalize=True
        )
        timeseries_fig = color_timeseries_graph(
            timeseries_fig, ensemble, parameter, vector, df_value_norm
        )

        # Draw date selected as line
        timeseries_fig = add_date_line(timeseries_fig, date, options["show_dateline"])

        # Ensure xaxis covers selected date
        if parent.uuid("date-selected") in ctx:
            timeseries_fig["layout"]["xaxis"].update(
                range=[min(daterange[0], date), max(daterange[1], date)]
            )

        return timeseries_fig, scatter_fig, corr_v_fig, corr_p_fig

    @app.callback(
        Output(parent.uuid("date-slider"), "value"),
        Input(parent.uuid("vector-vs-time-graph"), "clickData"),
    )
    def _update_date_from_clickdata(timeseries_clickdata: Union[None, dict]):
        """Update date-slider from clickdata"""
        dates = parent.vmodel.dates
        return (
            dates.index(timeseries_clickdata.get("points", [{}])[0]["x"])
            if timeseries_clickdata is not None
            else len(dates) - 1
        )

    @app.callback(
        Output(parent.uuid("date-selected"), "children"),
        Input(parent.uuid("date-slider"), "value"),
    )
    def _update_date(dateidx: int):
        """Update selected date from date-slider"""
        return parent.vmodel.dates[dateidx]

    @app.callback(
        Output({"id": parent.uuid("plot-options"), "tab": "response"}, "value"),
        Input({"id": parent.uuid("checkbox-options"), "tab": "response"}, "value"),
        Input({"id": parent.uuid("color-selector"), "tab": "response"}, "clickData"),
        Input({"id": parent.uuid("opacity-selector"), "tab": "response"}, "value"),
    )
    def _update_plot_options(
        checkbox_options: list,
        color_clickdata: str,
        opacity: float,
    ):
        """Combine plot options in one dictionary"""
        ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
        if color_clickdata is not None:
            color = color_clickdata["points"][0]["marker.color"]
            if "rgb" in color:
                color = rgb_to_hex(color)

        return dict(
            show_dateline="DateLine" in checkbox_options,
            autocompute_corr="AutoCompute" in checkbox_options,
            color=None if color_clickdata is None else color,
            opacity=opacity,
            ctx=ctx,
        )

    @app.callback(
        Output(parent.uuid("vector-select"), "children"),
        Input(parent.uuid("vshort-select"), "value"),
        Input({"id": parent.uuid("vitem-select"), "shortname": ALL}, "value"),
    )
    def _combine_substrings_to_vector(shortname: str, item: list):
        """Combine vector shortname and item to full vector name"""
        vector = shortname if not item or item[0] is None else f"{shortname}:{item[0]}"

        if vector not in parent.vmodel.vectors:
            raise PreventUpdate
        return vector

    @app.callback(
        Output(parent.uuid("vshort-select"), "options"),
        Output(parent.uuid("vshort-select"), "value"),
        Output(parent.uuid("clickdata-store"), "data"),
        Input({"id": parent.uuid("vtype-select"), "state": ALL}, "value"),
        Input(parent.uuid("param-corr-graph"), "clickData"),
    )
    def _update_vectorlist(vtype: list, corr_param_clickdata: dict):
        """
        Update the vector shortname options and selected value from
        selected vector type or clickdata
        """
        ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
        click_data = parent.uuid("param-corr-graph") in ctx

        vtype = vtype[0]

        if click_data:
            vector_selected = corr_param_clickdata.get("points", [{}])[0].get("y")
            vtype = find_vector_type(parent, vector_selected)

        shortname = (
            vector_selected.split(":")[0]
            if click_data
            else parent.vmodel.vector_groups[vtype]["shortnames"][0]
        )

        return (
            [
                {"label": i, "value": i}
                for i in parent.vmodel.vector_groups[vtype]["shortnames"]
            ],
            shortname,
            dict(
                vector=vector_selected,
                shortname=shortname,
                vtype=vtype,
            )
            if click_data
            else {},
        )

    @app.callback(
        Output(parent.uuid("vitems-container"), "children"),
        Output(parent.uuid("vtype-container"), "children"),
        Input(parent.uuid("vshort-select"), "value"),
        State({"id": parent.uuid("vtype-select"), "state": ALL}, "value"),
        State(parent.uuid("clickdata-store"), "data"),
        State({"id": parent.uuid("vitem-select"), "shortname": ALL}, "value"),
    )
    def _update_vector_items(
        shortname: str,
        previous_vtype: list,
        clickdata_vector: dict,
        previous_item: list,
    ):
        """
        Update the div container for vector type and vector item selections
        from clickdata and selected vector shortname
        """
        if clickdata_vector and shortname != clickdata_vector["shortname"]:
            clickdata_vector = {}
        vtype = clickdata_vector["vtype"] if clickdata_vector else previous_vtype[0]

        items = [
            v
            for v in parent.vmodel.vector_groups[vtype]["items"]
            if f"{shortname}:{v}" in parent.vmodel.vectors
        ]
        if items and not clickdata_vector:
            item = previous_item[0] if previous_item[0] in items else items[0]
        if items and clickdata_vector:
            item = clickdata_vector["vector"].replace(f"{shortname}:", "")

        return (
            [
                dcc.Dropdown(
                    id={"id": parent.uuid("vitem-select"), "shortname": shortname},
                    options=[{"label": i, "value": i} for i in items],
                    value=item if items else None,
                    disabled=not items,
                    placeholder="No subselections...",
                    clearable=False,
                    persistence=True,
                    persistence_type="session",
                )
            ],
            [
                dcc.RadioItems(
                    id={"id": parent.uuid("vtype-select"), "state": "update"},
                    options=[
                        {"label": i, "value": i} for i in parent.vmodel.vector_groups
                    ],
                    value=vtype,
                    labelStyle={"display": "inline-block", "margin-right": "10px"},
                )
            ]
            if clickdata_vector and clickdata_vector["vtype"] != previous_vtype[0]
            else dash.no_update,
        )

    @app.callback(
        Output({"id": parent.uuid("parameter-select"), "tab": "response"}, "value"),
        Input(parent.uuid("vector-corr-graph"), "clickData"),
    )
    def _update_parameter_selected(
        corr_vector_clickdata: Union[None, dict],
    ) -> str:
        """Update the selected parameter from clickdata"""
        if corr_vector_clickdata is None:
            raise PreventUpdate
        return corr_vector_clickdata.get("points", [{}])[0].get("y")


# pylint: disable=inconsistent-return-statements
def relevant_ctx_for_plot(parent, ctx: list, plot: str):
    """Group relevant uuids for the different plots"""
    vector = parent.uuid("vector-select") in ctx
    date = parent.uuid("date-selected") in ctx
    parameter = parent.uuid("parameter-select") in ctx
    ensemble = parent.uuid("ensemble-selector") in ctx
    filtered_vectors = (
        parent.uuid("vtype-filter") in ctx or parent.uuid("vitem-filter") in ctx
    )

    if plot == "timeseries_fig":
        return any([vector, ensemble])
    if plot == "scatter":
        return any([vector, date, parameter, ensemble])
    if plot == "parameter_correlation":
        return any([filtered_vectors, date, parameter, ensemble])
    if plot == "vector_correlation":
        return any([vector, date, ensemble])


def find_vector_type(parent, vector: str):
    """Get vector type from vector"""
    for vgroup, values in parent.vmodel.vector_groups.items():
        if vector in values["vectors"]:
            return vgroup
    return None


def filter_vectors(parent, vector_types: list, vector_items: list):
    """Filter vector list used for correlation"""
    vectors = list(
        chain.from_iterable(
            [parent.vmodel.vector_groups[vtype]["vectors"] for vtype in vector_types]
        )
    )
    items = list(chain.from_iterable(vector_items))
    filtered_vectors_with_items = [
        v for v in vectors if any(v.split(":")[1] == x for x in items if ":" in v)
    ]
    return [v for v in vectors if v in filtered_vectors_with_items or ":" not in v]


def update_timeseries_graph(
    timeseries_model,
    ensemble: str,
    vector: str,
    xaxisrange: list,
    real_filter: pd.Series = None,
):
    """Create vector vs time plot"""
    return {
        "data": timeseries_model.add_realization_traces(
            ensemble=ensemble, vector=vector, real_filter=real_filter
        ),
        "layout": dict(
            margin={"r": 20, "l": 20, "t": 60, "b": 20},
            yaxis={"automargin": True},
            xaxis={"range": xaxisrange},
            hovermode="closest",
            paper_bgcolor="white",
            plot_bgcolor="white",
            showlegend=False,
        ),
    }


def add_date_line(figure: dict, selected_date: str, show_dateline: bool):
    """Add/remove dateline on timeseries graph."""
    dateline_idx = [
        idx for idx, trace in enumerate(figure["data"]) if trace["name"] == "Dateline"
    ]
    if dateline_idx and show_dateline:
        figure["data"][dateline_idx[0]].update(
            x=[selected_date, selected_date], text=["", selected_date]
        )
    if dateline_idx and not show_dateline:
        figure["data"].pop(int(dateline_idx[0]))

    if not dateline_idx and show_dateline:
        ymin = min([min(trace["y"]) for trace in figure["data"]])
        ymax = max([max(trace["y"]) for trace in figure["data"]])
        figure["data"].append(
            go.Scatter(
                x=[selected_date, selected_date],
                y=[ymin, ymax],
                cliponaxis=False,
                mode="lines+text",
                line={"dash": "dot", "width": 4, "color": "#243746"},
                name="Dateline",
                text=["", selected_date],
                textposition="top center",
            )
        )
    return figure


def color_timeseries_graph(
    figure: dict,
    ensemble: str,
    selected_param: str,
    vector: str,
    df_norm: pd.DataFrame = None,
):
    """Color timeseries lines by parameter value"""
    if df_norm is not None:

        for trace_no, trace in enumerate(figure.get("data", [])):
            if trace["name"] == ensemble:
                figure["data"][trace_no]["marker"]["color"] = set_real_color(
                    real_no=trace["customdata"], df_norm=df_norm
                )
                figure["data"][trace_no]["hovertext"] = (
                    f"Real: {str(trace['customdata'])}, {selected_param}: "
                    f"{df_norm.loc[df_norm['REAL'] == trace['customdata']].iloc[0]['VALUE']}"
                )
        figure["layout"]["title"] = {
            "text": f"{vector} colored by {selected_param}",
        }

    return figure


def set_real_color(df_norm, real_no: str):
    """
    Return color for trace based on normalized parameter value.
    Midpoint for the colorscale is set on the average value
    """
    red = "rgba(255,18,67, 1)"
    mid_color = "rgba(220,220,220,1"
    green = "rgba(62,208,62, 1)"

    mean = df_norm["VALUE_NORM"].mean()

    norm_value = df_norm.loc[df_norm["REAL"] == real_no].iloc[0]["VALUE_NORM"]
    if norm_value <= mean:
        intermed = norm_value / mean
        return find_intermediate_color(red, mid_color, intermed, colortype="rgba")
    if norm_value > mean:
        intermed = (norm_value - mean) / (1 - mean)
        return find_intermediate_color(mid_color, green, intermed, colortype="rgba")
    return "rgba(220,220,220, 0.2"


def merge_parameter_and_vector_df(parent, ensemble: str, vectors: list, date: str):
    """Merge parameter dataframe with vector dataframe on given date """
    # Get dataframe with vector and REAL
    vector_df = parent.vmodel.get_ensemble_vectors_for_date(
        ensemble=ensemble,
        vectors=vectors,
        date=date,
    ).copy()
    vector_df["REAL"] = vector_df["REAL"].astype(int)
    # Get dataframe with parameters
    param_df = parent.pmodel.dataframe.copy()
    param_df = param_df[param_df["ENSEMBLE"] == ensemble]
    param_df["REAL"] = param_df["REAL"].astype(int)
    # Return merged dataframe
    param_df.set_index("REAL", inplace=True)
    vector_df.set_index("REAL", inplace=True)
    return vector_df.join(param_df).reset_index()


def update_scatter_graph(
    df: pd.DataFrame, vector: str, selected_param: str, color: str = None
):
    """Create scatter plot of selected vector vs selected parameter"""
    return (
        px.scatter(
            df[[vector, selected_param]],
            x=selected_param,
            y=vector,
            trendline="ols" if df[vector].nunique() > 1 else None,
            trendline_color_override="#243746",
        )
        .update_layout(
            margin={
                "r": 20,
                "l": 20,
                "t": 60,
                "b": 20,
            },
            paper_bgcolor="white",
            plot_bgcolor="white",
            title={"text": f"{vector} vs {selected_param}", "x": 0.5},
            xaxis_title=None,
            yaxis_title=None,
        )
        .update_traces(
            marker={
                "size": 15,
                "color": hex_to_rgb(color, 0.7),
                "line": {"width": 1.2, "color": hex_to_rgb(color, 1)},
            }
        )
    )


def scatter_fig_color_update(figure: dict, color: str, opacity: float):
    """Update color for scatter plot"""
    for trace in figure["data"]:
        if trace["mode"] == "markers":
            trace["marker"].update(color=hex_to_rgb(color, opacity))
            trace["marker"]["line"].update(color=hex_to_rgb(color, 1))
    return figure


def make_correlation_figure(df: pd.DataFrame, response: str, corrwith: list):
    """Create a bar plot with correlations for chosen response"""
    corrseries = correlate(df[corrwith + [response]], response=response)
    return CorrelationFigure(
        corrseries, n_rows=15, title=f"Correlations with {response}"
    )


def correlate(df: pd.DataFrame, response: str):
    """Returns the correlation matrix for a dataframe"""
    df = df[df.columns[df.nunique() > 1]].copy()
    if response not in df.columns:
        df[response] = np.nan
    series = df[response]
    df = df.drop(columns=[response])
    corrdf = df.corrwith(series)
    return corrdf.reindex(corrdf.abs().sort_values().index)


def color_corr_bars(
    figure: dict,
    selected_bar: str,
    color: str,
    opacity: float,
    color_selected="#FF1243",
):
    """
    Set colors to the correlation plot bar,
    with separate color for the selected bar
    """
    figure["data"][0]["marker"] = {
        "color": [
            hex_to_rgb(color, opacity)
            if _bar != selected_bar
            else hex_to_rgb(color_selected, 0.8)
            for _bar in figure["data"][0]["y"]
        ],
        "line": {
            "color": [
                color if _bar != selected_bar else color_selected
                for _bar in figure["data"][0]["y"]
            ],
            "width": 1.2,
        },
    }
    return figure
