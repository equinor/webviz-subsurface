from uuid import uuid4
import json
import numpy as np
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output


class ParameterFilter:
    """### ParameterFilter

This private container displays a filter widget for ensemble parameters. 
It is meant to be used as a component in other containers.
The container is initialized with a dataframe of parameter values from an ensemble set.
Each parameter is then visualized as a rangeslider.
When manipulating the rangesliders, the parameter dataframe is filtered, and the 
remaining realizations are stored as a list to a dcc.Store. The dcc Store object
can be retrieved with a callback (parameterfilter.storage_id).

To use:
1. Initialize an instance of this class in a container
2. Add parameterfilter.layout to the container layout
3. Register a callback that reads from parameterfilter.storage_id

* `app`: The Dash app object
* `parameters`: Dataframe of parameters from an ensemble set (see datainput._fmu_input)

TODO:
Currently only scalar parameters are used. Should be expanded to handle categorical parameters

"""

    def __init__(self, app, parameters):

        self.parameters = parameters
        self.numerical_parameters = (
            self.parameters.drop(["ENSEMBLE", "REAL"], axis=1)
            .select_dtypes(include=[np.number])
            .columns.tolist()
        )
        self.uuid = f"{str(uuid4())}"
        self._storage_id = f"{str(uuid4())}-real-data"
        self.parameter_sliders = []
        self.parameter_ids = []
        self.parameter_wrapper_ids = []
        self.find_parameters()
        self.set_callbacks(app)

    @property
    def storage_id(self):
        """The id of the dcc.Store component that holds the filtered realizations"""
        return self._storage_id

    def make_parameter_slider_and_id(self, parameter_name, parameter):
        """Make a slider widget for each parameter, and register relevant ids"""
        self.parameter_sliders.append(
            html.Div(
                id=f"{parameter_name}-wrapper-{self.uuid}",
                children=[
                    html.Label(
                        style={"marginTop": "25px", "fontSize": "10px"},
                        children=parameter_name,
                    ),
                    dcc.RangeSlider(
                        id=f"{parameter_name}-{self.uuid}",
                        min=parameter.min(),
                        max=parameter.max(),
                        step=(parameter.max() - parameter.min()) / 100,
                        value=[parameter.min(), parameter.max()],
                        marks={
                            str(parameter.min()): {"label": f"{parameter.min():.2f}"},
                            str(parameter.mean()): {"label": f"{parameter.mean():.2f}"},
                            str(parameter.max()): {"label": f"{parameter.max():.2f}"},
                        },
                    ),
                ],
            )
        )
        self.parameter_ids.append(f"{parameter_name}-{self.uuid}")
        self.parameter_wrapper_ids.append(f"{parameter_name}-wrapper-{self.uuid}")

    def find_parameters(self):
        dom_elements = []
        for parameter in self.parameters.columns:
            if parameter == "ENSEMBLE":
                print(self.parameters[parameter])
            elif parameter == "REAL":
                pass
            elif parameter in self.numerical_parameters:
                self.make_parameter_slider_and_id(parameter, self.parameters[parameter])
            else:
                pass

    @property
    def layout(self):
        return html.Div(
            style={
                "overflowY": "scroll",
                "height": "800px",
                "paddingLeft": "15px",
                "paddingRight": "15px",
            },
            children=[
                dcc.Store(id=self.storage_id),
                html.Label(style={"fontSize": "10px"}, children="Ensemble"),
                dcc.Dropdown(
                    id="ensemble",
                    options=[
                        {"label": e, "value": e}
                        for e in list(self.parameters["ENSEMBLE"].unique())
                    ],
                    value=list(self.parameters["ENSEMBLE"].unique())[0],
                ),
                html.Div(children=self.parameter_sliders),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.storage_id, "children"),
            [
                Input(item, "value")
                for sublist in [["ensemble"], self.parameter_ids]
                for item in sublist
            ],
        )
        def _get_parameters(ensemble, *parameters):
            """Filters dataframe and dumps list of realizations to store"""
            if not parameters:
                raise PreventUpdate
            df = self.parameters.loc[self.parameters["ENSEMBLE"] == ensemble]
            for pcol, parameter in zip(
                df[self.numerical_parameters].columns, parameters
            ):
                df = df.loc[df[pcol].between(parameter[0], parameter[1])]
            return json.dumps(df["REAL"].tolist())
