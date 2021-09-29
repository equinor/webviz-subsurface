from typing import Dict, List, Tuple

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import webviz_core_components as wcc
from dash import ALL, Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
from webviz_config.utils import calculate_slider_step


class ParameterFilter:
    """Component that can be added to a plugin to filter parameters"""

    def __init__(self, app: Dash, uuid: str, dframe: pd.DataFrame) -> None:
        """
        * **`app`:** The Dash app instance.
        * **`uuid`:** Unique id (use the plugin id).
        * **`dframe`:** Dataframe, of all parameter values in all ensembles"""
        self.app = app
        self._uuid = uuid
        self._dframe = dframe
        self._validate_dframe()
        self._prepare_data()
        self.set_callbacks(app)

    def _validate_dframe(self) -> None:
        for col in ["REAL", "ENSEMBLE"]:
            if col not in self._dframe.columns:
                raise KeyError(f"Required columns {col} not found in dataframe")

    def _prepare_data(self, drop_constants: bool = True) -> None:
        """
        Different data preparations on the parameters, before storing them as an attribute.
        Option to drop parameters with constant values. Prefixes on parameters from GEN_KW
        are removed, in addition parameters with LOG distribution will be kept while the
        other is dropped.
        """

        if drop_constants:
            constant_params = [
                param
                for param in [
                    x for x in self._dframe.columns if x not in ["REAL", "ENSEMBLE"]
                ]
                if len(self._dframe[param].unique()) == 1
            ]
            self._dframe = self._dframe.drop(columns=constant_params)

        # Keep only LOG parameters
        log_params = [
            param.replace("LOG10_", "")
            for param in [
                x for x in self._dframe.columns if x not in ["REAL", "ENSEMBLE"]
            ]
            if param.startswith("LOG10_")
        ]
        self._dframe = self._dframe.drop(columns=log_params)
        self._dframe = self._dframe.rename(
            columns={
                col: f"{col} (log)"
                for col in self._dframe.columns
                if col.startswith("LOG10_")
            }
        )
        # Remove prefix on parameter name added by GEN_KW
        self._dframe = self._dframe.rename(
            columns={
                col: (col.split(":", 1)[1])
                for col in self._dframe.columns
                if (":" in col and col not in ["REAL", "ENSEMBLE"])
            }
        )
        # Drop columns if duplicate names
        self._dframe = self._dframe.loc[:, ~self._dframe.columns.duplicated()]

    @property
    def _ensembles(self) -> List[str]:
        return list(self._dframe["ENSEMBLE"].unique())

    @property
    def is_sensitivity_run(self) -> bool:
        return "SENSCASE" in self._dframe.columns and "SENSNAME" in self._dframe.columns

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
            style={"height": "100%"},
            children=[
                html.Div(
                    style={"height": "90%"},
                    children=[
                        wcc.Header(
                            style={"color": "black"},
                            children="Parameter filter",
                        ),
                        html.Div(
                            style={"overflowY": "auto", "height": "90%"},
                            children=[self._range_sliders, self._discrete_selectors],
                        ),
                    ],
                ),
                self.buttons,
                dcc.Store(
                    id={"id": self._uuid, "type": "data-store"},
                    data=self._initial_store,
                ),
            ],
        )

    @property
    def _initial_store(self) -> Dict[str, List]:
        data = {}
        for ens_name, ens_df in self._dframe.groupby("ENSEMBLE"):
            data[ens_name] = sorted(list(ens_df["REAL"].unique()))
        return data

    @property
    def buttons(self) -> html.Div:
        return html.Div(
            style={"marginTop": "20px"},
            children=[
                dbc.Button(
                    "Reset",
                    style={
                        "width": "48%",
                        "float": "right",
                        "background-color": "white",
                    },
                    className="mr-1",
                    id={"id": self._uuid, "type": "button", "element": "reset"},
                ),
                dbc.Button(
                    "Apply",
                    # style={"padding": "0 20px", "visibility": "hidden"}
                    # if apply_disabled
                    style={
                        "width": "48%",
                        "float": "left",
                        "background-color": "white",
                    },
                    className="mr-1",
                    id={"id": self._uuid, "type": "button", "element": "apply"},
                ),
            ],
        )

    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output({"id": self._uuid, "type": "data-store"}, "data"),
            Input({"id": self._uuid, "type": "button", "element": "apply"}, "n_clicks"),
            State({"id": self._uuid, "type": "range-slider", "name": ALL}, "value"),
            State({"id": self._uuid, "type": "select", "name": ALL}, "value"),
        )
        def store_selections(n_clicks: int, range_sliders: list, selects: list) -> Dict:
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

            for ens in self._ensembles:
                if ens not in real_dict.keys():
                    real_dict[ens] = []
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
        def reset_selections(n_clicks: int, apply_click: int) -> Tuple[List, List, int]:
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
    return wcc.RangeSlider(
        label=name,
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
    )


def make_discrete_selector(values: pd.Series, name: str, uuid: str) -> html.Div:
    return wcc.SelectWithLabel(
        label=name,
        id={"id": uuid, "type": "select", "name": name},
        options=[{"label": val, "value": val} for val in values.unique()],
        value=sorted(list(values.unique())),
        multi=True,
    )
