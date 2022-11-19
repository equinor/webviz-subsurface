from typing import Callable, Dict, List, Optional

from dash import ALL, ClientsideFunction, Dash, Input, Output, callback_context
from dash.exceptions import PreventUpdate
from plotly.graph_objects import Figure


def update_figure_clientside(app: Dash, get_uuid: Callable) -> None:
    @app.callback(
        Output(
            {"id": get_uuid("clientside"), "plotly_attribute": "update_layout"}, "data"
        ),
        Input({"id": get_uuid("plotly_layout"), "layout_attribute": ALL}, "value"),
        Input(get_uuid("plotly_uirevision"), "value"),
    )
    def _update_layout(layout_attributes: Optional[List], uirevision: str) -> Dict:
        """Store plotly layout options from user selections in a dcc.Store"""
        if layout_attributes is None:
            return {}
        layout = {}
        for ctx in callback_context.inputs_list[0]:
            layout[ctx["id"]["layout_attribute"]] = ctx.get("value", None)
        layout["uirevision"] = str(uirevision) if uirevision else None
        return layout

    @app.callback(
        Output(
            {"id": get_uuid("clientside"), "plotly_attribute": "plotly_layout"}, "data"
        ),
        Input(
            {"id": get_uuid("clientside"), "plotly_attribute": "initial_layout"}, "data"
        ),
        Input(
            {"id": get_uuid("clientside"), "plotly_attribute": "update_layout"}, "data"
        ),
    )
    def _update_plot_layout(initial_layout: dict, update_layout: dict) -> Dict:
        if initial_layout is None:
            raise PreventUpdate
        fig = Figure({"layout": initial_layout})
        if update_layout is not None:
            fig.update_layout(update_layout)
        return fig["layout"]

    app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="set_dcc_figure"),
        Output(get_uuid("graph"), "figure"),
        Input(
            {"id": get_uuid("clientside"), "plotly_attribute": "plotly_layout"}, "data"
        ),
        Input(
            {"id": get_uuid("clientside"), "plotly_attribute": "plotly_data"}, "data"
        ),
    )
