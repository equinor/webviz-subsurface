from uuid import uuid4
import json

import numpy as np
import pandas as pd
import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State, ALL
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc


class ParameterFilter:
    def __init__(self, app, parameterdf):
        self.parameterdf = parameterdf
        self.parameterdf["REAL"] = self.parameterdf["REAL"].astype(int)
        self.uid = uuid4()
        self.set_callbacks(app)

    def make_parameter_slider_and_id(self):
        """Make a slider widget for each parameter, and register relevant ids"""
        filters = []
        for ens_name, ensdf in self.parameterdf.groupby("ENSEMBLE"):
            ensfilters = []
            for p_name in ensdf.columns:
                if p_name in ["REAL", "ENSEMBLE"]:
                    continue
                elif len(ensdf[p_name].unique()) < 2:
                    continue
                elif (
                    pd.to_numeric(ensdf[p_name], errors="coerce").notnull().all()
                    and len(ensdf[p_name].unique()) > 5
                ):
                    ensfilters.append(
                        make_rangeslider(
                            name=p_name,
                            values=ensdf[p_name],
                            unique_id={
                                "type": self.uuid("range"),
                                "index": p_name,
                                "ensemble": ens_name,
                            },
                        )
                    )
                else:
                    ensfilters.append(
                        make_multiselect(
                            name=p_name,
                            values=list(ensdf[p_name].unique()),
                            unique_id={
                                "type": self.uuid("select"),
                                "index": p_name,
                                "ensemble": ens_name,
                            },
                        )
                    )
            filters.append(
                html.Div(
                    id={"type": self.uuid("wrapper"), "ensemble": ens_name},
                    style={"display": "none"},
                    children=ensfilters,
                )
            )
        return html.Div(children=filters)

    @property
    def storage_id(self):
        return self.uuid("storage")

    @property
    def ensembles(self):
        return list(self.parameterdf["ENSEMBLE"].unique())

    def uuid(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def layout(self):
        return html.Div(
            children=[
                html.H3("Parameter filter"),
                dcc.Dropdown(
                    id=self.uuid("ensemble"),
                    options=[{"label": ens, "value": ens} for ens in self.ensembles],
                    value=self.ensembles[0],
                    clearable=False,
                ),
                self.make_parameter_slider_and_id(),
                dcc.Store(id=self.storage_id),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output({"type": self.uuid("wrapper"), "ensemble": ALL}, "style"),
            [Input(self.uuid("ensemble"), "value")],
        )
        def display_selectors(ens):
            outputs = dash.callback_context.outputs_list
            styles = []
            for output in outputs:
                if output["id"]["ensemble"] == ens:
                    styles.append({"display": "inline"})
                else:
                    styles.append({"display": "none"})
            return styles

        @app.callback(
            Output(self.storage_id, "data"),
            [
                Input(
                    {"type": self.uuid("range"), "index": ALL, "ensemble": ALL}, "value"
                ),
                Input(
                    {"type": self.uuid("select"), "index": ALL, "ensemble": ALL},
                    "value",
                ),
                Input(self.uuid("ensemble"), "value"),
            ],
            [State(self.storage_id, "data")],
        )
        def display_selectors(ranges, selects, ensemble, storage):
            df = self.parameterdf[self.parameterdf["ENSEMBLE"] == ensemble]

            storage = json.loads(storage) if storage is not None else {}
            range_inputs = dash.callback_context.inputs_list[0]
            select_inputs = dash.callback_context.inputs_list[1]
            for col in range_inputs:
                if col["id"]["ensemble"] == ensemble:
                    df = df[
                        df[col["id"]["index"]].between(
                            col["value"][0], col["value"][1]
                        )
                    ]
            for col in select_inputs:
                if col["id"]["ensemble"] == ensemble:
                    df = df[
                        df[col["id"]["index"]].isin(col["value"])
                    ]
                    print(col["value"])
            storage[ensemble] = df['REAL'].unique().tolist()
            print(ensemble, storage)
            return json.dumps(storage)


def make_rangeslider(name, values, unique_id):
    return html.Div(
        style={"marginBottom": "25px", "fontSize": "10px"},
        children=[
            html.Label(children=name,),
            dcc.RangeSlider(
                id=unique_id,
                min=values.min(),
                max=values.max(),
                step=(values.max() - values.min()) / 100,
                value=[values.min(), values.max()],
                marks={
                    str(values.min()): {"label": f"{values.min():.2f}"},
                    str(values.max()): {"label": f"{values.max():.2f}"},
                },
            ),
        ],
    )


def make_multiselect(name, values, unique_id):
    return html.Div(
        children=[
            html.Label(style={"marginTop": "10px", "fontSize": "10px"}, children=name,),
            wcc.Select(
                style={"fontSize": "10px"},
                id=unique_id,
                options=[{"label": val, "value": val} for val in values],
                value=values,
                size=min(5, len(values)),
            ),
        ],
    )
