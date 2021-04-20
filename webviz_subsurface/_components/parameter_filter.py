from typing import List, Dict, Optional
import warnings

import numpy as np
import pandas as pd
import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import dash_daq
import webviz_core_components as wcc
import dash_bootstrap_components as dbc
from webviz_config.utils import calculate_slider_step


class ParameterFilter:
    """Component that can be added to a plugin to filter parameters"""

    def __init__(self, app: dash.Dash, uuid: str, dframe: pd.DataFrame) -> None:
        """
        * **`app`:** The Dash app instance.
        * **`uuid`:** Unique id (use the plugin id).
        * **`dframe`:** Dataframe, of all parameter values in all ensembles"""
        self.app = app
        self._uuid = uuid
        self._dframe = dframe
        self._validate_dframe()
        self.set_callbacks(app)

    def _validate_dframe(self) -> None:
        for col in ["REAL", "ENSEMBLE"]:
            if col not in self._dframe.columns:
                raise KeyError(f"Required columns {col} not found in dataframe")

    @property
    def is_sensitivity_run(self):
        if "SENSCASE" and "SENSNAME" in self._dframe.columns:
            return True
        return False

    @property
    def _constant_parameters(self) -> List[str]:
        return [
            col
            for col in self._dframe.columns[self._dframe.nunique() <= 1]
            if col not in ["REAL", "ENSEMBLE"]
        ]

    @property
    def _range_parameters(self) -> List[str]:
        numeric_df = self._dframe.select_dtypes(include=np.number)
        return [
            col
            for col in numeric_df.columns[numeric_df.nunique() >= 10]
            if col not in ["REAL", "ENSEMBLE"]
        ]

    @property
    def _discrete_parameters(self) -> List[str]:
        return [
            col
            for col in self._dframe.columns
            if col
            not in ["REAL", "ENSEMBLE"]
            + self._constant_parameters
            + self._range_parameters
            + ["SENSNAME", "SENSCASE"]
        ]

    @property
    def _range_sliders(self) -> html.Div:
        return html.Div(
            children=[
                make_range_slider(values=self._dframe[col], name=col, uuid=self._uuid)
                for col in self._range_parameters
            ]
        )

    @property
    def _discrete_selectors(self) -> html.Div:
        return html.Div(
            children=[
                make_discrete_selector(
                    values=self._dframe[col], name=col, uuid=self._uuid
                )
                for col in self._discrete_parameters
            ]
        )

    @property
    def layout(self) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    style={"fontSize": "0.8em", "height": "80vh", "overflowY": "auto"},
                    children=[self._range_sliders, self._discrete_selectors],
                ),
                self.buttons,
                dcc.Store(id={"id": self._uuid, "type": "data-store"}),
            ]
        )

    @property
    def buttons(self) -> html.Div:
        return html.Div(
            children=[
                dbc.Button(
                    "Reset",
                    style={"padding": "0 20px"},
                    className="mr-1",
                    id={"id": self._uuid, "type": "button", "element": "reset"},
                ),
                dbc.Button(
                    "Apply",
                    # style={"padding": "0 20px", "visibility": "hidden"}
                    # if apply_disabled
                    style={"padding": "0 20px"},
                    className="mr-1",
                    id={"id": self._uuid, "type": "button", "element": "apply"},
                ),
            ]
        )

    def set_callbacks(self, app) -> None:
        @app.callback(
            Output({"id": self._uuid, "type": "data-store"}, "data"),
            Input({"id": self._uuid, "type": "button", "element": "apply"}, "n_clicks"),
            State({"id": self._uuid, "type": "range-slider", "name": ALL}, "value"),
            State({"id": self._uuid, "type": "select", "name": ALL}, "value"),
        )
        def store_selections(n_clicks, range_sliders, selects) -> Dict:
            if not n_clicks:
                raise PreventUpdate

            dframe = self._dframe
            real_dict = {}
            for values, name in zip(range_sliders, self._range_parameters):
                dframe = dframe[
                    (dframe[name] >= values[0]) & (dframe[name] <= values[1])
                ]
            for values, name in zip(selects, self._discrete_parameters):
                dframe = dframe[dframe[name].isin(values)]
            for ens, ens_df in dframe.groupby("ENSEMBLE"):
                real_dict[ens] = list(ens_df["REAL"].unique())
            return real_dict

        @app.callback(
            Output({"id": self._uuid, "type": "range-slider", "name": ALL}, "value"),
            Output({"id": self._uuid, "type": "select", "name": ALL}, "value"),
            Output(
                {"id": self._uuid, "type": "button", "element": "apply"}, "n_clicks"
            ),
            Input({"id": self._uuid, "type": "button", "element": "reset"}, "n_clicks"),
            State({"id": self._uuid, "type": "button", "element": "apply"}, "n_clicks"),
        )
        def reset_selections(n_clicks, apply_click) -> Dict:
            if not n_clicks:
                raise PreventUpdate
            range_sliders = [
                [self._dframe[col].min(), self._dframe[col].max()]
                for col in self._range_parameters
            ]
            selects = [
                sorted(list(self._dframe[col].unique()))
                for col in self._discrete_parameters
            ]
            return range_sliders, selects, apply_click


def make_range_slider(values: pd.Series, name: str, uuid: str) -> html.Div:
    return html.Div(
        children=[
            html.Label(style={"textAlign": "center"}, children=name),
            dcc.RangeSlider(
                id={"id": uuid, "type": "range-slider", "name": name},
                min=values.min(),
                max=values.max(),
                step=calculate_slider_step(
                    min_value=values.min(),
                    max_value=values.max(),
                    steps=len(list(values.unique())) - 1,
                ),
                value=[values.min(), values.max()],
                marks={
                    str(values.min()): {"label": f"{values.min():.2f}"},
                    str(values.max()): {"label": f"{values.max():.2f}"},
                },
                tooltip={"always_visible": False},
            ),
        ]
    )


def make_discrete_selector(values: pd.Series, name: str, uuid: str) -> html.Div:
    return html.Div(
        children=[
            html.Label(style={"textAlign": "center"}, children=name),
            wcc.Select(
                id={"id": uuid, "type": "select", "name": name},
                options=[{"label": val, "value": val} for val in values.unique()],
                value=sorted(list(values.unique())),
                multi=True,
            ),
        ]
    )