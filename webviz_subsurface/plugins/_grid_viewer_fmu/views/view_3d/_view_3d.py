from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

import jwt
import numpy as np
from dash import Input, Output, State, callback, html, no_update
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewABC

from webviz_subsurface._providers.ensemble_grid_provider import (
    CellFilter,
    EnsembleGridProvider,
    GridVizService,
    PropertySpec,
)

from ..._layout_elements import ElementIds
from ..._types import PROPERTYTYPE
from .settings import ColorScale, DataSettings, GridFilter
from .view_elements._vtk_view_3d_element import VTKView3D


class View3D(ViewABC):
    class Ids(StrEnum):
        VTKVIEW = "vtkview"
        DATASELECTORS = "data-selectors"
        GRIDFILTER = "grid-filter"
        COLORSCALE = "color-scale"

    def __init__(
        self,
        grid_provider: EnsembleGridProvider,
        grid_viz_service: GridVizService,
        initial_grid_filter: Dict[str, int],
    ) -> None:
        super().__init__("Grid View")
        self.grid_provider = grid_provider
        self.grid_viz_service = grid_viz_service
        self.vtk_view_3d = VTKView3D()
        self.add_view_element(self.vtk_view_3d, View3D.Ids.VTKVIEW)
        self.add_settings_group(
            DataSettings(grid_provider=grid_provider), View3D.Ids.DATASELECTORS
        )
        self.add_settings_group(
            GridFilter(
                grid_provider=grid_provider, initial_grid_filter=initial_grid_filter
            ),
            View3D.Ids.GRIDFILTER,
        )
        self.add_settings_group(ColorScale(), View3D.Ids.COLORSCALE)

    def _view_id(self, component_id: str) -> str:
        return (
            self.view_element(View3D.Ids.VTKVIEW)
            .component_unique_id(component_id)
            .to_string()
        )

    def _data_settings_id(self, component_id: str) -> str:
        return (
            self.settings_group(View3D.Ids.DATASELECTORS)
            .component_unique_id(component_id)
            .to_string()
        )

    def _color_scale_id(self, component_id: str) -> str:
        return (
            self.settings_group(View3D.Ids.COLORSCALE)
            .component_unique_id(component_id)
            .to_string()
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self._view_id(VTKView3D.Ids.VIEW),
                "layers",
            ),
            Output(
                self._view_id(VTKView3D.Ids.VIEW),
                "bounds",
            ),
            Input(
                self._data_settings_id(DataSettings.Ids.PROPERTIES),
                "value",
            ),
            Input(
                self._data_settings_id(DataSettings.Ids.DATES),
                "value",
            ),
            Input(
                self._data_settings_id(DataSettings.Ids.REALIZATIONS),
                "value",
            ),
            Input(self.get_store_unique_id(ElementIds.IJK_CROP_STORE), "data"),
            Input(self._color_scale_id(ColorScale.Ids.COLORRANGEMANUAL), "value"),
            Input(self._color_scale_id(ColorScale.Ids.COLORMIN), "value"),
            Input(self._color_scale_id(ColorScale.Ids.COLORMAX), "value"),
            Input(
                self._color_scale_id(ColorScale.Ids.COLORMAP),
                "value",
            ),
            State(
                self._data_settings_id(DataSettings.Ids.STATIC_DYNAMIC),
                "value",
            ),
            State(
                self._view_id(VTKView3D.Ids.VIEW),
                "layers",
            ),
            State(
                self._view_id(VTKView3D.Ids.VIEW),
                "bounds",
            ),
        )
        # pylint: disable=too-many-arguments, too-many-locals
        def _set_geometry_and_scalar(
            prop: List[str],
            date: List[str],
            realizations: List[int],
            grid_range: List[List[int]],
            should_use_manual: List[str],
            manual_min: Optional[float],
            manual_max: Optional[float],
            colormap: str,
            proptype: str,
            layers: List[Dict],
            bounds: Optional[List[float]],
        ) -> Tuple[List[Dict], Optional[List]]:

            if PROPERTYTYPE(proptype) == PROPERTYTYPE.STATIC:
                property_spec = PropertySpec(prop_name=prop[0], prop_date=None)
            else:
                property_spec = PropertySpec(prop_name=prop[0], prop_date=date[0])

            realization = realizations[0]

            if not bounds or not layers[0]["bounds"]:
                geometrics = self.grid_provider.get_3dgrid(realization).get_geometrics(
                    allcells=True, return_dict=True
                )

                bounds = [
                    geometrics["xmin"],
                    geometrics["ymin"],
                    geometrics["xmax"],
                    geometrics["ymax"],
                ]
                layers[0]["bounds"] = [
                    geometrics["xmin"],
                    geometrics["ymin"],
                    -geometrics["zmax"],
                    geometrics["xmax"],
                    geometrics["ymax"],
                    -geometrics["zmin"],
                ]
            else:
                bounds = no_update
            provider_id = self.grid_provider.provider_id()

            cell_filter = CellFilter(
                i_min=grid_range[0][0],
                i_max=grid_range[0][1],
                j_min=grid_range[1][0],
                j_max=grid_range[1][1],
                k_min=grid_range[2][0],
                k_max=grid_range[2][1],
            )

            geometry_token = jwt.encode(
                {
                    "provider_id": provider_id,
                    "realization": realization,
                    "cell_filter": asdict(cell_filter),
                },
                "secret",
                algorithm="HS256",
            )
            geometry_and_property_token = jwt.encode(
                {
                    "provider_id": provider_id,
                    "realization": realization,
                    "cell_filter": asdict(cell_filter),
                    "property_spec": asdict(property_spec),
                },
                "secret",
                algorithm="HS256",
            )

            if should_use_manual and manual_min and manual_max:
                value_range = [manual_min, manual_max]
            else:
                value_range = None

            layers[1]["pointsUrl"] = f"/grid/points/{geometry_token}"
            layers[1]["polysUrl"] = f"/grid/polys/{geometry_token}"
            layers[1]["propertiesUrl"] = f"/grid/scalar/{geometry_and_property_token}"
            layers[1]["colorMapRange"] = value_range
            layers[1]["colorMapName"] = colormap
            return layers, bounds

        @callback(
            Output(
                self._color_scale_id(ColorScale.Ids.COLORMIN),
                "disabled",
            ),
            Output(
                self._color_scale_id(ColorScale.Ids.COLORMAX),
                "disabled",
            ),
            Input(
                self._color_scale_id(ColorScale.Ids.COLORRANGEMANUAL),
                "value",
            ),
        )
        def _toggle_manual_color(enabled: List[str]) -> Tuple[bool, bool]:

            if enabled:
                return False, False
            return True, True

        @callback(
            Output(self._view_id(VTKView3D.Ids.INFOBOX), "children"),
            Input(
                self._data_settings_id(DataSettings.Ids.PROPERTIES),
                "value",
            ),
            Input(
                self._data_settings_id(DataSettings.Ids.DATES),
                "value",
            ),
            Input(
                self._data_settings_id(DataSettings.Ids.REALIZATIONS),
                "value",
            ),
            Input(
                self._view_id(VTKView3D.Ids.VIEW),
                "layers",
            ),
            Input(self.get_store_unique_id(ElementIds.IJK_CROP_STORE), "data"),
            State(
                self._data_settings_id(DataSettings.Ids.STATIC_DYNAMIC),
                "value",
            ),
        )
        def update_infobox(
            properties: List[str],
            dates: List[str],
            realizations: List[int],
            layers: List[dict],
            grid_range: List[List[int]],
            proptype: str,
        ) -> list:
            """Updates the information box with information on the visualized data."""
            if PROPERTYTYPE(proptype) == PROPERTYTYPE.STATIC:
                property_spec = PropertySpec(prop_name=properties[0], prop_date=None)
            else:
                property_spec = PropertySpec(
                    prop_name=properties[0], prop_date=dates[0]
                )

            realization = realizations[0]
            provider_id = self.grid_provider.provider_id()

            cell_filter = CellFilter(
                i_min=grid_range[0][0],
                i_max=grid_range[0][1],
                j_min=grid_range[1][0],
                j_max=grid_range[1][1],
                k_min=grid_range[2][0],
                k_max=grid_range[2][1],
            )
            scalars = self.grid_viz_service.get_mapped_property_values(
                provider_id=provider_id,
                realization=realization,
                cell_filter=cell_filter,
                property_spec=property_spec,
            )
            if scalars is not None:
                actual_value_range = [
                    np.nanmin(scalars.value_arr),
                    np.nanmax(scalars.value_arr),
                ]
            else:
                actual_value_range = [0, 0]
            color_range = layers[1].get("colorMapRange")
            if color_range is None:
                color_range = actual_value_range

            return [
                html.Div([html.B("Property: "), html.Label(properties[0])]),
                html.Div(
                    [html.B("Date: "), html.Label(dates[0] if dates else "No date")]
                ),
                html.Div([html.B("Realization: "), html.Label(realization)]),
                html.Div(
                    [
                        html.B("Color range: "),
                        html.Label(f"{color_range[0]:.2f} - {color_range[1]:.2f}"),
                    ]
                ),
                html.Div(
                    [
                        html.B("Actual value range: "),
                        html.Label(
                            f"{actual_value_range[0]:.2f} - {actual_value_range[1]:.2f}"
                        ),
                    ]
                ),
            ]
