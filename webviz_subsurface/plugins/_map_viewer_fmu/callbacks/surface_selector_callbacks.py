from typing import List, Dict, Optional

from dataclasses import asdict
from dash import callback, Input, Output, State, no_update
from dash.exceptions import PreventUpdate

from ..models.surface_set_model import SurfaceSetModel, SurfaceContext, SurfaceMode
from ..utils.formatting import format_date
from ..layout.data_selector_view import SurfaceSelectorID, SurfaceLinkID


def surface_selector_callbacks(get_uuid, surface_set_models: List[SurfaceSetModel]):
    disabled_style = {"opacity": 0.5, "pointerEvents": "none"}

    @callback(
        Output(
            {"view": "view1", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "options"
        ),
        Output({"view": "view1", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "value"),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
        State({"view": "view1", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "value"),
    )
    def _update_attribute(ensemble: str, current_attr: str):
        if surface_set_models.get(ensemble) is None:
            raise PreventUpdate
        available_attrs = surface_set_models[ensemble].attributes
        attr = current_attr if current_attr in available_attrs else available_attrs[0]
        options = [{"label": val, "value": val} for val in available_attrs]
        return options, attr

    @callback(
        Output(
            {"view": "view1", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "options"
        ),
        Output(
            {"view": "view1", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "value"
        ),
        Output(
            {"view": "view1", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "multi"
        ),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.MODE)}, "value"),
        State(
            {"view": "view1", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "value"
        ),
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
        Output({"view": "view1", "id": get_uuid(SurfaceSelectorID.DATE)}, "options"),
        Output({"view": "view1", "id": get_uuid(SurfaceSelectorID.DATE)}, "value"),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "value"),
        State({"view": "view1", "id": get_uuid(SurfaceSelectorID.DATE)}, "value"),
        State({"view": "view1", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
    )
    def _update_date(attribute: str, current_date: str, ensemble):

        available_dates = surface_set_models[ensemble].dates_in_attribute(attribute)
        if available_dates is None:
            return None, None
        date = current_date if current_date in available_dates else available_dates[0]
        options = [{"label": format_date(val), "value": val} for val in available_dates]
        return options, date

    @callback(
        Output({"view": "view1", "id": get_uuid(SurfaceSelectorID.NAME)}, "options"),
        Output({"view": "view1", "id": get_uuid(SurfaceSelectorID.NAME)}, "value"),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "value"),
        State({"view": "view1", "id": get_uuid(SurfaceSelectorID.NAME)}, "value"),
        State({"view": "view1", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
    )
    def _update_name(attribute: str, current_name: str, ensemble):

        available_names = surface_set_models[ensemble].names_in_attribute(attribute)
        name = current_name if current_name in available_names else available_names[0]
        options = [{"label": val, "value": val} for val in available_names]
        return options, name

    @callback(
        Output(
            {"view": "view1", "id": get_uuid(SurfaceSelectorID.SELECTED_DATA)}, "data"
        ),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "value"),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.NAME)}, "value"),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.DATE)}, "value"),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
        Input(
            {"view": "view1", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "value"
        ),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.MODE)}, "value"),
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

    @callback(
        Output(
            {"view": "view2", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "options"
        ),
        Output({"view": "view2", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "value"),
        Output({"view": "view2", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "style"),
        Input({"view": "view2", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "value"),
        Input(get_uuid(SurfaceLinkID.ATTRIBUTE), "value"),
        State({"view": "view2", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "value"),
        State(
            {"view": "view1", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "options"
        ),
    )
    def _update_attribute(
        ensemble: str,
        view1_attribute_value: str,
        link: bool,
        current_attr: str,
        view1_attribute_options,
    ):
        if link:
            return (view1_attribute_options, view1_attribute_value, disabled_style)
        if surface_set_models.get(ensemble) is None:
            raise PreventUpdate
        available_attrs = surface_set_models[ensemble].attributes
        attr = current_attr if current_attr in available_attrs else available_attrs[0]
        options = [{"label": val, "value": val} for val in available_attrs]
        print(attr)
        return options, attr, {}

    @callback(
        Output(
            {"view": "view2", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "options"
        ),
        Output(
            {"view": "view2", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "value"
        ),
        Output(
            {"view": "view2", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "multi"
        ),
        Output(
            {"view": "view2", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "style"
        ),
        Input({"view": "view2", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
        Input({"view": "view2", "id": get_uuid(SurfaceSelectorID.MODE)}, "value"),
        Input(
            {"view": "view1", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "value"
        ),
        Input(get_uuid(SurfaceLinkID.REALIZATIONS), "value"),
        State(
            {"view": "view2", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "value"
        ),
        State(
            {"view": "view1", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "options"
        ),
        State(
            {"view": "view1", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "multi"
        ),
    )
    def _update_real(
        ensemble: str,
        mode: str,
        view1_realizations_value,
        link: bool,
        current_reals: str,
        view1_realizations_options,
        view1_realizations_mode,
    ):
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
        return options, reals, multi, {}

    @callback(
        Output({"view": "view2", "id": get_uuid(SurfaceSelectorID.DATE)}, "options"),
        Output({"view": "view2", "id": get_uuid(SurfaceSelectorID.DATE)}, "value"),
        Output({"view": "view2", "id": get_uuid(SurfaceSelectorID.DATE)}, "style"),
        Input({"view": "view2", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "value"),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.DATE)}, "value"),
        Input(get_uuid(SurfaceLinkID.DATE), "value"),
        State({"view": "view2", "id": get_uuid(SurfaceSelectorID.DATE)}, "value"),
        State({"view": "view2", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
        State({"view": "view1", "id": get_uuid(SurfaceSelectorID.DATE)}, "options"),
    )
    def _update_date(
        attribute: str,
        view1_date_value: str,
        link: bool,
        current_date: str,
        ensemble,
        view1_date_options,
    ):
        if link:
            return view1_date_options, view1_date_value, disabled_style

        available_dates = surface_set_models[ensemble].dates_in_attribute(attribute)
        if available_dates is None:
            return None, None, {}
        date = current_date if current_date in available_dates else available_dates[0]
        options = [{"label": format_date(val), "value": val} for val in available_dates]
        return options, date, {}

    @callback(
        Output({"view": "view2", "id": get_uuid(SurfaceSelectorID.NAME)}, "options"),
        Output({"view": "view2", "id": get_uuid(SurfaceSelectorID.NAME)}, "value"),
        Output({"view": "view2", "id": get_uuid(SurfaceSelectorID.NAME)}, "style"),
        Input({"view": "view2", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "value"),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.NAME)}, "value"),
        Input(get_uuid(SurfaceLinkID.NAME), "value"),
        State({"view": "view2", "id": get_uuid(SurfaceSelectorID.NAME)}, "value"),
        State({"view": "view2", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
        State({"view": "view1", "id": get_uuid(SurfaceSelectorID.NAME)}, "options"),
    )
    def _update_name(
        attribute: str,
        view1_name_value: str,
        link: bool,
        current_name: str,
        ensemble: str,
        view1_name_options,
    ):
        if link:
            return view1_name_options, view1_name_value, disabled_style
        print("ATTRIBUTE-----------------------------", attribute)
        available_names = surface_set_models[ensemble].names_in_attribute(attribute)
        name = current_name if current_name in available_names else available_names[0]
        options = [{"label": val, "value": val} for val in available_names]
        return options, name, {}

    @callback(
        Output({"view": "view2", "id": get_uuid(SurfaceSelectorID.MODE)}, "value"),
        Output({"view": "view2", "id": get_uuid(SurfaceSelectorID.MODE)}, "style"),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.MODE)}, "value"),
        Input(get_uuid(SurfaceLinkID.MODE), "value"),
    )
    def _update_mode(view1_mode: str, link: bool):
        if link:
            return view1_mode, disabled_style
        return no_update, {}

    @callback(
        Output({"view": "view2", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
        Output({"view": "view2", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "style"),
        Input({"view": "view1", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
        Input(get_uuid(SurfaceLinkID.ENSEMBLE), "value"),
    )
    def _update_mode(view1_ensemble: str, link: bool):
        if link:
            return view1_ensemble, disabled_style
        return no_update, {}

    @callback(
        Output(
            {"view": "view2", "id": get_uuid(SurfaceSelectorID.SELECTED_DATA)}, "data"
        ),
        Input({"view": "view2", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "value"),
        Input({"view": "view2", "id": get_uuid(SurfaceSelectorID.NAME)}, "value"),
        Input({"view": "view2", "id": get_uuid(SurfaceSelectorID.DATE)}, "value"),
        Input({"view": "view2", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
        Input(
            {"view": "view2", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "value"
        ),
        Input({"view": "view2", "id": get_uuid(SurfaceSelectorID.MODE)}, "value"),
        State(get_uuid(SurfaceLinkID.ATTRIBUTE), "value"),
        State(get_uuid(SurfaceLinkID.NAME), "value"),
        State(get_uuid(SurfaceLinkID.DATE), "value"),
        State(get_uuid(SurfaceLinkID.ENSEMBLE), "value"),
        State(get_uuid(SurfaceLinkID.REALIZATIONS), "value"),
        State(get_uuid(SurfaceLinkID.MODE), "value"),
        State({"view": "view1", "id": get_uuid(SurfaceSelectorID.ATTRIBUTE)}, "value"),
        State({"view": "view1", "id": get_uuid(SurfaceSelectorID.NAME)}, "value"),
        State({"view": "view1", "id": get_uuid(SurfaceSelectorID.DATE)}, "value"),
        State({"view": "view1", "id": get_uuid(SurfaceSelectorID.ENSEMBLE)}, "value"),
        State(
            {"view": "view1", "id": get_uuid(SurfaceSelectorID.REALIZATIONS)}, "value"
        ),
        State({"view": "view1", "id": get_uuid(SurfaceSelectorID.MODE)}, "value"),
    )
    def _update_stored_data(
        attribute: str,
        name: str,
        date: str,
        ensemble: str,
        realizations: List[str],
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
        view1_realizations: List[str],
        view1_mode: str,
    ):
        print(linked_attribute, linked_name, linked_date)
        if attribute:
            attribute = attribute[0] if isinstance(attribute, list) else attribute
        if name:
            name = name[0] if isinstance(name, list) else name
        if date:
            date = date[0] if isinstance(date, list) else date
        print(attribute, linked_attribute, view1_attribute)
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
