from typing import Callable

from dash import Input, Output, State, ALL,callback
from dash.exceptions import PreventUpdate
import plotly.graph_objs as go

from webviz_subsurface._figures import create_figure
from ..models import UpscalingQCModel
from ..layout.sidebar import PlotTypes

def update_plot(get_uuid: Callable, qc_model: UpscalingQCModel) -> None:
    @callback(
        Output(get_uuid("plotly-graph"), "figure"),
        Input(get_uuid("plot-type"), "value"),
        Input(get_uuid("x"), "value"),
        Input({"type": get_uuid("selector"), "value": ALL}, "value"),
        State({"type": get_uuid("selector"), "value": ALL}, "id")
    )
    def _update_plotly_graph(plot_type, x_column, selector_values, selector_ids) -> go.Figure:
        selectors = [id_obj["value"] for id_obj in selector_ids]
        dframe = qc_model.get_dataframe(selectors=selectors, selector_values=selector_values, responses=[x_column], max_points=100000)
        plot_type = PlotTypes(plot_type)
        if plot_type == PlotTypes.HISTOGRAM:
            return create_figure(
            plot_type="histogram",
            data_frame=dframe,
            color="SOURCE",
            x=x_column,
            
        )

        raise PreventUpdate

