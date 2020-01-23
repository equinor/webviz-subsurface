from datetime import datetime
from uuid import uuid4
import json
import yaml
import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc


class SurfaceSelector:
    # pylint: disable=too-many-instance-attributes,too-many-statements
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
        - somedate
"""

    def __init__(self, app, config, ensembles):
        self._configuration = self.read_config(config)
        self._ensembles = ensembles
        self._storage_id = f"{str(uuid4())}-surface-selector"
        self.set_ids()
        self.set_callbacks(app)

    @staticmethod
    def read_config(config):
        """Reads config file either from a yaml provided file or from a dict"""
        if isinstance(config, str):
            return yaml.safe_load(open(config, "r"))

        if isinstance(config, dict):
            return config

        raise TypeError("Config must be a dictionary of a yaml file")

    @property
    def storage_id(self):
        """The id of the dcc.Store component that holds the selection"""
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
        self.name_wrapper_id = f"{uuid}-name-wrapper"
        self.date_wrapper_id = f"{uuid}-date-wrapper"
        self.ens_wrapper_id = f"{uuid}-ens-wrapper"
        self.real_wrapper_id = f"{uuid}-real-wrapper"
        self.aggreal_id = f"{uuid}-aggreal"
        self.sens_name_id = f"{uuid}-sens-name-id"
        self.sens_case_id = f"{uuid}-sens-case-id"
        self.sens_name_wrapper_id = f"{uuid}-sens-name-wrapper-id"
        self.sens_case_wrapper_id = f"{uuid}-sens-case-wrapper-id"

    @property
    def attrs(self):
        return list(self._configuration.keys())

    def names_in_attr(self, attr):
        return self._configuration[attr].get("names", None)

    def dates_in_attr(self, attr):
        return self._configuration[attr].get("dates", None)

    @property
    def ensembles(self):
        return list(self._ensembles["ENSEMBLE"].unique())

    def sens_names(self, ensemble):
        sensnames = list(
            self._ensembles.loc[self._ensembles["ENSEMBLE"] == ensemble][
                "SENSNAME"
            ].unique()
        )
        if sensnames[0] is None:
            return None
        return sensnames

    def sens_cases(self, ensemble, sensname):
        senscases = list(
            self._ensembles.loc[
                (self._ensembles["ENSEMBLE"] == ensemble)
                & (self._ensembles["SENSNAME"] == sensname)
            ]["SENSCASE"].unique()
        )
        if senscases and senscases[0] is None:
            return None
        return senscases

    def realizations(self, ensemble, sensname=None, senstype=None):
        df = self._ensembles.loc[self._ensembles["ENSEMBLE"] == ensemble].copy()
        if sensname and senstype:
            df = df.loc[(df["SENSNAME"] == sensname) & (df["SENSCASE"] == senstype)]
        return list(df["REAL"])

    @property
    def aggregations(self):
        return ["mean", "stddev", "min", "max", "p10", "p90"]

    @property
    def attribute_selector(self):
        return html.Div(
            style={"display": "grid"},
            children=[
                html.H6("Surface property"),
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
                        ),
                        self.make_buttons(self.attr_id_btn_prev, self.attr_id_btn_next),
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

    def selector(self, wrapper_id, dropdown_id, title, btn_prev, btn_next):
        return html.Div(
            id=wrapper_id,
            style={"display": "none"},
            children=[
                html.H6(title),
                html.Div(
                    style=self.set_grid_layout("6fr 1fr"),
                    children=[
                        dcc.Dropdown(id=dropdown_id, clearable=False),
                        self.make_buttons(btn_prev, btn_next),
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
                                {"label": ens, "value": ens} for ens in self.ensembles
                            ],
                            value=self.ensembles[0],
                            clearable=False,
                        ),
                        self.make_buttons(
                            self.ensemble_id_btn_prev, self.ensemble_id_btn_next
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
                html.Div(
                    style=self.set_grid_layout("3fr 3fr 1fr 3fr 3fr"),
                    children=[
                        html.Div(
                            children=[
                                html.Label("Mode"),
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
                                    clearable=False,
                                ),
                            ]
                        ),
                        html.Div(
                            children=[
                                html.Label("Realization"),
                                dcc.Dropdown(id=self.realization_id, clearable=False),
                            ]
                        ),
                        html.Div(
                            children=[
                                html.Label("Prev/Next"),
                                self.make_buttons(
                                    self.realization_id_btn_prev,
                                    self.realization_id_btn_next,
                                ),
                            ]
                        ),
                        html.Div(
                            id=self.sens_name_wrapper_id,
                            children=[
                                html.Label("Sensitivity name"),
                                dcc.Dropdown(id=self.sens_name_id, clearable=False),
                            ],
                        ),
                        html.Div(
                            id=self.sens_case_wrapper_id,
                            children=[
                                html.Label("Sensitivity case"),
                                dcc.Dropdown(id=self.sens_case_id, clearable=False),
                            ],
                        ),
                    ],
                )
            ],
        )

    @staticmethod
    def set_grid_layout(columns):
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
                    ],
                ),
                self.ensemble_selector,
                self.realization_selector,
                dcc.Store(id=self.storage_id),
            ]
        )

    def set_callbacks(self, app):
        # pylint: disable=inconsistent-return-statements
        @app.callback(
            Output(self.attr_id, "value"),
            [
                Input(self.attr_id_btn_prev, "n_clicks"),
                Input(self.attr_id_btn_next, "n_clicks"),
            ],
            [State(self.attr_id, "value")],
        )
        def _update_attr(_n_prev, _n_next, current_value):
            ctx = dash.callback_context.triggered
            if not ctx or not current_value:
                raise PreventUpdate
            if not ctx[0]["value"]:
                return current_value
            callback = ctx[0]["prop_id"]
            if callback == f"{self.attr_id_btn_prev}.n_clicks":
                return prev_value(current_value, self.attrs)
            if callback == f"{self.attr_id_btn_next}.n_clicks":
                return next_value(current_value, self.attrs)

        @app.callback(
            Output(self.ensemble_id, "value"),
            [
                Input(self.ensemble_id_btn_prev, "n_clicks"),
                Input(self.ensemble_id_btn_next, "n_clicks"),
            ],
            [State(self.ensemble_id, "value")],
        )
        def _update_ensemble(_n_prev, _n_next, current_value):
            ctx = dash.callback_context.triggered
            if not ctx or not current_value:
                raise PreventUpdate
            if not ctx[0]["value"]:
                return current_value
            callback = ctx[0]["prop_id"]
            if callback == f"{self.ensemble_id_btn_prev}.n_clicks":
                return prev_value(current_value, self.ensembles)
            if callback == f"{self.ensemble_id_btn_next}.n_clicks":
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
        def _update_name(attr, _n_prev, _n_next, current_value):
            ctx = dash.callback_context.triggered
            if not ctx:
                raise PreventUpdate
            names = self.names_in_attr(attr)
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
        def _update_date(attr, _n_prev, _n_next, current_value):
            ctx = dash.callback_context.triggered
            if not ctx:
                raise PreventUpdate
            dates = self.dates_in_attr(attr)
            if not dates or not dates[0]:
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
                Input(self.sens_name_id, "value"),
                Input(self.sens_case_id, "value"),
            ],
            [State(self.realization_id, "value")],
        )
        def _update_real(
            ensemble, aggreal, _n_prev, _n_next, sens_name, sens_case, current_value
        ):
            ctx = dash.callback_context.triggered
            if not ctx:
                raise PreventUpdate
            if aggreal == "Aggregation":
                reals = self.aggregations
            else:
                reals = self.realizations(ensemble, sens_name, sens_case)
            if not reals:
                return [], None, {"visibility": "hidden"}
            callback = ctx[0]["prop_id"]
            if callback == f"{self.realization_id_btn_prev}.n_clicks":
                value = prev_value(current_value, reals)
            elif callback == f"{self.realization_id_btn_next}.n_clicks":
                value = next_value(current_value, reals)
            else:
                value = current_value if current_value in reals else reals[0]
            options = [{"value": real, "label": real} for real in reals]
            return options, value, {}

        @app.callback(
            [
                Output(self.sens_name_id, "options"),
                Output(self.sens_name_id, "value"),
                Output(self.sens_name_wrapper_id, "style"),
            ],
            [Input(self.ensemble_id, "value")],
            [State(self.sens_name_id, "value")],
        )
        def _update_sens_name(ensemble, current_value):
            sens_names = self.sens_names(ensemble)
            if not sens_names:
                return [], None, {"visibility": "hidden"}
            value = current_value if current_value in sens_names else sens_names[0]
            options = [{"value": sens, "label": sens} for sens in sens_names]
            return options, value, {}

        @app.callback(
            [
                Output(self.sens_case_id, "options"),
                Output(self.sens_case_id, "value"),
                Output(self.sens_case_wrapper_id, "style"),
            ],
            [Input(self.sens_name_id, "value")],
            [State(self.ensemble_id, "value"), State(self.sens_case_id, "value")],
        )
        def _update_sens_case(sensname, ensemble, current_value):
            sens_cases = self.sens_cases(ensemble, sensname)
            if not sens_cases:
                return [], None, {"visibility": "hidden"}
            value = current_value if current_value in sens_cases else sens_cases[0]
            options = [{"value": sens, "label": sens} for sens in sens_cases]
            return options, value, {}

        @app.callback(
            Output(self.storage_id, "children"),
            [
                Input(self.attr_id, "value"),
                Input(self.name_id, "value"),
                Input(self.date_id, "value"),
                Input(self.ensemble_id, "value"),
                Input(self.aggreal_id, "value"),
                Input(self.realization_id, "value"),
                Input(self.sens_name_id, "value"),
                Input(self.sens_case_id, "value"),
            ],
        )
        def _set_data(
            attr, name, date, ensemble, aggreal, calculation, sens_name, sens_case
        ):

            """
            Stores current selections to dcc.Store. The information can
            be retrieved as a json string from a dash callback Input.
            E.g. [Input(surfselector.storage_id, 'children')]
            """
            reals = self.realizations(ensemble, sens_name, sens_case)
            all_senscases = [
                {
                    "case": senscase,
                    "realizations": self.realizations(ensemble, sens_name, senscase),
                }
                for senscase in self.sens_cases(ensemble, sens_name)
            ]
            return json.dumps(
                {
                    "attribute": attr,
                    "name": name,
                    "date": date,
                    "ensemble": ensemble,
                    "aggregation": calculation if aggreal == "Aggregation" else None,
                    "realization": reals if aggreal == "Aggregation" else calculation,
                    "sensname": sens_name,
                    "senscase": sens_case,
                    "all_senscases": all_senscases,
                }
            )


def prev_value(current_value, options):
    try:
        index = options.index(current_value)
        return options[max(0, index - 1)]
    except ValueError:
        return current_value


def next_value(current_value, options):
    try:
        index = options.index(current_value)
        return options[min(len(options) - 1, index + 1)]
    except ValueError:
        return current_value


def format_date(date_string):
    """Reformat date string for presentation
    20010101 => Jan 2001
    20010101_20010601 => (Jan 2001) - (June 2001)
    20010101_20010106 => (01 Jan 2001) - (06 Jan 2001)"""
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
