from uuid import uuid4
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_plotly.graph_objs import FanChart
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
from ..datainput import scratch_ensemble


class SummaryStats:
    '''### Summary statistics

This container visualizes simulation profiles, both per realization and
statistical plots (min, max, mean, p10, p90).

* `ensemble`: Which ensemble in `container_settings` to visualize.
* `sampling`: Optional. Either `monthly` or `yearly`. Default is `monthly`.
* `title`: Optional title for the container.
'''

    def __init__(
            self,
            app,
            container_settings,
            ensemble,
            sampling: str = 'monthly',
            title: str = 'Simulation time series'):

        self.title = title
        self.dropwdown_vector_id = 'dropdown-vector-{}'.format(uuid4())
        self.sampling = sampling
        self.radio_plot_type_id = 'radio-plot-type-{}'.format(uuid4())
        self.chart_id = 'chart-id-{}'.format(uuid4())

        # Finding all summary vectors:
        self.ensemble_path = container_settings['scratch_ensembles'][ensemble]

        self.smry_columns = sorted(list(get_summary_data(self.ensemble_path,
                                                         self.sampling)
                                        .drop(columns=['DATE', 'REAL'])
                                        .columns))

        self.set_callbacks(app)

    @property
    def layout(self):
        return html.Div([
            html.H2(self.title),
            html.P('Summary Vector:', style={'font-weight': 'bold'}),
            dcc.Dropdown(id=self.dropwdown_vector_id,
                         clearable=False,
                         options=[{'label': i, 'value': i}
                                  for i in self.smry_columns],
                         value=self.smry_columns[0]),
            html.P('Plot type:', style={'font-weight': 'bold'}),
            dcc.RadioItems(id=self.radio_plot_type_id,
                           options=[{'label': i, 'value': i}
                                    for i in ['Realizations', 'Statistics']],
                           value='Realizations'),
            dcc.Graph(id=self.chart_id,
                      config={
                          'displaylogo': False,
                          'modeBarButtonsToRemove': ['sendDataToCloud']
                      }
                      )
        ])

    def set_callbacks(self, app):
        @app.callback(Output(self.chart_id, 'figure'),
                      [Input(self.dropwdown_vector_id, 'value'),
                       Input(self.radio_plot_type_id, 'value')])
        def update_plot(vector, summary_plot_type):
            if summary_plot_type == 'Realizations':
                return render_realization_plot(
                    self.ensemble_path,
                    self.sampling, vector)
            if summary_plot_type == 'Statistics':
                return render_stat_plot(
                    self.ensemble_path,
                    self.sampling, vector)

    def add_webvizstore(self):
        return [(get_summary_data, [{'ensemble_path': self.ensemble_path,
                                     'sampling': self.sampling,
                                     'statistics': False}]),
                (get_summary_data, [{'ensemble_path': self.ensemble_path,
                                     'sampling': self.sampling,
                                     'statistics': True}])]


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_summary_data(ensemble_path, sampling,
                     statistics=False) -> pd.DataFrame:

    ens = scratch_ensemble('', ensemble_path)
    if statistics:
        return ens.get_smry_stats(time_index=sampling)
    else:
        return ens.get_smry(time_index=sampling)


@cache.memoize(timeout=cache.TIMEOUT)
def render_realization_plot(ensemble_path, sampling, vector):

    data = get_summary_data(ensemble_path,
                            sampling)[['REAL', 'DATE', vector]]

    traces = [{
        'x': df['DATE'],
        'customdata': df['REAL'],
        'y': df[vector],
        'name': name,
        'type': 'line'
    } for name, df in data.groupby('REAL') if name != 'DATE']

    layout = {
        'hovermode': 'closest',
        'barmode': 'overlay',
        'bargap': 0.05,
        'xaxis': {'title': 'Date', 'family': 'Equinor'},
        'yaxis': {'title': vector, 'family': 'Equinor'},
        'font': {'family': 'Equinor'},
        'hoverlabel': {'font': {'family': 'Equinor'}},
    }

    return {'data': traces, 'layout': layout}


@cache.memoize(timeout=cache.TIMEOUT)
def render_stat_plot(ensemble_path, sampling, vector):

    data = get_summary_data(ensemble_path, sampling,
                            statistics=True)[vector].unstack().transpose()

    data['name'] = vector
    data.rename(index=str, inplace=True,
                columns={"minimum": "min", "maximum": "max"})

    return FanChart(data.iterrows())
