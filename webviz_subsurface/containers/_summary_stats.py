from uuid import uuid4
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_plotly.graph_objs import FanChart
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
from ..datainput import scratch_ensemble
from plotly.colors import DEFAULT_PLOTLY_COLORS
import itertools


class SummaryStats:

    """
    Summary statistics
    ==================

    Provides:
      1. Summary data plot (y: vector, x: timeseries, traces: realization-i)
      2. Statistics plot (y: vector, x: timeseries, fanchart of ensemble-i
                          min, max, mean, p10, p90)

    Args:
    -----
      * `ensemble`: Which ensembles in `container_settings` to visualize.
        -> list of ensemble paths (can be only one)
      * `column_keys`: list of pre defined vectors to visualize. Default is
        `none`
      * `sampling`: Optional. Either `monthly` or `yearly`. Default is
        `monthly`.
      * `title`: Optional title for the container.

    Logic:
    ------
      Data:
        Ensembles are stored as one big concated dataframe including a columns
        "ENSEMBLE" to identify them.

      Loading data:
        get_summary_data or get_summary_stats load data from scratch. After the
        functions got called the first time the result gets cached.

      Accessing data:
        Calling get_summary_data with the same input parameter will return the
        memoized dataframe.
    """

    def __init__(self, app, container_settings, ensembles, column_keys=None,
                 history_uncertainty: bool = False, sampling: str = 'monthly',
                 title: str = 'Simulation time series'):

        self.title = title
        self.checklist_show_H_id = 'checklist-show-H-{}'.format(uuid4())
        self.dropwdown_vector_id = 'dropdown-vector-{}'.format(uuid4())
        self.column_keys = tuple(column_keys) if isinstance(
            column_keys, (list, tuple)) else None
        self.sampling = sampling
        self.radio_plot_type_id = 'radio-plot-type-{}'.format(uuid4())
        self.chart_id = 'chart-id-{}'.format(uuid4())
        self.H_vctr_uncertainty = history_uncertainty

        self.ensemble_paths = tuple(
            (ensemble,
             container_settings['scratch_ensembles'][ensemble])
            for ensemble in ensembles)

        smry_columns_lst = sorted(
            list(
                get_summary_data(
                    ensemble_paths=self.ensemble_paths,
                    sampling=self.sampling,
                    column_keys=self.column_keys).drop(
                    columns=[
                        'DATE',
                        'REAL',
                        'ENSEMBLE']).columns))
        self.smry_columns = [column for column in smry_columns_lst
                             if not column.endswith('H')]
        self.smry_columns_H = [column for column in smry_columns_lst
                               if column.endswith('H')]

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
            dcc.Checklist(
                id=self.checklist_show_H_id,
                options=[
                    {'label': 'Show *H', 'value': 'SHOW_H'}
                ],
                values=[],
            ),
            html.Div(id=self.chart_id)
        ])

    def set_callbacks(self, app):
        @app.callback(Output(self.chart_id, 'children'),
                      [Input(self.dropwdown_vector_id, 'value'),
                       Input(self.radio_plot_type_id, 'value'),
                       Input(self.checklist_show_H_id, 'values')])
        def update_plot(vector, summary_plot_type, checklist_show_H_id):
            if summary_plot_type == 'Realizations':
                return render_realization_plot(
                    ensemble_paths=self.ensemble_paths,
                    column_keys=self.column_keys,
                    sampling=self.sampling,
                    smry_columns_H=self.smry_columns_H,
                    vector=vector,
                    checklist_show_H_id=checklist_show_H_id,
                    H_vctr_uncertainty=self.H_vctr_uncertainty)
            if summary_plot_type == 'Statistics':
                return render_stat_plot(
                    ensemble_paths=self.ensemble_paths,
                    column_keys=self.column_keys,
                    sampling=self.sampling,
                    vector=vector)

    def add_webvizstore(self):
        return [(get_summary_data, [{'ensemble_paths': self.ensemble_paths,
                                     'column_keys': self.column_keys,
                                     'sampling': self.sampling,
                                     'smry_columns_H': self.smry_columns_H}]),
                (get_summary_stats, [{'ensemble_paths': self.ensemble_paths,
                                      'column_keys': self.column_keys,
                                      'sampling': (self.sampling)}])]


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_summary_data(ensemble_paths: tuple, sampling: str,
                     column_keys: tuple) -> pd.DataFrame:
    """ Loops over given ensemble paths, extracts smry-data and concates them
    into one big df. An additional column ENSEMBLE gets added for eacht
    ens-path to seperate the ensambles.
    note: Dash functions take positional args., so order matters. """

    # convert column_keys-tuple back to list
    column_keys = list(column_keys) if isinstance(column_keys, tuple) else None

    # create a list containing ensemble-dataframs + ['ENSEMBLE'] column
    smry_data_dfs = []
    for ensemble, ensemble_path in ensemble_paths:
        smry_data_df = scratch_ensemble(ensemble, ensemble_path).get_smry(
            time_index=sampling, column_keys=column_keys)
        smry_data_df['ENSEMBLE'] = ensemble
        smry_data_dfs.append(smry_data_df)

    smry_data_df = pd.concat(smry_data_dfs)

    return pd.concat(smry_data_dfs)


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_summary_stats(ensemble_paths: tuple, sampling: str,
                      column_keys: tuple) -> pd.DataFrame:
    """ Loops over given ensemble paths, extracts smry-data and concates them
    into one big df. An additional column ENSEMBLE gets added for each
    enesmble-path to seperate the ensambles.
    note: Dash functions take positional args., so order matters. """

    # convert column_keys-tuple back to list
    column_keys = list(column_keys) if isinstance(column_keys, tuple) else None

    smry_stats_dfs = []
    for ensemble, ensemble_path in ensemble_paths:
        smry_stats_df = scratch_ensemble(
            ensemble, ensemble_path).get_smry_stats(time_index=sampling,
                                                    column_keys=column_keys)
        smry_stats_df['ENSEMBLE'] = ensemble
        smry_stats_dfs.append(smry_stats_df)

    return pd.concat(smry_stats_dfs)


@cache.memoize(timeout=cache.TIMEOUT)
def render_realization_plot(ensemble_paths: tuple, sampling: str,
                            column_keys: tuple, smry_columns_H: list,
                            vector: str, checklist_show_H_id: str,
                            H_vctr_uncertainty: bool):
    """
    Returns a dcc.Graph. Data a plotted from df returned by
    get_summary_data() Callback from dropwdown_vector_id changes the vector
    attribute. Rest is defined in the config or part of the code.
    Rows including NaN values in the vector columns get dropped.

    Plot is a selection of traces. There are several trace-groups, one per
    ensemble. These are created in the outer loop and get assigned a color
    and a filtered df_i, filtered by currently selected ensemble.
    The first trace is created with showlegend set to True to get be shown
    in the legend. The inner-loop creates traces by looping over the
    realizations within the filtered df_i and appends them to the total list
    of traces. Theses traces have showlegend set to false to avid an overly
    populated legend.
    """
    # "cycle" in case n_ensembles > n_DEFAULT_PLOTLY_COLORS
    cycle_list = itertools.cycle(DEFAULT_PLOTLY_COLORS)

    vector_H = (vector + 'H')

    smry_data_unfiltered = get_summary_data(ensemble_paths=ensemble_paths,
                                            column_keys=column_keys,
                                            sampling=sampling)

    if vector_H in smry_columns_H:
        smry_data_filtered = smry_data_unfiltered[['REAL', 'DATE', 'ENSEMBLE',
                                                   vector, vector_H]
                                                  ].dropna(subset=[vector])

    else:
        smry_data_filtered = smry_data_unfiltered[['REAL', 'DATE', 'ENSEMBLE',
                                                   vector]
                                                  ].dropna(subset=[vector])

    traces = []
    for ens in smry_data_filtered.ENSEMBLE.unique():
        smry_data_i = smry_data_filtered[smry_data_filtered['ENSEMBLE'] == ens]
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

    if (vector_H in smry_columns_H and 'SHOW_H' in checklist_show_H_id):

        if H_vctr_uncertainty:

            H_trace = {
                'x': smry_data_i[smry_data_i['REAL']
                                 == smry_data_i.REAL.unique()[0]]['DATE'],
                'y': smry_data_i[smry_data_i['REAL']
                                 == smry_data_i.REAL.unique()[0]][vector],
                'legendgroup': '*H',
                'name': '*H',
                'type': 'markers',
                'marker': {
                        'color': 'black'
                },
                'showlegend': True
            }
            traces.append(H_trace)

        for real in smry_data_i.REAL.unique()[1:]:
            H_trace = {
                'x': smry_data_i[smry_data_i['REAL'] == real]['DATE'],
                'y': smry_data_i[smry_data_i['REAL'] == real][vector],
                'legendgroup': ens,
                'name': ens,
                'type': 'line',
                'marker': {
                    'color': 'black'
                },
                'showlegend': False
            }
            traces.append(trace)

        else:

            H_trace = {
                'x': smry_data_i[smry_data_i['REAL']
                                 == smry_data_i.REAL.unique()[0]]['DATE'],
                'y': smry_data_i[smry_data_i['REAL']
                                 == smry_data_i.REAL.unique()[0]][vector_H],
                'legendgroup': '*H',
                'name': '*H',
                'type': 'markers',
                'marker': {
                        'color': 'black'
                },
                'showlegend': True
            }
            traces.append(H_trace)

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
                     vector: str):
    """returns a list of html.Divs (required by dash). One div per ensemble.
    Eachdiv includes a dcc.Graph(id, figure, config)."""

    # get smry_stats
    smry_stats = get_summary_stats(ensemble_paths=ensemble_paths,
                                   column_keys=column_keys,
                                   sampling=sampling,)

    # create a list of FanCharts to be plotted
    fan_chart_divs = []
    for ensemble in smry_stats.ENSEMBLE.unique():
        vector_stats = smry_stats[smry_stats['ENSEMBLE']
                                  == ensemble][vector].unstack().transpose()
        vector_stats['name'] = vector
        vector_stats.rename(index=str, inplace=True,
                            columns={"minimum": "min", "maximum": "max"})
        fan_chart_divs.append(html.H5(ensemble))
        fan_chart_divs.append(
            html.Div(
                dcc.Graph(
                    id='graph-{}'.format(ensemble),
                    figure=FanChart(vector_stats.iterrows()),
                    config={
                        'displaylogo': False,
                        'modeBarButtonsToRemove': ['sendDataToCloud']
                    }
                )
            )
        )

    return fan_chart_divs
