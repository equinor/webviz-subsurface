from typing import List, Tuple, Dict, Optional

import numpy as np
from webviz_config.webviz_plugin_subclasses import (
    ViewABC,
)

from dash.development.base_component import Component

from dash import Input, Output, State, callback, callback_context, no_update, ALL
import webviz_core_components as wcc
from webviz_vtk.utils.vtk import b64_encode_numpy

from webviz_subsurface._providers.ensemble_grid_provider import (
    EnsembleGridProvider,
    GridVizService,
    PropertySpec,
    CellFilter,
    Ray,
)
from webviz_subsurface._utils.perf_timer import PerfTimer
from ..._layout_elements import ElementIds
from ..._types import PROPERTYTYPE
from .settings import DataSettings, GridFilter, Settings
from .view_elements._vtk_view_3d_element import VTKView3D


class View3D(ViewABC):
    def __init__(
        self, grid_provider: EnsembleGridProvider, grid_viz_service: GridVizService
    ) -> None:
        super().__init__("Grid View")
        self.grid_provider = grid_provider
        self.grid_viz_service = grid_viz_service
        self.vtk_view_3d = VTKView3D()
        self.add_view_element(self.vtk_view_3d, ElementIds.VTKVIEW3D.ID),
        self.add_settings_group(
            DataSettings(grid_provider=grid_provider), ElementIds.DataSelectors.ID
        )
        self.add_settings_group(
            GridFilter(grid_provider=grid_provider), ElementIds.GridFilter.ID
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(ElementIds.VTKVIEW3D.ID)
                .component_unique_id(ElementIds.VTKVIEW3D.GRID_POLYDATA)
                .to_string(),
                "polys",
            ),
            Output(
                self.view_element(ElementIds.VTKVIEW3D.ID)
                .component_unique_id(ElementIds.VTKVIEW3D.GRID_POLYDATA)
                .to_string(),
                "points",
            ),
            Output(
                self.view_element(ElementIds.VTKVIEW3D.ID)
                .component_unique_id(ElementIds.VTKVIEW3D.GRID_CELLDATA)
                .to_string(),
                "values",
            ),
            Output(
                self.view_element(ElementIds.VTKVIEW3D.ID)
                .component_unique_id(ElementIds.VTKVIEW3D.GRID_REPRESENTATION)
                .to_string(),
                "colorDataRange",
            ),
            Input(
                self.settings_group(ElementIds.DataSelectors.ID)
                .component_unique_id(ElementIds.DataSelectors.PROPERTIES)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ElementIds.DataSelectors.ID)
                .component_unique_id(ElementIds.DataSelectors.DATES)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ElementIds.DataSelectors.ID)
                .component_unique_id(ElementIds.DataSelectors.REALIZATIONS)
                .to_string(),
                "value",
            ),
            Input(
                self.get_store_unique_id(ElementIds.GridFilter.IJK_CROP_STORE), "data"
            ),
            State(
                self.settings_group(ElementIds.DataSelectors.ID)
                .component_unique_id(ElementIds.DataSelectors.STATIC_DYNAMIC)
                .to_string(),
                "value",
            ),
            State(
                self.view_element(ElementIds.VTKVIEW3D.ID)
                .component_unique_id(ElementIds.VTKVIEW3D.GRID_POLYDATA)
                .to_string(),
                "polys",
            ),
        )
        def _set_geometry_and_scalar(
            prop: List[str],
            date: List[int],
            realizations: List[int],
            grid_range: List[List[int]],
            proptype: str,
            current_polys: str,
        ) -> Tuple:

            if PROPERTYTYPE(proptype) == PROPERTYTYPE.STATIC:
                property_spec = PropertySpec(prop_name=prop[0], prop_date=0)
            else:
                property_spec = PropertySpec(prop_name=prop[0], prop_date=date[0])

            triggered = callback_context.triggered[0]["prop_id"]
            timer = PerfTimer()
            if (
                triggered == "."
                or current_polys is None
                or self.get_store_unique_id(ElementIds.GridFilter.IJK_CROP_STORE)
                in triggered
                or self.settings_group(ElementIds.DataSelectors.ID)
                .component_unique_id(ElementIds.DataSelectors.REALIZATIONS)
                .to_string()
                in triggered
            ):
                surface_polys, scalars = self.grid_viz_service.get_surface(
                    provider_id=self.grid_provider.provider_id(),
                    realization=realizations[0],
                    property_spec=property_spec,
                    cell_filter=CellFilter(
                        i_min=grid_range[0][0],
                        i_max=grid_range[0][1],
                        j_min=grid_range[1][0],
                        j_max=grid_range[1][1],
                        k_min=grid_range[2][0],
                        k_max=grid_range[2][1],
                    ),
                )

                return (
                    b64_encode_numpy(surface_polys.poly_arr.astype(np.float32)),
                    b64_encode_numpy(surface_polys.point_arr.astype(np.float32)),
                    b64_encode_numpy(scalars.value_arr.astype(np.float32)),
                    [np.nanmin(scalars.value_arr), np.nanmax(scalars.value_arr)],
                )
            else:
                scalars = self.grid_viz_service.get_mapped_property_values(
                    provider_id=self.grid_provider.provider_id(),
                    realization=realizations[0],
                    property_spec=property_spec,
                    cell_filter=CellFilter(
                        i_min=grid_range[0][0],
                        i_max=grid_range[0][1],
                        j_min=grid_range[1][0],
                        j_max=grid_range[1][1],
                        k_min=grid_range[2][0],
                        k_max=grid_range[2][1],
                    ),
                )
                return (
                    no_update,
                    no_update,
                    b64_encode_numpy(scalars.value_arr.astype(np.float32)),
                    [np.nanmin(scalars.value_arr), np.nanmax(scalars.value_arr)],
                )
