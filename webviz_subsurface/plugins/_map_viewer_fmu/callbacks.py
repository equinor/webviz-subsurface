from dataclasses import asdict
from typing import Callable, Dict, List, Optional, Tuple, Any

from dash import Input, Output, State, callback, callback_context, no_update
from dash.exceptions import PreventUpdate
from flask import url_for
from webviz_config.utils._dash_component_utils import calculate_slider_step

from webviz_subsurface._components import DeckGLMapAIO
from webviz_subsurface._components.deckgl_map.providers.xtgeo import (
    get_surface_bounds,
    get_surface_range,
)
from webviz_subsurface._models.well_set_model import WellSetModel

from .layout import LayoutElements
from .models.surface_set_model import SurfaceMode, SurfaceSetModel
from .types import SurfaceContext, WellsContext
from .utils.formatting import format_date


def plugin_callbacks(
    get_uuid: Callable,
    surface_set_models: Dict[str, SurfaceSetModel],
    well_set_model: Optional[WellSetModel],
) -> None:
    disabled_style = {"opacity": 0.5, "pointerEvents": "none"}

    def left_view(element_id: str) -> Dict[str, str]:
        return {"view": LayoutElements.LEFT_VIEW, "id": get_uuid(element_id)}

    def right_view(element_id: str) -> Dict[str, str]:
        return {"view": LayoutElements.RIGHT_VIEW, "id": get_uuid(element_id)}

    @callback(
        Output(left_view(LayoutElements.ATTRIBUTE), "options"),
        Output(left_view(LayoutElements.ATTRIBUTE), "value"),
        Input(left_view(LayoutElements.ENSEMBLE), "value"),
        State(left_view(LayoutElements.ATTRIBUTE), "value"),
    )
    def _update_attribute(
        ensemble: str, current_attr: List[str]
    ) -> Tuple[List[Dict], List[Any]]:
        if surface_set_models.get(ensemble) is None:
            raise PreventUpdate
        available_attrs = surface_set_models[ensemble].attributes
        attr = (
            current_attr if current_attr[0] in available_attrs else available_attrs[:1]
        )
        options = [{"label": val, "value": val} for val in available_attrs]
        return options, attr

    @callback(
        Output(left_view(LayoutElements.REALIZATIONS), "options"),
        Output(left_view(LayoutElements.REALIZATIONS), "value"),
        Output(left_view(LayoutElements.REALIZATIONS), "multi"),
        Input(left_view(LayoutElements.ENSEMBLE), "value"),
        Input(left_view(LayoutElements.MODE), "value"),
        State(left_view(LayoutElements.REALIZATIONS), "value"),
    )
    def _update_real(
        ensemble: str,
        mode: str,
        current_reals: List[int],
    ) -> Tuple[List[Dict], List[int], bool]:
        if surface_set_models.get(ensemble) is None or current_reals is None:
            raise PreventUpdate
        available_reals = surface_set_models[ensemble].realizations
        if SurfaceMode(mode) == SurfaceMode.REALIZATION:
            reals = (
                [current_reals[0]]
                if current_reals[0] in available_reals
                else [available_reals[0]]
            )
            multi = False
        else:
            reals = available_reals
            multi = True
        options = [{"label": val, "value": val} for val in available_reals]
        return options, reals, multi

    @callback(
        Output(left_view(LayoutElements.DATE), "options"),
        Output(left_view(LayoutElements.DATE), "value"),
        Input(left_view(LayoutElements.ATTRIBUTE), "value"),
        State(left_view(LayoutElements.DATE), "value"),
        State(left_view(LayoutElements.ENSEMBLE), "value"),
    )
    def _update_date(
        attribute: List[str], current_date: List[str], ensemble: str
    ) -> Tuple[Optional[List[Dict]], Optional[List]]:

        available_dates = surface_set_models[ensemble].dates_in_attribute(attribute[0])

        if not available_dates:
            return None, None
        date = (
            current_date
            if current_date is not None and current_date[0] in available_dates
            else available_dates[:1]
        )
        options = [{"label": format_date(val), "value": val} for val in available_dates]
        return options, date

    @callback(
        Output(left_view(LayoutElements.NAME), "options"),
        Output(left_view(LayoutElements.NAME), "value"),
        Input(left_view(LayoutElements.ATTRIBUTE), "value"),
        State(left_view(LayoutElements.NAME), "value"),
        State(left_view(LayoutElements.ENSEMBLE), "value"),
    )
    def _update_name(
        attribute: List[str], current_name: List[str], ensemble: str
    ) -> Tuple[List[Dict], List]:

        available_names = surface_set_models[ensemble].names_in_attribute(attribute[0])
        name = (
            current_name
            if current_name is not None and current_name[0] in available_names
            else available_names[:1]
        )
        options = [{"label": val, "value": val} for val in available_names]
        return options, name

    @callback(
        Output(left_view(LayoutElements.SELECTED_DATA), "data"),
        Input(left_view(LayoutElements.ATTRIBUTE), "value"),
        Input(left_view(LayoutElements.NAME), "value"),
        Input(left_view(LayoutElements.DATE), "value"),
        Input(left_view(LayoutElements.ENSEMBLE), "value"),
        Input(left_view(LayoutElements.REALIZATIONS), "value"),
        Input(left_view(LayoutElements.MODE), "value"),
    )
    def _update_stored_data(
        attribute: List[str],
        name: List[str],
        date: Optional[List[str]],
        ensemble: str,
        realizations: List[int],
        mode: str,
    ) -> Dict:

        surface_spec = SurfaceContext(
            attribute=attribute[0],
            name=name[0],
            date=date[0] if date else None,
            ensemble=ensemble,
            realizations=realizations,
            mode=SurfaceMode(mode),
        )

        return asdict(surface_spec)

    @callback(
        Output(right_view(LayoutElements.ATTRIBUTE), "options"),
        Output(right_view(LayoutElements.ATTRIBUTE), "value"),
        Output(right_view(LayoutElements.ATTRIBUTE), "style"),
        Input(right_view(LayoutElements.ENSEMBLE), "value"),
        Input(left_view(LayoutElements.ATTRIBUTE), "value"),
        Input(get_uuid(LayoutElements.LINK_ATTRIBUTE), "value"),
        State(right_view(LayoutElements.ATTRIBUTE), "value"),
        State(left_view(LayoutElements.ATTRIBUTE), "options"),
    )
    def _update_attribute_right(
        ensemble: str,
        view1_attribute_value: List[str],
        link: bool,
        current_attr: List[str],
        view1_attribute_options: List[Dict[str, str]],
    ) -> Tuple[List[Dict], List[str], dict]:
        if link:
            return (view1_attribute_options, view1_attribute_value, disabled_style)
        if surface_set_models.get(ensemble) is None:
            raise PreventUpdate
        available_attrs = surface_set_models[ensemble].attributes
        attr = (
            current_attr if current_attr[0] in available_attrs else available_attrs[:1]
        )
        options = [{"label": val, "value": val} for val in available_attrs]
        return options, attr, {}

    @callback(
        Output(right_view(LayoutElements.REALIZATIONS), "options"),
        Output(right_view(LayoutElements.REALIZATIONS), "value"),
        Output(right_view(LayoutElements.REALIZATIONS), "multi"),
        Output(right_view(LayoutElements.REALIZATIONS), "style"),
        Input(right_view(LayoutElements.ENSEMBLE), "value"),
        Input(right_view(LayoutElements.MODE), "value"),
        Input(left_view(LayoutElements.REALIZATIONS), "value"),
        Input(get_uuid(LayoutElements.LINK_REALIZATIONS), "value"),
        State(right_view(LayoutElements.REALIZATIONS), "value"),
        State(left_view(LayoutElements.REALIZATIONS), "options"),
        State(left_view(LayoutElements.REALIZATIONS), "multi"),
    )
    def _update_real_right(
        ensemble: str,
        mode: str,
        view1_realizations_value: List[int],
        link: bool,
        current_reals: List[int],
        view1_realizations_options: List[Dict[str, int]],
        view1_realizations_mode: bool,
    ) -> Tuple[List[Dict], List[int], bool, dict]:
        if link:
            return (
                view1_realizations_options,
                view1_realizations_value,
                view1_realizations_mode,
                disabled_style,
            )
        if surface_set_models.get(ensemble) is None or current_reals is None:
            raise PreventUpdate
        available_reals = surface_set_models[ensemble].realizations
        if SurfaceMode(mode) == SurfaceMode.REALIZATION:
            reals = (
                current_reals[:1]
                if current_reals[0] in available_reals
                else available_reals[:1]
            )
            multi = False
        else:
            reals = available_reals
            multi = True
        options = [{"label": val, "value": val} for val in available_reals]
        return options, reals, multi, {}

    @callback(
        Output(right_view(LayoutElements.DATE), "options"),
        Output(right_view(LayoutElements.DATE), "value"),
        Output(right_view(LayoutElements.DATE), "style"),
        Input(right_view(LayoutElements.ATTRIBUTE), "value"),
        Input(left_view(LayoutElements.DATE), "value"),
        Input(get_uuid(LayoutElements.LINK_DATE), "value"),
        State(right_view(LayoutElements.DATE), "value"),
        State(right_view(LayoutElements.ENSEMBLE), "value"),
        State(left_view(LayoutElements.DATE), "options"),
    )
    def _update_date_right(
        attribute: List[str],
        view1_date_value: List[str],
        link: bool,
        current_date: List[str],
        ensemble: str,
        view1_date_options: Optional[List[Dict[str, str]]],
    ) -> Tuple[Optional[List[Dict]], Optional[List[str]], dict]:
        if link:
            return view1_date_options, view1_date_value, disabled_style

        available_dates = surface_set_models[ensemble].dates_in_attribute(attribute[0])
        if not available_dates:
            return None, None, {}
        date = (
            current_date
            if current_date is not None and current_date[0] in available_dates
            else available_dates[:1]
        )
        options = [{"label": format_date(val), "value": val} for val in available_dates]
        return options, date, {}

    @callback(
        Output(right_view(LayoutElements.NAME), "options"),
        Output(right_view(LayoutElements.NAME), "value"),
        Output(right_view(LayoutElements.NAME), "style"),
        Input(right_view(LayoutElements.ATTRIBUTE), "value"),
        Input(left_view(LayoutElements.NAME), "value"),
        Input(get_uuid(LayoutElements.LINK_NAME), "value"),
        State(right_view(LayoutElements.NAME), "value"),
        State(right_view(LayoutElements.ENSEMBLE), "value"),
        State(left_view(LayoutElements.NAME), "options"),
    )
    def _update_name_right(
        attribute: List[str],
        view1_name_value: List[str],
        link: bool,
        current_name: List[str],
        ensemble: str,
        view1_name_options: List[Dict[str, str]],
    ) -> Tuple[List[Dict], List[str], dict]:
        if link:
            return view1_name_options, view1_name_value, disabled_style
        available_names = surface_set_models[ensemble].names_in_attribute(attribute[0])
        name = (
            current_name
            if current_name is not None and current_name[0] in available_names
            else available_names[:1]
        )
        options = [{"label": val, "value": val} for val in available_names]
        return options, name, {}

    @callback(
        Output(right_view(LayoutElements.MODE), "value"),
        Output(right_view(LayoutElements.MODE), "style"),
        Input(left_view(LayoutElements.MODE), "value"),
        Input(get_uuid(LayoutElements.LINK_MODE), "value"),
    )
    def _update_mode_right(view1_mode: str, link: bool) -> Tuple[str, dict]:
        if link:
            return view1_mode, disabled_style
        return no_update, {}

    @callback(
        Output(right_view(LayoutElements.ENSEMBLE), "value"),
        Output(right_view(LayoutElements.ENSEMBLE), "style"),
        Input(left_view(LayoutElements.ENSEMBLE), "value"),
        Input(get_uuid(LayoutElements.LINK_ENSEMBLE), "value"),
    )
    def _update_ensemble_right(view1_ensemble: str, link: bool) -> Tuple[str, dict]:
        if link:
            return view1_ensemble, disabled_style
        return no_update, {}

    @callback(
        Output(right_view(LayoutElements.SELECTED_DATA), "data"),
        Input(right_view(LayoutElements.ATTRIBUTE), "value"),
        Input(right_view(LayoutElements.NAME), "value"),
        Input(right_view(LayoutElements.DATE), "value"),
        Input(right_view(LayoutElements.ENSEMBLE), "value"),
        Input(right_view(LayoutElements.REALIZATIONS), "value"),
        Input(right_view(LayoutElements.MODE), "value"),
        State(get_uuid(LayoutElements.LINK_ATTRIBUTE), "value"),
        State(get_uuid(LayoutElements.LINK_NAME), "value"),
        State(get_uuid(LayoutElements.LINK_DATE), "value"),
        State(get_uuid(LayoutElements.LINK_ENSEMBLE), "value"),
        State(get_uuid(LayoutElements.LINK_REALIZATIONS), "value"),
        State(get_uuid(LayoutElements.LINK_MODE), "value"),
        State(left_view(LayoutElements.ATTRIBUTE), "value"),
        State(left_view(LayoutElements.NAME), "value"),
        State(left_view(LayoutElements.DATE), "value"),
        State(left_view(LayoutElements.ENSEMBLE), "value"),
        State(left_view(LayoutElements.REALIZATIONS), "value"),
        State(left_view(LayoutElements.MODE), "value"),
    )
    def _update_stored_data_right(
        attribute: str,
        name: str,
        date: str,
        ensemble: str,
        realizations: List[int],
        mode: str,
        linked_attribute: bool,
        linked_name: bool,
        linked_date: bool,
        linked_ensemble: bool,
        linked_realizations: bool,
        linked_mode: bool,
        view1_attribute: str,
        view1_name: str,
        view1_date: str,
        view1_ensemble: str,
        view1_realizations: List[int],
        view1_mode: str,
    ) -> dict:

        surface_spec = SurfaceContext(
            attribute=attribute if not linked_attribute else view1_attribute,
            name=name if not linked_name else view1_name,
            date=date if not linked_date else view1_date,
            ensemble=ensemble if not linked_ensemble else view1_ensemble,
            realizations=realizations
            if not linked_realizations
            else view1_realizations,
            mode=SurfaceMode(mode) if not linked_mode else SurfaceMode(view1_mode),
        )

        return asdict(surface_spec)

    @callback(
        Output(
            DeckGLMapAIO.ids.propertymap_image(get_uuid(LayoutElements.DECKGLMAP_LEFT)),
            "data",
        ),
        Output(
            DeckGLMapAIO.ids.propertymap_range(get_uuid(LayoutElements.DECKGLMAP_LEFT)),
            "data",
        ),
        Output(
            DeckGLMapAIO.ids.propertymap_bounds(
                get_uuid(LayoutElements.DECKGLMAP_LEFT)
            ),
            "data",
        ),
        Input(left_view(LayoutElements.SELECTED_DATA), "data"),
    )
    def _update_property_map(
        surface_selected_data: dict,
    ) -> Tuple[str, List[float], List[float]]:
        selected_surface = SurfaceContext(**surface_selected_data)
        ensemble = selected_surface.ensemble
        surface = surface_set_models[ensemble].get_surface(selected_surface)

        return (
            url_for("_send_surface_as_png", surface_context=selected_surface),
            get_surface_range(surface),
            get_surface_bounds(surface),
        )

    @callback(
        Output(
            DeckGLMapAIO.ids.colormap_image(get_uuid(LayoutElements.DECKGLMAP_LEFT)),
            "data",
        ),
        Input(left_view(LayoutElements.COLORMAP_SELECT), "value"),
    )
    def _update_color_map(colormap: str) -> str:
        return f"/colormaps/{colormap}.png"

    if well_set_model is not None:

        @callback(
            Output(
                DeckGLMapAIO.ids.well_data(get_uuid(LayoutElements.DECKGLMAP_LEFT)),
                "data",
            ),
            Input(left_view(LayoutElements.WELLS), "value"),
        )
        def _update_well_data(wells: List[str]) -> str:
            wells_context = WellsContext(well_names=wells)
            return url_for("_send_well_data_as_json", wells_context=wells_context)

        @callback(
            Output(
                DeckGLMapAIO.ids.well_data(get_uuid(LayoutElements.DECKGLMAP_RIGHT)),
                "data",
            ),
            Input(right_view(LayoutElements.WELLS), "value"),
        )
        def _update_well_data_right(wells: List[str]) -> str:
            wells_context = WellsContext(well_names=wells)
            return url_for("_send_well_data_as_json", wells_context=wells_context)

    @callback(
        Output(
            DeckGLMapAIO.ids.colormap_range(get_uuid(LayoutElements.DECKGLMAP_LEFT)),
            "data",
        ),
        Input(left_view(LayoutElements.COLORMAP_RANGE), "value"),
    )
    def _update_colormap_range(colormap_range: List[float]) -> List[float]:
        return colormap_range

    @callback(
        Output(left_view(LayoutElements.COLORMAP_RANGE), "min"),
        Output(left_view(LayoutElements.COLORMAP_RANGE), "max"),
        Output(left_view(LayoutElements.COLORMAP_RANGE), "step"),
        Output(left_view(LayoutElements.COLORMAP_RANGE), "value"),
        Output(left_view(LayoutElements.COLORMAP_RANGE), "marks"),
        Input(
            DeckGLMapAIO.ids.propertymap_range(get_uuid(LayoutElements.DECKGLMAP_LEFT)),
            "data",
        ),
        Input(left_view(LayoutElements.COLORMAP_KEEP_RANGE), "value"),
        Input(left_view(LayoutElements.COLORMAP_RESET_RANGE), "n_clicks"),
        State(left_view(LayoutElements.COLORMAP_RANGE), "value"),
    )
    def _update_colormap_range_slider(
        value_range: List[float], keep: str, reset: int, current_val: List[float]
    ) -> Tuple[float, float, float, List[float], dict]:
        ctx = callback_context.triggered[0]["prop_id"]
        min_val = value_range[0]
        max_val = value_range[1]
        if ctx == ".":
            value = no_update
        if (
            LayoutElements.COLORMAP_RESET_RANGE in ctx
            or not keep
            or current_val is None
        ):
            value = [min_val, max_val]
        else:
            value = current_val
        return (
            min_val,
            max_val,
            calculate_slider_step(min_value=min_val, max_value=max_val, steps=100)
            if min_val != max_val
            else 0,
            value,
            {
                str(min_val): {"label": f"{min_val:.2f}"},
                str(max_val): {"label": f"{max_val:.2f}"},
            },
        )

    @callback(
        Output(
            DeckGLMapAIO.ids.propertymap_image(
                get_uuid(LayoutElements.DECKGLMAP_RIGHT)
            ),
            "data",
        ),
        Output(
            DeckGLMapAIO.ids.propertymap_range(
                get_uuid(LayoutElements.DECKGLMAP_RIGHT)
            ),
            "data",
        ),
        Output(
            DeckGLMapAIO.ids.propertymap_bounds(
                get_uuid(LayoutElements.DECKGLMAP_RIGHT)
            ),
            "data",
        ),
        Input(right_view(LayoutElements.SELECTED_DATA), "data"),
    )
    def _update_property_map_right(
        surface_selected_data: dict,
    ) -> Tuple[str, List[float], List[float]]:
        selected_surface = SurfaceContext(**surface_selected_data)
        ensemble = selected_surface.ensemble
        surface = surface_set_models[ensemble].get_surface(selected_surface)
        return (
            url_for("_send_surface_as_png", surface_context=selected_surface),
            get_surface_range(surface),
            get_surface_bounds(surface),
        )

    @callback(
        Output(right_view(LayoutElements.COLORMAP_RANGE), "min"),
        Output(right_view(LayoutElements.COLORMAP_RANGE), "max"),
        Output(right_view(LayoutElements.COLORMAP_RANGE), "step"),
        Output(right_view(LayoutElements.COLORMAP_RANGE), "value"),
        Output(right_view(LayoutElements.COLORMAP_RANGE), "marks"),
        Output(right_view(LayoutElements.COLORMAP_RANGE), "style"),
        Input(
            DeckGLMapAIO.ids.propertymap_range(
                get_uuid(LayoutElements.DECKGLMAP_RIGHT)
            ),
            "data",
        ),
        Input(right_view(LayoutElements.COLORMAP_KEEP_RANGE), "value"),
        Input(right_view(LayoutElements.COLORMAP_RESET_RANGE), "n_clicks"),
        Input(get_uuid(LayoutElements.LINK_COLORMAP_RANGE), "value"),
        Input(left_view(LayoutElements.COLORMAP_RANGE), "min"),
        Input(left_view(LayoutElements.COLORMAP_RANGE), "max"),
        Input(left_view(LayoutElements.COLORMAP_RANGE), "step"),
        Input(left_view(LayoutElements.COLORMAP_RANGE), "value"),
        Input(left_view(LayoutElements.COLORMAP_RANGE), "marks"),
        State(right_view(LayoutElements.COLORMAP_RANGE), "value"),
    )
    def _update_colormap_range_slider_right(
        value_range: List[float],
        keep: str,
        reset: int,
        link: bool,
        view1_min: float,
        view1_max: float,
        view1_step: float,
        view1_value: List[float],
        view1_marks: Dict,
        current_val: List[float],
    ) -> Tuple[float, float, float, List[float], dict, dict]:
        ctx = callback_context.triggered[0]["prop_id"]
        min_val = value_range[0]
        max_val = value_range[1]
        if ctx == ".":
            value = no_update
        if link:
            return (
                view1_min,
                view1_max,
                view1_step,
                view1_value,
                view1_marks,
                disabled_style,
            )
        if (
            LayoutElements.COLORMAP_RESET_RANGE in ctx
            or not keep
            or current_val is None
        ):
            value = [min_val, max_val]
        else:
            value = current_val
        return (
            min_val,
            max_val,
            calculate_slider_step(min_value=min_val, max_value=max_val, steps=100)
            if min_val != max_val
            else 0,
            value,
            {
                str(min_val): {"label": f"{min_val:.2f}"},
                str(max_val): {"label": f"{max_val:.2f}"},
            },
            {},
        )

    @callback(
        Output(right_view(LayoutElements.COLORMAP_KEEP_RANGE), "style"),
        Output(right_view(LayoutElements.COLORMAP_RESET_RANGE), "style"),
        Input(get_uuid(LayoutElements.LINK_COLORMAP_RANGE), "value"),
    )
    def _update_keep_range_style(link: bool) -> Tuple[dict, dict]:
        if link:
            return disabled_style, disabled_style
        return {}, {}

    @callback(
        Output(
            DeckGLMapAIO.ids.colormap_image(get_uuid(LayoutElements.DECKGLMAP_RIGHT)),
            "data",
        ),
        Input(right_view(LayoutElements.COLORMAP_SELECT), "value"),
    )
    def _update_color_map_right(colormap: str) -> str:
        return f"/colormaps/{colormap}.png"

    @callback(
        Output(
            DeckGLMapAIO.ids.colormap_range(get_uuid(LayoutElements.DECKGLMAP_RIGHT)),
            "data",
        ),
        Input(right_view(LayoutElements.COLORMAP_RANGE), "value"),
    )
    def _update_colormap_range_right(colormap_range: List[float]) -> List[float]:
        return colormap_range
