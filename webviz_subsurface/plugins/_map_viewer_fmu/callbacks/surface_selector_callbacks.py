from typing import List, Dict, Optional

from dataclasses import asdict
from dash import callback, Input, Output, State
from dash.exceptions import PreventUpdate

from webviz_subsurface._models import SurfaceSetModel
from ..utils.formatting import format_date
from ..classes.surface_context import SurfaceContext
from ..classes.surface_mode import SurfaceMode
from ..layout.surface_selector_view import SurfaceSelectorID


def surface_selector_callbacks(get_uuid, surface_set_models: List[SurfaceSetModel]):
    @callback(
        Output(get_uuid(SurfaceSelectorID.ATTRIBUTE.value), "options"),
        Output(get_uuid(SurfaceSelectorID.ATTRIBUTE.value), "value"),
        Input(get_uuid(SurfaceSelectorID.ENSEMBLE.value), "value"),
        State(get_uuid(SurfaceSelectorID.ATTRIBUTE.value), "value"),
    )
    def _update_attribute(ensemble: str, current_attr: str):
        if surface_set_models.get(ensemble) is None:
            raise PreventUpdate
        available_attrs = surface_set_models[ensemble].attributes
        attr = current_attr if current_attr in available_attrs else available_attrs[0]
        options = [{"label": val, "value": val} for val in available_attrs]
        return options, attr

    @callback(
        Output(get_uuid(SurfaceSelectorID.REALIZATIONS.value), "options"),
        Output(get_uuid(SurfaceSelectorID.REALIZATIONS.value), "value"),
        Output(get_uuid(SurfaceSelectorID.REALIZATIONS.value), "multi"),
        Input(get_uuid(SurfaceSelectorID.ENSEMBLE.value), "value"),
        Input(get_uuid(SurfaceSelectorID.MODE.value), "value"),
        State(get_uuid(SurfaceSelectorID.REALIZATIONS.value), "value"),
    )
    def _update_real(
        ensemble: str,
        mode: str,
        current_reals: str,
    ):
        if surface_set_models.get(ensemble) is None or current_reals is None:
            raise PreventUpdate
        available_reals = surface_set_models[ensemble].realizations
        if not isinstance(current_reals, list):
            current_reals = [current_reals]
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
        Output(get_uuid(SurfaceSelectorID.DATE.value), "options"),
        Output(get_uuid(SurfaceSelectorID.DATE.value), "value"),
        Input(get_uuid(SurfaceSelectorID.ATTRIBUTE.value), "value"),
        State(get_uuid(SurfaceSelectorID.DATE.value), "value"),
        State(get_uuid(SurfaceSelectorID.ENSEMBLE.value), "value"),
    )
    def _update_date(attribute: str, current_date: str, ensemble):
        if not isinstance(attribute, list):
            attribute = [attribute]
        available_dates = surface_set_models[ensemble].dates_in_attribute(attribute[0])
        if available_dates is None:
            return None, None
        date = current_date if current_date in available_dates else available_dates[0]
        options = [{"label": format_date(val), "value": val} for val in available_dates]
        return options, date

    @callback(
        Output(get_uuid(SurfaceSelectorID.NAME.value), "options"),
        Output(get_uuid(SurfaceSelectorID.NAME.value), "value"),
        Input(get_uuid(SurfaceSelectorID.ATTRIBUTE.value), "value"),
        State(get_uuid(SurfaceSelectorID.NAME.value), "value"),
        State(get_uuid(SurfaceSelectorID.ENSEMBLE.value), "value"),
    )
    def _update_name(attribute: str, current_name: str, ensemble):
        if not isinstance(attribute, list):
            attribute = [attribute]
        available_names = surface_set_models[ensemble].names_in_attribute(attribute[0])
        name = current_name if current_name in available_names else available_names[0]
        options = [{"label": val, "value": val} for val in available_names]
        return options, name

    @callback(
        Output(get_uuid(SurfaceSelectorID.SELECTED_DATA.value), "data"),
        Input(get_uuid(SurfaceSelectorID.ATTRIBUTE.value), "value"),
        Input(get_uuid(SurfaceSelectorID.NAME.value), "value"),
        Input(get_uuid(SurfaceSelectorID.DATE.value), "value"),
        Input(get_uuid(SurfaceSelectorID.ENSEMBLE.value), "value"),
        Input(get_uuid(SurfaceSelectorID.REALIZATIONS.value), "value"),
        Input(get_uuid(SurfaceSelectorID.MODE.value), "value"),
    )
    def _update_stored_data(
        attribute: str,
        name: str,
        date: str,
        ensemble: str,
        realizations: List[str],
        mode: str,
    ):
        surface_spec = SurfaceContext(
            attribute=attribute,
            name=name,
            date=date,
            ensemble=ensemble,
            realizations=realizations,
            mode=SurfaceMode(mode),
        )

        return asdict(surface_spec)
