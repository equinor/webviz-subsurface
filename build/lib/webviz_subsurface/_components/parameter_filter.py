from typing import Dict, List, Tuple, Union
from uuid import uuid4

import numpy as np
import pandas as pd
import webviz_core_components as wcc
from dash import (
    ALL,
    Input,
    Output,
    State,
    callback,
    callback_context,
    dcc,
    html,
    no_update,
)
from dash.exceptions import PreventUpdate

from webviz_subsurface._models.parameter_model import ParametersModel
from webviz_subsurface._utils.formatting import printable_int_list


class ParameterFilter:
    """Component that can be added to a plugin to filter parameters"""

    def __init__(
        self,
        uuid: str,
        dframe: pd.DataFrame,
        reset_on_ensemble_update: bool = False,
        display_header: bool = True,
    ) -> None:
        """
        * **`uuid`:** Unique id (use the plugin id).
        * **`dframe`:** Dataframe, of all parameter values in all ensembles"""

        self._uuid = uuid
        self._reset_on_ensemble_update = reset_on_ensemble_update
        self._display_header = display_header
        self._pmodel = ParametersModel(
            dataframe=dframe,
            drop_constants=True,
            keep_numeric_only=False,
            drop_parameters_with_nan=True,
        )
        self._dframe = self._pmodel.dataframe
        self._range_parameters = self._get_range_parameters()
        self._column_precisions = self._get_column_precisions()
        self._dframe = self._dframe.round(self._column_precisions)
        self._discrete_parameters = self._get_discrete_parameters()
        self._min_max_ranges_per_ensemble = self._get_min_max_ranges_per_ensemble()
        self._min_max_all = self._return_min_max_ranges(self._ensembles)
        self.set_callbacks()

    @property
    def _ensembles(self) -> List[str]:
        return self._pmodel.ensembles

    @property
    def _realizations_per_ensemble(self) -> Dict[str, list]:
        return {
            ens: list(self._dframe[self._dframe["ENSEMBLE"] == ens]["REAL"].unique())
            for ens in self._ensembles
        }

    @property
    def is_sensitivity_run(self) -> bool:
        return self._pmodel.sensrun

    @property
    def _settings_visible(self) -> bool:
        return len(self._ensembles) > 1

    @property
    def _viewheight_parameters(self) -> str:
        return "60vh" if self._settings_visible else "75vh"

    @property
    def _parameters_per_ensemble(self) -> Dict[str, List]:
        return self._pmodel.parameters_per_ensemble

    @staticmethod
    def _precision(number: float) -> int:
        if abs(number) <= 0.01:
            return 6
        if abs(number) <= 1:
            return 3
        return 1

    def _get_range_parameters(self) -> List[str]:
        numeric_df = self._dframe.select_dtypes(include=np.number)
        return [
            col
            for col in numeric_df.columns[numeric_df.nunique() >= 6]
            if col not in self._pmodel.selectors
        ]

    def _get_discrete_parameters(self) -> List[str]:
        return [
            col
            for col in self._dframe.columns
            if col not in self._pmodel.selectors + self._range_parameters
        ]

    def _get_column_precisions(self) -> Dict[str, int]:
        return {
            col: self._precision(np.nanmin(self._dframe[col]))
            for col in self._range_parameters
        }

    def _get_min_max_ranges_per_ensemble(self) -> Dict[str, Dict[str, list]]:
        min_max_ranges = {}
        for ens in self._ensembles:
            dframe = self._dframe[self._dframe["ENSEMBLE"] == ens]
            parameters = self._parameters_per_ensemble[ens]
            min_max_ranges[ens] = {
                col: [dframe[col].min(), dframe[col].max()] for col in parameters
            }
        return min_max_ranges

    def _return_min_max_ranges(self, ensembles: list) -> Dict[str, list]:
        ranges = [self._min_max_ranges_per_ensemble[ens] for ens in ensembles]
        parameters = self._pmodel.get_parameters_for_ensembles(ensembles)
        return {
            col: [
                min(ens_ranges[col][0] for ens_ranges in ranges if col in ens_ranges),
                max(ens_ranges[col][1] for ens_ranges in ranges if col in ens_ranges),
            ]
            for col in parameters
        }

    def _missing_reals_in_ensemble(self, ensemble: str, reals: list) -> list:
        return [x for x in self._realizations_per_ensemble[ensemble] if x not in reals]

    @staticmethod
    def _get_values(
        sliders: list, selects: list, slider_id: list, select_id: list
    ) -> dict:
        values = {idv["name"]: val for val, idv in zip(sliders, slider_id)}
        values.update({idv["name"]: val for val, idv in zip(selects, select_id)})
        return values

    @property
    def layout(self) -> html.Div:
        children = [
            self.buttons,
            self.settings_layout,
            self.realizations_removed_layout,
            self.active_filters_layout,
            self.parameter_filter_layout,
        ]

        if self._display_header:
            children = [self.header] + children

        return html.Div(
            children=[
                html.Div(children=children),
                dcc.Store(
                    id={"id": self._uuid, "type": "data-store"},
                    data=self._initial_store,
                ),
                dcc.Store(id={"id": self._uuid, "type": "value-store"}, data={}),
                dcc.Store(id={"id": self._uuid, "type": "ensemble-update"}),
            ],
        )

    @property
    def _initial_store(self) -> Dict[str, List]:
        data = {}
        for ens_name, ens_df in self._dframe.groupby("ENSEMBLE"):
            data[ens_name] = sorted(list(ens_df["REAL"].unique()))
        return data

    @property
    def active_filters_layout(self) -> html.Details:
        return html.Details(
            className="webviz-selectors",
            children=[
                html.Summary(
                    "Active Filters",
                    className="webviz-underlined-label",
                    id={"id": self._uuid, "type": "filter-active-label"},
                ),
                html.Div(
                    style={"padding": "10px", "font-size": "15px"},
                    id={"id": self._uuid, "type": "filter-active-wrapper"},
                ),
            ],
        )

    @property
    def realizations_removed_layout(self) -> wcc.Selectors:
        return wcc.Selectors(
            label="Realizations removed",
            open_details=False,
            children=html.Div(id={"id": self._uuid, "type": "real-active-wrapper"}),
            style={"font-size": "15px"},
        )

    @property
    def parameter_filter_layout(self) -> wcc.Selectors:
        return wcc.Selectors(
            label="Parameters",
            children=html.Div(
                id={"id": self._uuid, "type": "filter-wrapper"},
                style={"overflowY": "auto", "height": self._viewheight_parameters},
            ),
        )

    @property
    def settings_layout(self) -> html.Div:
        return html.Div(
            wcc.Selectors(
                label="Settings",
                children=html.Div(
                    style={
                        "marginBottom": "5px",
                        "backgroundColor": "white",
                        "border": "1px solid #bbb",
                        "border-radius": "4px",
                        "padding": "5px",
                    },
                    children=[
                        wcc.Checklist(
                            id={"id": self._uuid, "type": "ensemble-selector"},
                            label="Filter Ensembles:",
                            options=[
                                {"label": val, "value": val} for val in self._ensembles
                            ],
                            value=self._ensembles,
                            vertical=False,
                        ),
                        wcc.RadioItems(
                            id={"id": self._uuid, "type": "range-selector"},
                            label="Use ranges from:",
                            options=[
                                {"label": "Selected", "value": "selected"},
                                {"label": "All", "value": "all"},
                            ],
                            value="selected",
                            vertical=False,
                        ),
                    ],
                ),
            ),
            style={"display": "block" if self._settings_visible else "none"},
        )

    @property
    def header(self) -> wcc.Header:
        return wcc.Header(
            "Parameter filter",
            style={"color": "black", "marginBottom": "15px", "borderColor": "black"},
        )

    @property
    def buttons(self) -> html.Div:
        button_style = {
            "height": "30px",
            "line-height": "30px",
            "background-color": "white",
        }
        return html.Div(
            style={"marginTop": "10px", "height": "35px"},
            children=[
                html.Button(
                    "Reset",
                    style={"width": "48%", "float": "right", **button_style},
                    id={"id": self._uuid, "type": "reset-button"},
                ),
                html.Button(
                    "Apply",
                    style={"width": "48%", "float": "left", **button_style},
                    id={"id": self._uuid, "type": "apply-button"},
                ),
            ],
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self) -> None:
        @callback(
            Output({"id": self._uuid, "type": "data-store"}, "data"),
            Output({"id": self._uuid, "type": "value-store"}, "data"),
            Input({"id": self._uuid, "type": "apply-button"}, "n_clicks"),
            State({"id": self._uuid, "type": "ensemble-selector"}, "value"),
            State({"id": self._uuid, "type": "slider", "name": ALL, "r": ALL}, "value"),
            State({"id": self._uuid, "type": "select", "name": ALL, "r": ALL}, "value"),
            State({"id": self._uuid, "type": "data-store"}, "data"),
            State({"id": self._uuid, "type": "slider", "name": ALL, "r": ALL}, "id"),
            State({"id": self._uuid, "type": "select", "name": ALL, "r": ALL}, "id"),
        )
        def store_selections(
            n_clicks: int,
            ensembles: list,
            sliders: list,
            selects: list,
            data_store: dict,
            slider_id: List[dict],
            select_id: List[dict],
        ) -> tuple:
            if not n_clicks:
                raise PreventUpdate

            values = self._get_values(sliders, selects, slider_id, select_id)

            real_dict = {}
            for ens, ens_df in self._dframe.groupby("ENSEMBLE"):
                if ens in ensembles:
                    for col in self._parameters_per_ensemble[ens]:
                        if col in self._range_parameters:
                            ens_df = ens_df[
                                (ens_df[col] >= values[col][0])
                                & (ens_df[col] <= values[col][1])
                            ]
                        else:
                            ens_df = ens_df[ens_df[col].isin(values[col])]

                real_dict[ens] = list(ens_df["REAL"].unique())

            # only update data_store if realization filter has changed
            update_data_store = any(
                real_dict[ens] != data_store[ens] for ens in self._ensembles
            )
            return real_dict if update_data_store else no_update, values

        @callback(
            Output({"id": self._uuid, "type": "filter-wrapper"}, "children"),
            Output({"id": self._uuid, "type": "apply-button"}, "n_clicks"),
            Input({"id": self._uuid, "type": "reset-button"}, "n_clicks"),
            Input({"id": self._uuid, "type": "range-selector"}, "value"),
            Input({"id": self._uuid, "type": "ensemble-selector"}, "value"),
            State({"id": self._uuid, "type": "slider", "name": ALL, "r": ALL}, "value"),
            State({"id": self._uuid, "type": "slider", "name": ALL, "r": ALL}, "id"),
            State({"id": self._uuid, "type": "select", "name": ALL, "r": ALL}, "value"),
            State({"id": self._uuid, "type": "select", "name": ALL, "r": ALL}, "id"),
        )
        # pylint: disable=too-many-locals
        def update_filtercomponents_and_apply(
            _reset_click: int,
            range_from: str,
            ensembles: list,
            sliders: list,
            slider_id: List[dict],
            selects: list,
            select_id: List[dict],
        ) -> Tuple[list, int]:
            ctx = callback_context.triggered[0]["prop_id"]
            if not ensembles:
                raise PreventUpdate

            reset = (
                self._reset_on_ensemble_update and "ensemble-selector" in ctx
            ) or "reset" in ctx
            if not reset and (range_from == "all" and "ensemble-selector" in ctx):
                return no_update, 1

            values = self._get_values(sliders, selects, slider_id, select_id)
            min_max_range = self._return_min_max_ranges(ensembles)
            ens_df = self._dframe[self._dframe["ENSEMBLE"].isin(ensembles)]

            children = []
            for col in self._pmodel.get_parameters_for_ensembles(ensembles):
                if col in self._range_parameters:
                    children.append(
                        make_range_slider(
                            min_max=(
                                self._min_max_all[col]
                                if range_from == "all"
                                else min_max_range[col]
                            ),
                            value=min_max_range[col]
                            if reset or col not in values
                            else values[col],
                            name=col,
                            uuid=self._uuid,
                            step=10 ** -self._column_precisions[col],
                        )
                    )

                else:
                    df = self._dframe if range_from == "all" else ens_df
                    unique_values = list(df[col].dropna().unique())
                    value = (
                        list(ens_df[col].dropna().unique())
                        if reset or col not in values
                        else [x for x in values[col] if x in unique_values]
                    )
                    children.append(
                        make_discrete_selector(
                            value=value if value else unique_values,
                            options=unique_values,
                            name=col,
                            uuid=self._uuid,
                        )
                    )

            return children, 1 if not "range-selector" in ctx else no_update

        @callback(
            Output({"id": self._uuid, "type": "real-active-wrapper"}, "children"),
            Input({"id": self._uuid, "type": "value-store"}, "data"),
            State({"id": self._uuid, "type": "data-store"}, "data"),
        )
        def _update_missing_real_text(_value_store: list, data_store: dict) -> list:
            return [
                html.Div(
                    [
                        html.Span(f"{ens}:  ", style={"font-weight": "bold"}),
                        printable_int_list(self._missing_reals_in_ensemble(ens, reals)),
                    ]
                )
                for ens, reals in data_store.items()
            ]

        @callback(
            Output({"id": self._uuid, "type": "filter-active-label"}, "style"),
            Output({"id": self._uuid, "type": "filter-active-wrapper"}, "children"),
            Input({"id": self._uuid, "type": "value-store"}, "data"),
            State({"id": self._uuid, "type": "ensemble-selector"}, "value"),
            State({"id": self._uuid, "type": "slider", "name": ALL, "r": ALL}, "value"),
            State({"id": self._uuid, "type": "select", "name": ALL, "r": ALL}, "value"),
            State({"id": self._uuid, "type": "slider", "name": ALL, "r": ALL}, "id"),
            State({"id": self._uuid, "type": "select", "name": ALL, "r": ALL}, "id"),
        )
        def _update_active_filter_text(
            _value_store: list,
            ensembles: list,
            sliders: list,
            selects: list,
            slider_id: List[dict],
            select_id: List[dict],
        ) -> Tuple[dict, list]:

            min_max = self._return_min_max_ranges(ensembles)
            df = self._dframe[self._dframe["ENSEMBLE"].isin(ensembles)]
            values = self._get_values(sliders, selects, slider_id, select_id)

            params_active = []
            for col in self._pmodel.get_parameters_for_ensembles(ensembles):
                if col in self._range_parameters:
                    min_val, max_val = values[col]
                    if (min_val > min_max[col][0]) or (max_val < min_max[col][1]):
                        params_active.append(
                            html.Div(f"{col}:", style={"font-weight": "bold"})
                        )
                        params_active.append(html.Div(f"{min_val} - {max_val}"))
                else:
                    unique_values = list(df[col].dropna().unique())
                    if not all(x in values[col] for x in unique_values):
                        params_active.append(html.Div(f"{col}"))

            active_filter_style = (
                {"color": "lightgray", "border-color": "lightgray"}
                if not params_active
                else {}
            )
            return active_filter_style, params_active

        @callback(
            Output({"id": self._uuid, "type": "apply-button"}, "style"),
            Input({"id": self._uuid, "type": "apply-button"}, "n_clicks"),
            Input({"id": self._uuid, "type": "slider", "name": ALL, "r": ALL}, "value"),
            Input({"id": self._uuid, "type": "select", "name": ALL, "r": ALL}, "value"),
            State({"id": self._uuid, "type": "slider", "name": ALL, "r": ALL}, "id"),
            State({"id": self._uuid, "type": "select", "name": ALL, "r": ALL}, "id"),
            State({"id": self._uuid, "type": "value-store"}, "data"),
            State({"id": self._uuid, "type": "apply-button"}, "style"),
        )
        def _update_apply_button_style(
            _n_clicks: int,
            sliders: List[list],
            selects: List[list],
            slider_id: List[dict],
            select_id: List[dict],
            values_stored: Dict[str, list],
            style: dict,
        ) -> dict:

            ctx = callback_context.triggered[0]["prop_id"]
            values = self._get_values(sliders, selects, slider_id, select_id)
            modified_values = any(
                values[col] != values_stored.get(col, values[col]) for col in values
            )

            if modified_values and not "apply-button" in ctx:
                style["background-color"] = "#7393B3"
                style["color"] = "white"
            else:
                style["background-color"] = "white"
                style["color"] = "#555"
            return style

        @callback(
            Output({"id": self._uuid, "type": "ensemble-selector"}, "value"),
            Output({"id": self._uuid, "type": "ensemble-selector"}, "options"),
            Input({"id": self._uuid, "type": "ensemble-update"}, "data"),
            prevent_initial_call=True,
        )
        def _update_ensembles_from_outside(ensembles: list) -> tuple:
            """Update ensemble in parameter filter"""
            return (
                ensembles,
                [
                    {
                        "label": val,
                        "value": val,
                        "disabled": val not in ensembles or len(ensembles) == 1,
                    }
                    for val in self._ensembles
                ],
            )


def make_range_slider(
    value: list, min_max: list, step: float, name: str, uuid: str
) -> html.Div:
    return wcc.RangeSlider(
        label=name,
        id={
            "id": uuid,
            "type": "slider",
            "name": name,
            "r": str(uuid4()),  # needed to trigger update (bug)
        },
        min=min_max[0],
        max=min_max[1],
        step=step,
        value=_validate_slider_value(min_max, value),
        marks={format_marker_value(val): {"label": str(val)} for val in min_max},
        tooltip={"always_visible": False},
    )


def make_discrete_selector(
    value: list, options: list, name: str, uuid: str
) -> html.Div:
    return wcc.SelectWithLabel(
        label=name,
        id={
            "id": uuid,
            "type": "select",
            "name": name,
            "r": str(uuid4()),  # needed to trigger update (bug)
        },
        options=[{"label": val, "value": val} for val in sorted(options)],
        value=value,
        multi=True,
    )


def _validate_slider_value(min_max: list, value: list) -> list:
    min_val, max_val = min_max
    if min_val > value[0]:
        value[0] = min_val
    if max_val < value[0]:
        value[0] = max_val
    if max_val < value[1]:
        value[1] = max_val
    if min_val > value[1]:
        value[1] = min_val
    return value


def format_marker_value(number: Union[float, int]) -> str:
    # In order to show up on the RangeSlider the values used for the marks
    # needs to be without trailing zeros and scientific notification
    number = float(number)
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0")
