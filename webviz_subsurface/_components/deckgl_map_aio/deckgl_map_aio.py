from dash import (
    html,
    dcc,
    callback,
    Input,
    Output,
    State,
    MATCH,
    callback_context,
    no_update,
)


from ._deckgl_map_viewer import DeckGLMapViewer
from ._deckgl_map_controller import DeckGLMapController


class DeckGLMapAIO(html.Div):
    class ids:
        map = lambda aio_id: {
            "component": "DeckGLMapAIO",
            "subcomponent": "map",
            "aio_id": aio_id,
        }
        colormap_image = lambda aio_id: {
            "component": "DataTableAIO",
            "subcomponent": "colormap_image",
            "aio_id": aio_id,
        }
        colormap_range = lambda aio_id: {
            "component": "DataTableAIO",
            "subcomponent": "colormap_range",
            "aio_id": aio_id,
        }
        polylines = lambda aio_id: {
            "component": "DataTableAIO",
            "subcomponent": "polylines",
            "aio_id": aio_id,
        }
        selected_well = lambda aio_id: {
            "component": "DataTableAIO",
            "subcomponent": "selected_well",
            "aio_id": aio_id,
        }
        map_data = lambda aio_id: {
            "component": "DataTableAIO",
            "subcomponent": "map_data",
            "aio_id": aio_id,
        }

    ids = ids

    def __init__(
        self,
        aio_id,
    ):
        """"""

        super().__init__(
            [
                dcc.Store(data=[], id=self.ids.colormap_image(aio_id)),
                dcc.Store(data=[], id=self.ids.colormap_range(aio_id)),
                dcc.Store(data=[], id=self.ids.polylines(aio_id)),
                dcc.Store(data=[], id=self.ids.selected_well(aio_id)),
                dcc.Store(data=[], id=self.ids.map_data(aio_id)),
                DeckGLMapViewer(
                    id=self.ids.map(aio_id),
                    surface=True,
                    wells=True,
                    pie_charts=True,
                    drawing=True,
                ),
            ]
        )

    @callback(
        Output(ids.map(MATCH), "deckglSpecBase"),
        Input(ids.colormap_image(MATCH), "data"),
        Input(ids.colormap_range(MATCH), "data"),
        State(ids.map(MATCH), "deckglSpecBase"),
        State(ids.map(MATCH), "deckglSpecPatch"),
    )
    def _update_spec(colormap_image, colormap_range, current_spec, client_patch):
        """This should be moved to a clientside callback"""
        map_controller = DeckGLMapController(current_spec, client_patch=client_patch)
        triggered_prop = callback_context.triggered[0]["prop_id"]
        initial_callback = True if triggered_prop == "." else False
        if initial_callback or "colormap_image" in triggered_prop:
            map_controller.update_colormap(colormap_image)
        if initial_callback or "colormap_range" in triggered_prop:
            map_controller.update_colormap_range(colormap_range)
        return map_controller._spec

    @callback(
        Output(ids.map(MATCH), "resources"),
        Input(ids.map_data(MATCH), "data"),
        State(ids.map(MATCH), "resources"),
    )
    def update_resources(map_data, current_resources):
        triggered_prop = callback_context.triggered[0]["prop_id"]
        current_resources.update(**map_data)
        return current_resources

    @callback(
        Output(ids.polylines(MATCH), "data"),
        Output(ids.selected_well(MATCH), "data"),
        Input(ids.map(MATCH), "deckglSpecPatch"),
        State(ids.map(MATCH), "deckglSpecBase"),
        State(ids.polylines(MATCH), "data"),
        State(ids.selected_well(MATCH), "data"),
    )
    def _update_from_client(
        client_patch, current_spec, polyline_state, selected_well_state
    ):
        map_controller = DeckGLMapController(current_spec, client_patch=client_patch)
        polyline_data = map_controller.get_polylines()
        selected_well = map_controller.get_selected_well()
        selected_well = (
            selected_well if selected_well != selected_well_state else no_update
        )
        polyline_data = polyline_data if polyline_data != polyline_state else no_update
        return polyline_data, selected_well
