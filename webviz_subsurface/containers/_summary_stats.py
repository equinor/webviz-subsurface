from uuid import uuid4
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_plotly.graph_objs import FanChart
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
from webviz_config.containers import WebvizContainer
from ..datainput import scratch_ensemble
from plotly.colors import DEFAULT_PLOTLY_COLORS
import itertools


class SummaryStats(WebvizContainer):

    """Summary statistics

    Args:
        ensembles: list of ensemble paths. Length >= 1
        column_keys: list of pre defined vectors to visualize. Default is none
        sampling: Optional. Either 'monthly' or 'yearly'. Default is 'monthly'.
        title: Optional title for the container.
        history_uncertainty: boolean value if history vector is subjected to
            uncertainty.
    Return:
        dcc.Graph() of either statistics plot or realization plot.
    Annotations:
        Function argument-litst are passed as tuple as they are hashed in
        webviz-store --portable option (list-type is not hashable).
        Pandas within fmu.ensemlbe expects list. Therefore argument-tuples are
        converted back into lists within get_smry_data and get_smry_stats
        functions.
    """

    def __init__(
            self,
            app,
            container_settings,
            ensembles,
            column_keys=None,
            sampling: str = 'monthly',
            title: str = 'Simulation time series',
            history_uncertainty: bool = False):

        self.title = title
        self.dropwdown_vector_id = 'dropdown-vector-{}'.format(uuid4())
        self.column_keys = tuple(column_keys) if isinstance(
            column_keys, (list, tuple)) else None
        self.sampling = sampling
        self.radio_plot_type_id = 'radio-plot-type-{}'.format(uuid4())
        self.show_history_uncertainty_id = 'show-history-uncertainty-{}'.format(
            uuid4())
        self.chart_id = 'chart-id-{}'.format(uuid4())
        self.ensemble_paths = tuple(
            (ensemble,
             container_settings['scratch_ensembles'][ensemble])
            for ensemble in ensembles)
        self.smry_columns = sorted(
            list(
                get_summary_data(
                    ensemble_paths=self.ensemble_paths,
                    sampling=self.sampling,
                    column_keys=self.column_keys) .drop(
                    columns=[
                        'DATE',
                        'REAL',
                        'ENSEMBLE']) .columns))
        self.smry_vector_columns = tuple([col for col in self.smry_columns
                                          if not col.endswith('H')])
        self.smry_history_columns = tuple([col for col in self.smry_columns
                                           if col.endswith('H')])
        self.history_uncertainty = history_uncertainty
        self.set_callbacks(app)

    @property
    def layout(self):
        return html.Div([
            html.H2(self.title),
            html.P('Summary Vector:', style={'font-weight': 'bold'}),
            dcc.Dropdown(id=self.dropwdown_vector_id,
                         clearable=False,
                         options=[{'label': i, 'value': i}
                                  for i in self.smry_vector_columns],
                         value=self.smry_vector_columns[0]),
            html.P('Plot type:', style={'font-weight': 'bold'}),
            dcc.RadioItems(id=self.radio_plot_type_id,
                           options=[{'label': i, 'value': i}
                                    for i in ['Realizations', 'Statistics']],
                           value='Realizations'),
            dcc.Checklist(
                id=self.show_history_uncertainty_id,
                options=[{'label': 'Show history', 'value': 'SHOW_H'}],
                values=[],
            ),
            html.Div(id=self.chart_id)
        ])

    def set_callbacks(self, app):
        @app.callback(Output(self.chart_id, 'children'),
                      [Input(self.dropwdown_vector_id, 'value'),
                       Input(self.radio_plot_type_id, 'value'),
                       Input(self.show_history_uncertainty_id, 'values')])
        def update_plot(
                vector,
                summary_plot_type,
                show_history_uncertainty_id):
            if summary_plot_type == 'Realizations':
                return render_realization_plot(
                    ensemble_paths=self.ensemble_paths,
                    column_keys=self.column_keys,
                    sampling=self.sampling,
                    smry_history_columns=self.smry_history_columns,
                    history_uncertainty=self.history_uncertainty,
                    vector=vector,
                    show_history_uncertainty=show_history_uncertainty_id)
            if summary_plot_type == 'Statistics':
                return render_stat_plot(
                    ensemble_paths=self.ensemble_paths,
                    column_keys=self.column_keys,
                    sampling=self.sampling,
                    vector=vector,
                    show_history_uncertainty=show_history_uncertainty_id)

    def add_webvizstore(self):
        return [(get_summary_data,
                 [{'ensemble_paths': self.ensemble_paths,
                   'column_keys': self.column_keys,
                   'sampling': self.sampling,
                   'smry_history_columns': self.smry_history_columns,
                   'history_uncertainty': self.history_uncertainty}]),
                (get_summary_stats,
                 [{'ensemble_paths': self.ensemble_paths,
                   'column_keys': self.column_keys,
                   'sampling': self.sampling}])]


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_summary_data(ensemble_paths: tuple, sampling: str,
                     column_keys: tuple) -> pd.DataFrame:
    """ Loops over given ensemble paths, extracts smry-data and concates them
    into one big df. An additional column ENSEMBLE is added for each
    ens-path to seperate the ensambles.
    column_keys is converted to list as list-type is needed in
    .get_smry_stats()"""

    column_keys = list(column_keys) if isinstance(
        column_keys, (list, tuple)) else None

    smry_data = []
    for ens, ens_path in ensemble_paths:
        ens_smry_data = scratch_ensemble(
            ens, ens_path).get_smry(
                time_index=sampling, column_keys=column_keys)
        ens_smry_data['ENSEMBLE'] = ens
        smry_data.append(ens_smry_data)
    return pd.concat(smry_data)


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_summary_stats(ensemble_paths: tuple, sampling: str,
                      column_keys: tuple) -> pd.DataFrame:
    """ Loops over given ensemble paths, extracts smry-data and concates them
    into one big df. An additional column ENSEMBLE is added for each
    ens-path to seperate the ensambles.
    column_keys is converted to list as list-type is needed in
    .get_smry_stats()"""

    column_keys = list(column_keys) if isinstance(
        column_keys, (list, tuple)) else None

    smry_stats = []
    for ens, ens_path in ensemble_paths:
        ens_smry_stats = scratch_ensemble(
            ens, ens_path).get_smry_stats(
                time_index=sampling, column_keys=column_keys)
        ens_smry_stats['ENSEMBLE'] = ens
        smry_stats.append(ens_smry_stats)

    return pd.concat(smry_stats)


@cache.memoize(timeout=cache.TIMEOUT)
def render_realization_plot(ensemble_paths: tuple, sampling: str,
                            column_keys: tuple, vector: str,
                            smry_history_columns: tuple,
                            history_uncertainty: bool,
                            show_history_uncertainty: str):
    """ Creates scatter-plot-traces for choosen vector. One trace per
    realization will be created. If history-data are not subjeted to
    uncertainty only one traces per ensemble will be created for history_data.
    If there is no history-vector in for the given vector, no trace will be
    created. """

    cycle_list = itertools.cycle(DEFAULT_PLOTLY_COLORS)
    history_vector = (vector + 'H')

    if history_vector in smry_history_columns:
        smry_data = get_summary_data(
            ensemble_paths=ensemble_paths,
            column_keys=column_keys,
            sampling=sampling)[
                ['REAL', 'DATE', 'ENSEMBLE', vector, history_vector]]
    else:
        smry_data = get_summary_data(
            ensemble_paths=ensemble_paths,
            column_keys=column_keys,
            sampling=sampling)[
                ['REAL', 'DATE', 'ENSEMBLE', vector]]

    smry_data.dropna(subset=[vector])

    traces = []
    for ens in smry_data.ENSEMBLE.unique():
        smry_data_i = smry_data[smry_data['ENSEMBLE'] == ens]
        color = next(cycle_list)
        first_trace = {
            'x': smry_data_i[smry_data_i['REAL']
                             == smry_data_i.REAL.unique()[0]]['DATE'],
            'y': smry_data_i[smry_data_i['REAL']
                             == smry_data_i.REAL.unique()[0]][vector],
            'legendgroup': ens,
            'name': ens,
            'type': 'markers',
            'marker': {
                    'color': color
            },
            'showlegend': True
        }
        traces.append(first_trace)
        for real in smry_data_i.REAL.unique()[1:]:
            trace = {
                'x': smry_data_i[smry_data_i['REAL'] == real]['DATE'],
                'y': smry_data_i[smry_data_i['REAL'] == real][vector],
                'legendgroup': ens,
                'name': ens,
                'type': 'line',
                'marker': {
                    'color': color
                },
                'showlegend': False
            }
            traces.append(trace)

    if (history_vector in smry_history_columns
            and 'SHOW_H' in show_history_uncertainty):
        hist_trace = {
            'x': smry_data_i[smry_data_i['REAL'] == smry_data_i.REAL.unique(
            )[0]]['DATE'],
            'y': smry_data_i[smry_data_i['REAL'] == smry_data_i.REAL.unique(
            )[0]][history_vector],
            'legendgroup': 'History',
            'name': 'History',
            'type': 'markers',
            'marker': {
                    'color': 'red'
            },
            'showlegend': True
        }
        traces.append(hist_trace)
        if history_uncertainty:
            for real in smry_data_i.REAL.unique()[1:]:
                hist_trace = {
                    'x': smry_data_i[smry_data_i['REAL'] == real]['DATE'],
                    'y': smry_data_i[smry_data_i['REAL'] == real][history_vector],
                    'legendgroup': ens,
                    'name': ens,
                    'type': 'line',
                    'marker': {
                        'color': 'red'
                    },
                    'showlegend': False
                }
                traces.append(hist_trace)

    layout = {
        'hovermode': 'closest',
        'barmode': 'overlay',
        'bargap': 0.05,
        'xaxis': {'title': 'Date', 'family': 'Equinor'},
        'yaxis': {'title': vector, 'family': 'Equinor'},
        'font': {'family': 'Equinor'},
        'hoverlabel': {'font': {'family': 'Equinor'}},
    }

    return dcc.Graph(figure={'data': traces, 'layout': layout},
                     config={
                         'displaylogo': False,
                         'modeBarButtonsToRemove': ['sendDataToCloud']
    })


@cache.memoize(timeout=cache.TIMEOUT)
def render_stat_plot(ensemble_paths: tuple, sampling: str, column_keys: tuple,
                     vector: str, show_history_uncertainty: str):
    """Loops over ensemlbe_paths and creates one summary_statistics-plot per
    ensemble."""

    smry_stats = get_summary_stats(
        ensemble_paths=ensemble_paths,
        column_keys=column_keys,
        sampling=sampling)

    fan_chart_divs = []
    for ens in smry_stats.ENSEMBLE.unique():
        vector_stats = smry_stats[
            smry_stats['ENSEMBLE'] == ens][
                vector].unstack().transpose()
        vector_stats['name'] = vector
        vector_stats.rename(index=str, inplace=True,
                            columns={"minimum": "min", "maximum": "max"})
        fan_chart_divs.append(html.H5(ens))
        fan_chart_divs.append(
            html.Div(
                dcc.Graph(
                    id='graph-{}'.format(ens),
                    figure=FanChart(vector_stats.iterrows()),
                    config={
                        'displaylogo': False,
                        'modeBarButtonsToRemove': ['sendDataToCloud']
                    }
                )
            )
        )

    return fan_chart_divs
