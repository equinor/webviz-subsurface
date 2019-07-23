import itertools
from uuid import uuid4
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_plotly.graph_objs import FanChart
from webviz_config.common_cache import cache
from webviz_config.containers import WebvizContainer
from plotly.colors import DEFAULT_PLOTLY_COLORS
from webviz_subsurface.datainput import load_ensemble_set, get_time_series_data, \
    get_time_series_statistics, get_time_series_fielgains


# =============================================================================
# Container
# =============================================================================

class TimeSeries(WebvizContainer):

    def __init__(
            self,
            app,
            container_settings,
            ensembles,
            column_keys=None,
            sampling: str = 'monthly',
            history_uncertainty: bool = False):

        self.title = 'EnsembleSet'
        self.uid = f'{uuid4()}'
        self.time_index = sampling
        self.column_keys = tuple(column_keys) if isinstance(
            column_keys, (list, tuple)) else None
        self.history_uncertainty = history_uncertainty
        self.ensemble_paths = tuple(
            (ensemble,
             container_settings['scratch_ensembles'][ensemble])
            for ensemble in ensembles)
        self.set_callbacks(app)

    @property
    def dropwdown_vector_id(self):
        return f'dropdown-vector-{self.uid}'

    @property
    def chart_id(self):
        return f'chart-id-{self.uid}'

    @property
    def vector_columns(self):
        return sorted(
            list(
                get_time_series_data(
                    ensemble_paths=self.ensemble_paths,
                    time_index=self.time_index,
                    column_keys=self.column_keys) .drop(
                        columns=[
                            'DATE',
                            'REAL',
                            'ENSEMBLE']).columns))

    @property
    def smry_history_columns(self):
        return tuple(
            [vctr + 'H' for vctr in self.vector_columns
             if vctr + 'H' in self.vector_columns])

    @property
    def smry_vector_columns(self):
        return tuple(
            [vctr for vctr in self.vector_columns
             if vctr not in self.smry_history_columns])


# =============================================================================
# Layout
# =============================================================================

    @property
    def layout(self):
        return html.Div([
            html.H2(self.title),
            html.Div([
                html.Div([
                    html.P('Summary Vector:', style={'font-weight': 'bold'}),
                    dcc.Dropdown(id=self.dropwdown_vector_id,
                                 clearable=False,
                                 options=[{'label': i, 'value': i}
                                          for i in self.smry_vector_columns],
                                 value=self.smry_vector_columns[0]),
                    html.P('Plot type:', style={'font-weight': 'bold'}),
                ], style={"float":"left", 'display': 'inline-block'}),
                html.Div([
                    html.Div(id=self.chart_id)
                ], style={'width': '80%', 'display': 'inline-block'}),
            ]),
        ])


# =============================================================================
# Callbacks
# =============================================================================

    def set_callbacks(self, app):
        @app.callback(Output(self.chart_id, 'children'),
                      [Input(self.dropwdown_vector_id, 'value')])
        def update_plot(vector):
            return render_realization_plot(
                ensemble_paths=self.ensemble_paths,
                column_keys=self.column_keys,
                time_index=self.time_index,
                vector=vector
            )


# =============================================================================
# Render functions
# =============================================================================

def render_realization_plot(
        ensemble_paths: tuple,
        time_index: str,
        column_keys: tuple,
        vector: str,
    ):

    cycle_list = itertools.cycle(DEFAULT_PLOTLY_COLORS)

    smry_data = get_time_series_data(
        ensemble_paths=ensemble_paths,
        column_keys=column_keys,
        time_index=time_index)[
            ['REAL', 'DATE', 'ENSEMBLE', vector]]

    smry_data.dropna(subset=[vector])

    plot_traces = []

    for ens in smry_data.ENSEMBLE.unique():

        plot_traces += trace_group(
            ens_smry_data=smry_data[smry_data['ENSEMBLE'] == ens],
            ens=ens,
            vector=vector,
            color=next(cycle_list))

    layout = {
        'hovermode': 'closest',
        'barmode': 'overlay',
        'bargap': 0.05,
        'xaxis': {'title': 'Date', 'family': 'Equinor'},
        'yaxis': {'title': vector, 'family': 'Equinor'},
        'font': {'family': 'Equinor'},
        'hoverlabel': {'font': {'family': 'Equinor'}},
    }

    return dcc.Graph(figure={'data': plot_traces, 'layout': layout},
                     config={
                         'displaylogo': False,
                         'modeBarButtonsToRemove': ['sendDataToCloud']})


# =============================================================================
# Auxiliary functions
# =============================================================================

def trace_group(ens_smry_data, ens, vector, color):

    ens_traces = []

    # 1st and only trace of the legendgroup to show up in legend
    ens_traces.append({
        'x': ens_smry_data[ens_smry_data['REAL']
                           == ens_smry_data.REAL.unique()[0]]['DATE'],
        'y': ens_smry_data[ens_smry_data['REAL']
                           == ens_smry_data.REAL.unique()[0]][vector],
        'legendgroup': ens,
        'name': ens,
        'type': 'markers',
        'marker': {
            'color': color
        },
        'showlegend': True
    })

    for real in ens_smry_data.REAL.unique()[1:]:

        ens_traces.append({
            'x': ens_smry_data[ens_smry_data['REAL'] == real]['DATE'],
            'y': ens_smry_data[ens_smry_data['REAL'] == real][vector],
            'legendgroup': ens,
            'name': ens,
            'type': 'line',
            'marker': {
                'color': color
            },
            'showlegend': False
        })

    return ens_traces


def single_trace(ens_smry_data, ens, vector, color):

    return {
        'x': ens_smry_data[ens_smry_data['REAL']
                           == ens_smry_data.REAL.unique()[0]]['DATE'],
        'y': ens_smry_data[ens_smry_data['REAL']
                           == ens_smry_data.REAL.unique()[0]][vector],
        'legendgroup': ens,
        'name': ens,
        'type': 'markers',
        'marker': {
            'color': color
        },
        'showlegend': True
    }

