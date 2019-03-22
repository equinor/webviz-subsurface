from uuid import uuid4
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_plotly.graph_objs import FanChart
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
from ..datainput import scratch_ensemble


class ParameterDistribution:
    '''### Parameter distribution

This container shows parameter distribution as histogram,
and correlation between the parameters as a correlation matrix.

* `ensemble`: Which ensemble in `container_settings` to visualize.
* `title`: Optional title for the container.
'''

    def __init__(self, app, container_settings, ensemble,
                 title: str = 'Parameter Distribution'):

        self.title = title

        self.dropdown_vector_id = 'dropdown-vector-{}'.format(uuid4())
        self.radio_plot_type_id = 'radio-plot-type-{}'.format(uuid4())
        self.chart_id = 'chart-id-{}'.format(uuid4())
        self.histogram_div_id = 'histogram-div-{}'.format(uuid4())

        # Finding all parameters:
        self.ensemble_path = container_settings['scratch_ensembles'][ensemble]
        self.parameter_columns = sorted(list(
            get_parameters(self.ensemble_path).columns))

        self.set_callbacks(app)

    @property
    def layout(self):
        return html.Div([
            html.H2(self.title),
            html.P('Plot type:', style={'font-weight': 'bold'}),
            dcc.RadioItems(id=self.radio_plot_type_id,
                           options=[{'label': i, 'value': i} for i in
                                    ['Histogram', 'Pairwise correlation']],
                           value='Histogram'),
            html.Div(id=self.histogram_div_id,
                     children=[
                         html.P('Parameter:',
                                style={'font-weight': 'bold'}),
                         dcc.Dropdown(id=self.dropdown_vector_id,
                                      clearable=False,
                                      options=[{'label': i, 'value': i} for
                                               i in self.parameter_columns],
                                      value=self.parameter_columns[0]),
                     ]),
            dcc.Graph(id=self.chart_id,
                      config={
                          'displaylogo': False,
                          'modeBarButtonsToRemove': ['sendDataToCloud']
                      }
                      )
        ])

    def set_callbacks(self, app):
        @app.callback(Output(self.chart_id, 'figure'),
                      [Input(self.dropdown_vector_id, 'value'),
                       Input(self.radio_plot_type_id, 'value')])
        def update_plot(parameter, plot_type):
            if plot_type == 'Histogram':
                return render_histogram(self.ensemble_path, parameter)
            if plot_type == 'Pairwise correlation':
                return render_matrix(self.ensemble_path)

        @app.callback(Output(self.histogram_div_id, 'style'),
                      [Input(self.radio_plot_type_id, 'value')])
        def toggle_parameter_selector(plot_type):
            if plot_type == 'Histogram':
                return {'display': 'block'}
            if plot_type == 'Pairwise correlation':
                return {'display': 'none'}

    def add_webvizstore(self):
        return [(get_parameters, [{'ensemble_path': self.ensemble_path}])]


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_parameters(ensemble_path) -> pd.DataFrame:
    ens = scratch_ensemble('', ensemble_path)

    return ens.parameters


@cache.memoize(timeout=cache.TIMEOUT)
def render_histogram(ensemble_path, parameter):
    data = {
        'x': get_parameters(ensemble_path)[parameter],
        'type': 'histogram'
    }

    layout = {
        'bargap': 0.05,
        'font': {'family': 'Equinor'},
        'xaxis': {'family': 'Equinor'},
        'yaxis': {'family': 'Equinor'},
        'hoverlabel': {'font': {'family': 'Equinor'}}
    }

    return {'data': [data], 'layout': layout}


@cache.memoize(timeout=cache.TIMEOUT)
def render_matrix(ensemble_path):

    data = get_parameters(ensemble_path)
    values = list(data.corr().values)

    data = {
        'type': 'heatmap',
        'x': data.columns,
        'y': data.columns,
        'z': values
    }

    layout = {
        'margin': {'l': 200},
        'font': {'family': 'Equinor'},
        'xaxis': {'family': 'Equinor'},
        'yaxis': {'family': 'Equinor'},
        'hoverlabel': {'font': {'family': 'Equinor'}}
    }

    return {'data': [data], 'layout': layout}
