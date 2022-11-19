import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from uuid import uuid4

import numpy as np
import pandas as pd
import yaml
from dash import Dash, Input, Output, State, callback_context, dcc, html
from dash.exceptions import PreventUpdate


class SurfaceSelector:
    """### Surface Selector

    Creates a widget to select surfaces from a yaml configuration file or dictionary, and
    a dataframe of ensemble/realizations, optionally with sensitivity cases.
    The current selections are stored in a dcc.Store object that can
    be accessed by the storage_id property of the class instance.

    * `config`: A dictionary / yaml configuration file of surfaces on the format below
    * `ensembles`: A pandas dataframe with ensemble, real(index), runpath, sensname and senscase

    Format of configuration:
    some_property:
        names:
            - surfacename
            - surfacename
        dates:
            - somedate
            - somedate
    another_property:
        names:
            - surfacename
            - surfacename
        dates:
            - somedate
            - somedate"""

    def __init__(
        self, app: Dash, config: Union[str, dict], ensembles: pd.DataFrame
    ) -> None:

        self._configuration = self.read_config(config)
        self._ensembles = ensembles
        self._storage_id = f"{str(uuid4())}-surface-selector"

        self.set_ids()
        self.set_callbacks(app)

    @staticmethod
    def read_config(config: Union[str, dict]) -> dict:
        """Reads config file either from a yaml provided file or from a dict"""
        if isinstance(config, str):
            with open(config, "r") as filehandle:
                return yaml.safe_load(filehandle)

        if isinstance(config, dict):
            return config

        raise TypeError("Config must be a dictionary of a yaml file")

    @property
    def storage_id(self) -> str:
        """The id of the dcc.Store component that holds the selection"""
        return self._storage_id

    def set_ids(self) -> None:
        uuid = str(uuid4())
        self.attr_id = f"{uuid}-attr"
        self.attr_id_btn_prev = f"{uuid}-attr-btn-prev"
        self.attr_id_btn_next = f"{uuid}-attr-btn-next"
        self.name_id = f"{uuid}-name"
        self.name_id_btn_prev = f"{uuid}-name-btn-prev"
        self.name_id_btn_next = f"{uuid}-name-btn-next"
        self.date_id = f"{uuid}-date"
        self.date_id_btn_prev = f"{uuid}-date-btn-prev"
        self.date_id_btn_next = f"{uuid}-date-btn-next"
        self.name_wrapper_id = f"{uuid}-name-wrapper"
        self.date_wrapper_id = f"{uuid}-date-wrapper"

    @property
    def attrs(self) -> List[str]:
        return list(self._configuration.keys())

    def _names_in_attr(self, attr: Optional[str]) -> Optional[List[str]]:
        return self._configuration[attr].get("names", None)

    def _dates_in_attr(self, attr: Optional[str]) -> Optional[List[str]]:
        dates = self._configuration[attr].get("dates", None)
        if dates is not None and dates == [np.nan]:
            return None
        return dates

    @property
    def attribute_selector(self) -> html.Div:
        return html.Div(
            style={"display": "grid"},
            children=[
                html.Label("Surface attribute"),
                html.Div(
                    style=self.set_grid_layout("6fr 1fr"),
                    children=[
                        dcc.Dropdown(
                            id=self.attr_id,
                            options=[
                                {"label": attr, "value": attr} for attr in self.attrs
                            ],
                            value=self.attrs[0],
                            clearable=False,
                            persistence=True,
                            persistence_type="session",
                        ),
                        self._make_buttons(
                            self.attr_id_btn_prev, self.attr_id_btn_next
                        ),
                    ],
                ),
            ],
        )

    def _make_buttons(self, prev_id: str, next_id: str) -> html.Div:
        return html.Div(
            style=self.set_grid_layout("1fr 1fr"),
            children=[
                html.Button(
                    style={
                        "fontSize": "2rem",
                        "paddingLeft": "5px",
                        "paddingRight": "5px",
                    },
                    id=prev_id,
                    children="⬅",
                ),
                html.Button(
                    style={
                        "fontSize": "2rem",
                        "paddingLeft": "5px",
                        "paddingRight": "5px",
                    },
                    id=next_id,
                    children="➡",
                ),
            ],
        )

    def selector(
        self,
        wrapper_id: str,
        dropdown_id: str,
        title: str,
        btn_prev: str,
        btn_next: str,
    ) -> html.Div:
        return html.Div(
            id=wrapper_id,
            style={"display": "none"},
            children=[
                html.Label(title),
                html.Div(
                    style=self.set_grid_layout("6fr 1fr"),
                    children=[
                        dcc.Dropdown(
                            id=dropdown_id,
                            clearable=False,
                            persistence=True,
                            persistence_type="session",
                        ),
                        self._make_buttons(btn_prev, btn_next),
                    ],
                ),
            ],
        )

    @staticmethod
    def set_grid_layout(columns: Union[List[str], str]) -> Dict[str, str]:
        return {"display": "grid", "gridTemplateColumns": f"{columns}"}

    @property
    def layout(self) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    children=[
                        self.attribute_selector,
                        self.selector(
                            self.name_wrapper_id,
                            self.name_id,
                            "Surface name",
                            self.name_id_btn_prev,
                            self.name_id_btn_next,
                        ),
                        self.selector(
                            self.date_wrapper_id,
                            self.date_id,
                            "Date",
                            self.date_id_btn_prev,
                            self.date_id_btn_next,
                        ),
                    ]
                ),
                dcc.Store(id=self.storage_id, storage_type="session"),
            ]
        )

    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(self.attr_id, "value"),
            [
                Input(self.attr_id_btn_prev, "n_clicks"),
                Input(self.attr_id_btn_next, "n_clicks"),
            ],
            [State(self.attr_id, "value")],
        )
        def _update_attr(
            _n_prev: Optional[int], _n_next: Optional[int], current_value: str
        ) -> str:
            ctx = callback_context.triggered
            if ctx is None or not current_value:
                raise PreventUpdate
            if not ctx[0]["value"]:
                return current_value
            callback = ctx[0]["prop_id"]
            if callback == f"{self.attr_id_btn_prev}.n_clicks":
                return prev_value(current_value, self.attrs)
            if callback == f"{self.attr_id_btn_next}.n_clicks":
                return next_value(current_value, self.attrs)
            return ""

        @app.callback(
            [
                Output(self.name_id, "options"),
                Output(self.name_id, "value"),
                Output(self.name_wrapper_id, "style"),
            ],
            [
                Input(self.attr_id, "value"),
                Input(self.name_id_btn_prev, "n_clicks"),
                Input(self.name_id_btn_next, "n_clicks"),
            ],
            [State(self.name_id, "value")],
        )
        def _update_name(
            attr: str,
            _n_prev: Optional[int],
            _n_next: Optional[int],
            current_value: str,
        ) -> Tuple[Optional[List[Dict[str, str]]], Optional[str], Dict[str, str]]:
            ctx = callback_context.triggered
            if ctx is None:
                raise PreventUpdate
            names = self._names_in_attr(attr)
            if not names:
                return None, None, {"visibility": "hidden"}

            callback = ctx[0]["prop_id"]
            if callback == f"{self.name_id_btn_prev}.n_clicks":
                value = prev_value(current_value, names)
            elif callback == f"{self.name_id_btn_next}.n_clicks":
                value = next_value(current_value, names)
            else:
                value = current_value if current_value in names else names[0]
            options = [{"label": name, "value": name} for name in names]
            return options, value, {}

        @app.callback(
            [
                Output(self.date_id, "options"),
                Output(self.date_id, "value"),
                Output(self.date_wrapper_id, "style"),
            ],
            [
                Input(self.attr_id, "value"),
                Input(self.date_id_btn_prev, "n_clicks"),
                Input(self.date_id_btn_next, "n_clicks"),
            ],
            [State(self.date_id, "value")],
        )
        def _update_date(
            attr: str,
            _n_prev: Optional[int],
            _n_next: Optional[int],
            current_value: str,
        ) -> Tuple[List[Dict[str, str]], Optional[str], Dict[str, str]]:
            ctx = callback_context.triggered

            if ctx is None:
                raise PreventUpdate
            dates = self._dates_in_attr(attr)

            if dates is None or dates[0] is None:
                return [], None, {"visibility": "hidden"}

            callback = ctx[0]["prop_id"]
            if callback == f"{self.date_id_btn_prev}.n_clicks":
                value = prev_value(current_value, dates)
            elif callback == f"{self.date_id_btn_next}.n_clicks":
                value = next_value(current_value, dates)
            else:
                value = current_value if current_value in dates else dates[0]
            options = [{"label": format_date(date), "value": date} for date in dates]
            return options, value, {}

        @app.callback(
            Output(self.storage_id, "data"),
            [
                Input(self.attr_id, "value"),
                Input(self.name_id, "value"),
                Input(self.date_id, "value"),
            ],
        )
        def _set_data(
            attr: Optional[str], name: Optional[str], date: Optional[str]
        ) -> str:
            """
            Stores current selections to dcc.Store. The information can
            be retrieved as a json string from a dash callback Input.
            E.g. [Input(surfselector.storage_id, 'children')]
            """

            # Preventing update if selections are not valid (waiting for the other callbacks)
            names_in_attr = self._names_in_attr(attr)
            if names_in_attr and not name in names_in_attr:
                raise PreventUpdate

            dates_in_attr = self._dates_in_attr(attr)

            if dates_in_attr and date and not date in dates_in_attr:
                raise PreventUpdate
            return json.dumps({"name": name, "attribute": attr, "date": date})


def prev_value(current_value: str, options: List[str]) -> str:
    try:
        index = options.index(current_value)
        return options[max(0, index - 1)]
    except ValueError:
        return current_value


def next_value(current_value: str, options: List[str]) -> str:
    try:
        index = options.index(current_value)
        return options[min(len(options) - 1, index + 1)]
    except ValueError:
        return current_value


def format_date(date_string: str) -> str:
    """Reformat date string for presentation
    20010101 => Jan 2001
    20010101_20010601 => (Jan 2001) - (June 2001)
    20010101_20010106 => (01 Jan 2001) - (06 Jan 2001)"""
    date_string = str(date_string)
    if len(date_string) == 8:
        return datetime.strptime(date_string, "%Y%m%d").strftime("%b %Y")

    if len(date_string) == 17:
        [begin, end] = [
            datetime.strptime(date, "%Y%m%d") for date in date_string.split("_")
        ]
        if begin.year == end.year and begin.month == end.month:
            return f"({begin.strftime('%-d %b %Y')})-\
              ({end.strftime('%-d %b %Y')})"

        return f"({begin.strftime('%b %Y')})-({end.strftime('%b %Y')})"

    return date_string
