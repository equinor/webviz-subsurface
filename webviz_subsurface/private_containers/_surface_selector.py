import os
from uuid import uuid4
import json
import yaml
import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc


class SurfaceSelector:
    '''### Surface Selector

Creates a widget to select surfaces from a configuration file.
The current selection are stored in a dcc.Store object that can
be accessed by the storage_id property

* `yaml_file`: A configuration file of surfaces
* `ensembles`: A dictionary of ensemble names and lists of realizations.

Format of configuration file:
some_property:
    names:
        - surfacename
        - surfacename
    dates:
        - somedate
        - somedata
another_property:
    names:
        - surfacename
        - surfacename
    dates:
        - somedate
        - somedata
'''
    def __init__(self, app, yaml_file, ensembles):
        self._configuration = yaml.safe_load(open(yaml_file, "r"))
        self._ensembles = ensembles
        self._storage_id = f"{str(uuid4())}-surface-selector"
        self.set_ids()
        self.set_callbacks(app)

    @property
    def storage_id(self):
        '''The id of the dcc.Store component that holds the selection'''
        return self._storage_id

    def set_ids(self):
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
        self.ensemble_id = f"{uuid}-ens"
        self.ensemble_id_btn_prev = f"{uuid}-ensemble-btn-prev"
        self.ensemble_id_btn_next = f"{uuid}-ensemble-btn-next"
        self.realization_id = f"{uuid}-real"
        self.realization_id_btn_prev = f"{uuid}-realization-btn-prev"
        self.realization_id_btn_next = f"{uuid}-realization-btn-next"
        self.attr_wrapper_id = f"{uuid}-attr-wrapper"
        self.name_wrapper_id = f"{uuid}-name-wrapper"
        self.date_wrapper_id = f"{uuid}-date-wrapper"
        self.ens_wrapper_id = f"{uuid}-ens-wrapper"
        self.real_wrapper_id = f"{uuid}-real-wrapper"
        self.aggreal_id = f"{uuid}-aggreal"

    @property
    def attrs(self):
        return list(self._configuration.keys())

    def names_in_attr(self, attr):
        return self._configuration[attr].get("names", None)

    def dates_in_attr(self, attr):
        return self._configuration[attr].get("dates", None)

    @property
    def ensembles(self):
        return list(self._ensembles.keys())

    def realizations(self, ensemble):
        return self._ensembles[ensemble]

    @property
    def aggregations(self):
        return ["mean", "stddev", "min", "max", "p10", "p90"]

    @property
    def show_dropdown_style(self):
        return {"display": "grid"}

    @property
    def hide_dropdown_style(self):
        return {"display": "none"}

    @property
    def attribute_selector(self):
        return html.Div(
            id=self.attr_wrapper_id,
            style={"display": "grid"},
            children=[
                html.H6("Surface property"),
                html.Div(
                    style=self.set_grid_layout("6fr 1fr"),
                    children=[
                        dcc.Dropdown(
                            id=self.attr_id,
                            options=[
                                {"label": attr, "value": attr}
                                for attr in self.attrs
                            ],
                            value=self.attrs[0],
                            clearable=False,
                        ),
                        self.make_buttons(
                            self.attr_id_btn_prev, self.attr_id_btn_next
                        ),
                    ],
                ),
            ],
        )

    def make_buttons(self, prev_id, next_id):
        return html.Div(
            style=self.set_grid_layout("1fr 1fr"),
            children=[
                html.Button(id=prev_id, children="<="),
                html.Button(id=next_id, children="=>"),
            ],
        )

    @property
    def name_selector(self):
        return html.Div(
            id=self.name_wrapper_id,
            style={"display": "none"},
            children=[
                html.H6("Surface name"),
                html.Div(
                    style=self.set_grid_layout("6fr 1fr"),
                    children=[
                        dcc.Dropdown(id=self.name_id, clearable=False),
                        self.make_buttons(
                            self.name_id_btn_prev, self.name_id_btn_next
                        ),
                    ],
                ),
            ],
        )

    @property
    def date_selector(self):
        return html.Div(
            id=self.date_wrapper_id,
            style={"display": "none"},
            children=[
                html.H6("Date"),
                html.Div(
                    style=self.set_grid_layout("6fr 1fr"),
                    children=[
                        dcc.Dropdown(id=self.date_id, clearable=False),
                        self.make_buttons(
                            self.date_id_btn_prev, self.date_id_btn_next
                        ),
                    ],
                ),
            ],
        )

    @property
    def ensemble_selector(self):
        return html.Div(
            id=self.ens_wrapper_id,
            style={"display": "grid"},
            children=[
                html.H6("Ensemble"),
                html.Div(
                    style=self.set_grid_layout("6fr 1fr"),
                    children=[
                        dcc.Dropdown(
                            id=self.ensemble_id,
                            options=[
                                {"label": ens, "value": ens}
                                for ens in self.ensembles
                            ],
                            value=self.ensembles[0],
                            clearable=False,
                        ),
                        self.make_buttons(
                            self.ensemble_id_btn_prev,
                            self.ensemble_id_btn_next,
                        ),
                    ],
                ),
            ],
        )

    @property
    def realization_selector(self):
        return html.Div(
            id=self.real_wrapper_id,
            children=[
                html.H6("Aggregation / Realization"),
                html.Div(
                    style=self.set_grid_layout("3fr 3fr 1fr"),
                    children=[
                        dcc.Dropdown(
                            id=self.aggreal_id,
                            options=[
                                {
                                    "label": "Aggregation",
                                    "value": "Aggregation",
                                },
                                {
                                    "label": "Realization",
                                    "value": "Realization",
                                },
                            ],
                            value="Aggregation",
                        ),
                        dcc.Dropdown(id=self.realization_id, clearable=False),
                        self.make_buttons(
                            self.realization_id_btn_prev,
                            self.realization_id_btn_next,
                        ),
                    ],
                ),
            ],
        )

    def set_grid_layout(self, columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    @property
    def layout(self):
        return html.Div(
            children=[
                html.Div(
                    style=self.set_grid_layout("1fr"),
                    children=[
                        self.attribute_selector,
                        self.name_selector,
                        self.date_selector,
                    ],
                ),
                self.ensemble_selector,
                self.realization_selector,
                dcc.Store(id=self.storage_id),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.attr_id, "value"),
            [
                Input(self.attr_id_btn_prev, "n_clicks"),
                Input(self.attr_id_btn_next, "n_clicks"),
            ],
            [State(self.attr_id, "value")],
        )
        def update_attr(n_prev, n_next, current_value):
            ctx = dash.callback_context.triggered
            if not ctx or not current_value:
                raise PreventUpdate
            if not ctx[0]["value"]:
                return current_value
            cb = ctx[0]["prop_id"]
            if cb == f"{self.attr_id_btn_prev}.n_clicks":
                return prev_value(current_value, self.attrs)
            if cb == f"{self.attr_id_btn_next}.n_clicks":
                return next_value(current_value, self.attrs)

        @app.callback(
            Output(self.ensemble_id, "value"),
            [
                Input(self.ensemble_id_btn_prev, "n_clicks"),
                Input(self.ensemble_id_btn_next, "n_clicks"),
            ],
            [State(self.ensemble_id, "value")],
        )
        def update_ensemble(n_prev, n_next, current_value):
            ctx = dash.callback_context.triggered
            if not ctx or not current_value:
                raise PreventUpdate
            if not ctx[0]["value"]:
                return current_value
            cb = ctx[0]["prop_id"]
            if cb == f"{self.ensemble_id_btn_prev}.n_clicks":
                return prev_value(current_value, self.ensembles)
            if cb == f"{self.ensemble_id_btn_next}.n_clicks":
                return next_value(current_value, self.ensembles)
            return current_value

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
        def update_name(attr, n_prev, n_next, current_value):
            ctx = dash.callback_context.triggered
            if not ctx:
                raise PreventUpdate
            names = self.names_in_attr(attr)
            if not names:
                return None, None, self.hide_dropdown_style

            cb = ctx[0]["prop_id"]
            if cb == f"{self.name_id_btn_prev}.n_clicks":
                value = prev_value(current_value, names)
            elif cb == f"{self.name_id_btn_next}.n_clicks":
                value = next_value(current_value, names)
            else:
                value = current_value if current_value in names else names[0]
            options = [{"label": name, "value": name} for name in names]
            return options, value, self.show_dropdown_style

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
        def update_date(attr, n_prev, n_next, current_value):
            ctx = dash.callback_context.triggered
            if not ctx:
                raise PreventUpdate
            dates = self.dates_in_attr(attr)
            if not dates:
                return [], None, self.hide_dropdown_style

            cb = ctx[0]["prop_id"]
            if cb == f"{self.date_id_btn_prev}.n_clicks":
                value = prev_value(current_value, dates)
            elif cb == f"{self.date_id_btn_next}.n_clicks":
                value = next_value(current_value, dates)
            else:
                value = current_value if current_value in dates else dates[0]
            options = [{"label": date, "value": date} for date in dates]
            return options, value, self.show_dropdown_style

        @app.callback(
            [
                Output(self.realization_id, "options"),
                Output(self.realization_id, "value"),
                Output(self.realization_id, "style"),
            ],
            [
                Input(self.ensemble_id, "value"),
                Input(self.aggreal_id, "value"),
                Input(self.realization_id_btn_prev, "n_clicks"),
                Input(self.realization_id_btn_next, "n_clicks"),
            ],
            [State(self.realization_id, "value")],
        )
        def update_real(ensemble, aggreal, n_prev, n_next, current_value):
            ctx = dash.callback_context.triggered
            if not ctx:
                raise PreventUpdate
            if aggreal == "Aggregation":
                reals = self.aggregations
            else:
                reals = self.realizations(ensemble)
            if not reals:
                return [], None, self.hide_dropdown_style
            cb = ctx[0]["prop_id"]
            if cb == f"{self.realization_id_btn_prev}.n_clicks":
                value = prev_value(current_value, reals)
            elif cb == f"{self.realization_id_btn_next}.n_clicks":
                value = next_value(current_value, reals)
            else:
                value = current_value if current_value in reals else reals[0]
            options = [{"value": real, "label": real} for real in reals]
            return options, value, self.show_dropdown_style

        @app.callback(
            Output(self.storage_id, "children"),
            [
                Input(self.attr_id, "value"),
                Input(self.name_id, "value"),
                Input(self.date_id, "value"),
                Input(self.ensemble_id, "value"),
                Input(self.aggreal_id, "value"),
                Input(self.realization_id, "value"),
            ],
        )
        def set_data(attr, name, date, ensemble, aggreal, realization):
            return json.dumps(
                {
                    "attribute": attr,
                    "name": name,
                    "date": date,
                    "ensemble": ensemble,
                    "aggregation": True if aggreal == "Aggregation" else False,
                    "realization": realization,
                }
            )


def prev_value(current_value, options):
    try:
        index = options.index(current_value)
    except ValueError:
        index = None
    if index > 0:
        return options[index - 1]
    else:
        return current_value


def next_value(current_value, options):
    try:
        index = options.index(current_value)
    except ValueError:
        index = None
    if index < len(options) - 1:
        return options[index + 1]
    else:
        return current_value
