import orjson as json
import jwt

import numpy as np
from dash import Dash

from webviz_subsurface._providers.ensemble_grid_provider import (
    CellFilter,
    GridVizService,
    PropertySpec,
)


def set_routes(app: Dash, grid_viz_service: GridVizService) -> None:
    @app.server.route("/grid/points/<token>")
    def _get_points(token: str) -> bytes:
        try:
            geometry_token = jwt.decode(token, "secret", algorithms=["HS256"])
        except:
            return json.dumps([])
        provider_id = geometry_token["provider_id"]
        realization = geometry_token["realization"]
        # property_spec = PropertySpec(**geometry_token["property_spec"])
        cell_filter = CellFilter(**geometry_token["cell_filter"])
        surface_polys, scalars = grid_viz_service.get_surface(
            provider_id=provider_id,
            realization=realization,
            cell_filter=cell_filter,
            property_spec=None,
        )
        return json.dumps(surface_polys.point_arr.tolist())

    @app.server.route("/grid/polys/<token>")
    def _get_polys(token: str) -> bytes:
        try:
            geometry_token = jwt.decode(token, "secret", algorithms=["HS256"])
        except:
            return json.dumps([])
        provider_id = geometry_token["provider_id"]
        realization = geometry_token["realization"]
        # property_spec = PropertySpec(**geometry_token["property_spec"])
        cell_filter = CellFilter(**geometry_token["cell_filter"])
        surface_polys, scalars = grid_viz_service.get_surface(
            provider_id=provider_id,
            realization=realization,
            cell_filter=cell_filter,
            property_spec=None,
        )
        return json.dumps(surface_polys.poly_arr.tolist())

    @app.server.route("/grid/scalar/<token>")
    def _get_scalar(token: str) -> bytes:
        try:
            geometry_token = jwt.decode(token, "secret", algorithms=["HS256"])
        except:
            return json.dumps([])
        provider_id = geometry_token["provider_id"]
        realization = geometry_token["realization"]
        property_spec = PropertySpec(**geometry_token["property_spec"])
        cell_filter = CellFilter(**geometry_token["cell_filter"])
        surface_polys, scalars = grid_viz_service.get_surface(
            provider_id=provider_id,
            realization=realization,
            cell_filter=cell_filter,
            property_spec=property_spec,
        )
        return json.dumps(scalars.value_arr.tolist() if scalars else [])
