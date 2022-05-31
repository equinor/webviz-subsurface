import logging
from typing import Dict, List, Optional
from urllib.parse import quote
from dataclasses import dataclass

import flask
import geojson
import numpy as np
from dash import Dash
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import (
    vtkCellArray,
    vtkPolyData,
    vtkPolyLine,
)
from vtkmodules.util.numpy_support import vtk_to_numpy

from webviz_subsurface._providers.well_provider.well_provider import WellProvider
from webviz_subsurface._utils.perf_timer import PerfTimer

LOGGER = logging.getLogger(__name__)

_ROOT_URL_PATH = "/WellServer"

_WELL_SERVER_INSTANCE: Optional["WellServer"] = None


@dataclass
class PolyLine:
    point_arr: np.ndarray
    line_arr: np.ndarray


class WellServer:
    def __init__(self, app: Dash) -> None:
        self._setup_url_rule(app)
        self._id_to_provider_dict: Dict[str, WellProvider] = {}

    @staticmethod
    def instance(app: Dash) -> "WellServer":
        # pylint: disable=global-statement
        global _WELL_SERVER_INSTANCE
        if not _WELL_SERVER_INSTANCE:
            LOGGER.debug("Initializing SurfaceServer instance")
            _WELL_SERVER_INSTANCE = WellServer(app)

        return _WELL_SERVER_INSTANCE

    def register_provider(self, provider: WellProvider) -> None:

        provider_id = provider.provider_id()
        LOGGER.debug(f"Adding provider with id={provider_id}")

        existing_provider = self._id_to_provider_dict.get(provider_id)
        if existing_provider:
            # Issue a warning if there already is a provider registered with the same
            # id AND if the actual provider instance is different.
            # This should not be a problem, but will happen until the provider factory
            # gets caching.
            if existing_provider is not provider:
                LOGGER.warning(
                    f"Provider with id={provider_id} ignored, the id is already present"
                )
                return

        self._id_to_provider_dict[provider_id] = provider

    def encode_partial_url(
        self,
        provider_id: str,
        well_names: List[str],
    ) -> str:

        if not provider_id in self._id_to_provider_dict:
            raise ValueError("Could not find provider")

        sorted_well_names_str = "~".join(sorted(well_names))

        url_path: str = (
            f"{_ROOT_URL_PATH}/{quote(provider_id)}/{quote(sorted_well_names_str)}"
        )

        return url_path

    def _setup_url_rule(self, app: Dash) -> None:
        @app.server.route(_ROOT_URL_PATH + "/<provider_id>/<well_names_str>")
        def _handle_wells_request(
            provider_id: str, well_names_str: str
        ) -> flask.Response:
            LOGGER.debug(
                f"Handling well request: "
                f"provider_id={provider_id} "
                f"well_names_str={well_names_str} "
            )

            timer = PerfTimer()

            try:
                provider = self._id_to_provider_dict[provider_id]
                well_names_arr = well_names_str.split("~")
            # pylint: disable=bare-except
            except:
                LOGGER.error("Error decoding wells address")
                flask.abort(404)

            validate_geometry = True
            feature_arr = []
            for wname in well_names_arr:
                well_path = provider.get_well_path(wname)

                coords = list(zip(well_path.x_arr, well_path.y_arr, well_path.z_arr))
                # coords = coords[0::20]
                point = geojson.Point(
                    coordinates=[coords[0][0], coords[0][1]], validate=validate_geometry
                )

                geocoll = geojson.GeometryCollection(geometries=[point])

                feature = geojson.Feature(
                    id=wname, geometry=geocoll, properties={"name": wname}
                )
                feature_arr.append(feature)

            featurecoll = geojson.FeatureCollection(features=feature_arr)
            response = flask.Response(
                geojson.dumps(featurecoll), mimetype="application/geo+json"
            )

            LOGGER.debug(f"Request handled in: {timer.elapsed_s():.2f}s")
            return response

    def get_polyline(
        self, provider_id: str, well_name: str, tvdmin: float = None
    ) -> PolyLine:
        provider = self._id_to_provider_dict[provider_id]
        well_path = provider.get_well_path(well_name)
        xyz_arr = [
            [x, y, z]
            for x, y, z in zip(well_path.x_arr, well_path.y_arr, well_path.z_arr)
        ]
        points = vtkPoints()
        for p in xyz_arr:
            points.InsertNextPoint(p[0], p[1], -p[2])

        polyLine = vtkPolyLine()
        polyLine.GetPointIds().SetNumberOfIds(len(xyz_arr))
        for i in range(0, len(xyz_arr)):
            polyLine.GetPointIds().SetId(i, i)

        # Create a cell array to store the lines in and add the lines to it
        cells = vtkCellArray()
        cells.InsertNextCell(polyLine)

        # Create a polydata to store everything in
        polyData = vtkPolyData()
        # Add the points to the dataset
        polyData.SetPoints(points)

        # Add the lines to the dataset
        polyData.SetLines(cells)
        points = vtk_to_numpy(polyData.GetPoints().GetData())
        lines = vtk_to_numpy(polyData.GetLines().GetData())
        return PolyLine(point_arr=points, line_arr=lines)
