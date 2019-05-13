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

    def __init__(
            self,
            app,
            container_settings,
            ensembles,
            column_keys=None,
            sampling: str = 'monthly',
            title: str = 'Simulation time series'):
        self.title = title
        self.dropwdown_vector_id = 'dropdown-vector-{}'.format(uuid4())
        self.column_keys = column_keys
        self.sampling = sampling
        self.radio_plot_type_id = 'radio-plot-type-{}'.format(uuid4())
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
            html.Div(id=self.chart_id)
        ])

    def set_callbacks(self, app):
        @app.callback(Output(self.chart_id, 'children'),
                      [Input(self.dropwdown_vector_id, 'value'),
                       Input(self.radio_plot_type_id, 'value')])
        def update_plot(vector, summary_plot_type):
            if summary_plot_type == 'Realizations':
                return render_realization_plot(
                    self.ensemble_paths,
                    self.column_keys,
                    self.sampling, vector)
            if summary_plot_type == 'Statistics':
                return render_stat_plot(
                    self.ensemble_paths,
                    self.column_keys,
                    self.sampling, vector)

    def add_webvizstore(self):
        # column_keys-list unhashable, therefore column_keys-tuple
        """The webviz store stores all decorated functions and thier output as
        files. The filenames are hashes of the function arguments."""
        return [(get_summary_data, [{'ensemble_paths': self.ensemble_paths,
                                     'column_keys': tuple(self.column_keys),
                                     'sampling': self.sampling}]),
                (get_summary_stats, [{'ensemble_paths': self.ensemble_paths,
                                      'column_keys': tuple(self.column_keys),
                                      'sampling': (self.sampling)}])]


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_summary_data(ensemble_paths: tuple,
                     sampling: str,
                     column_keys: tuple) -> pd.DataFrame:
    """ Loops over given ensemble paths, extracts smry-data and concates them
    into one big df. An additional column ENSEMBLE gets added for eacht ens-path
    to seperate the ensambles.
    note: Dash functions take positional args., so order matters. """

    # convert column_keys-tuple back to list
    column_keys = list(column_keys)

    ens_data_dfs = []

    for ensemble, ensemble_path in ensemble_paths:
        ensemble_df = scratch_ensemble(ensemble, ensemble_path).get_smry(
            time_index=sampling, column_keys=column_keys)
        ensemble_df['ENSEMBLE'] = ensemble
        ens_data_dfs.append(ensemble_df)

    return pd.concat(ens_data_dfs)


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_summary_stats(ensemble_paths: tuple,
                      column_keys: tuple,
                      sampling: str) -> pd.DataFrame:
    """ Loops over given ensemble paths, extracts smry-data and concates them
    into one big df. An additional column ENSEMBLE gets added for each
    enesmble-path to seperate the ensambles.
    note: Dash functions take positional args., so order matters. """

    # convert column_keys-tuple back to list
    column_keys = list(column_keys)

    df_ens_set = []
    for ensemble, path in ensemble_paths:
        stats = scratch_ensemble(ensemble, path).get_smry_stats(
            time_index=sampling, column_keys=column_keys)

        df_ens_set.append(stats)
    return pd.concat(df_ens_set)


# @cache.memoize(timeout=cache.TIMEOUT)
def render_realization_plot(ensemble_paths, sampling, column_keys, vector):
    """ Returns a dcc.Graph. Data a plotted from df returned by
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

    summary_data = get_summary_data(ensemble_paths, column_keys, sampling
                                    )[['REAL', 'DATE', 'ENSEMBLE', vector]]

    df = summary_data.dropna(subset=[vector])
    cycle_list = itertools.cycle(DEFAULT_PLOTLY_COLORS)

    traces = []

    # outer loop over enesmbles
    for ens in df.ENSEMBLE.unique():
        df_i = df[df['ENSEMBLE'] == ens]
        color = next(cycle_list)
        # 1st trace of a legendgroup with 'showlegend': True
        first_trace = {
            'x': df_i[df_i['REAL'] == df.REAL.unique()[0]]['DATE'],
            'y': df_i[df_i['REAL'] == df.REAL.unique()[0]][vector],
            'legendgroup': ens,
            'name': ens,
            'type': 'line',
            'marker': {
                    'color': color
            },
            'showlegend': True
        }
        traces.append(first_trace)
        # inner loop over traces within a legendgroup
        for real in df.REAL.unique()[1:]:
            trace = {
                'x': df_i[df_i['REAL'] == real]['DATE'],
                'y': df_i[df_i['REAL'] == real][vector],
                'legendgroup': ens,
                'name': ens,
                'type': 'line',
                'marker': {
                    'color': color
                },
                'showlegend': False
            }
            traces.append(trace)

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
def render_stat_plot(ensemble_paths, sampling, column_keys, vector):
    """returns a list of html.Divs (required by dash). One div per ensemble.
    Eachdiv includes a dcc.Graph(id, figure, config)."""

    # get data
    data = get_summary_stats(ensemble_paths, sampling, column_keys)

    # create a list of FanCharts to be plotted
    fan_chart_divs = []
    for ensemble in data.ENSEMBLE.unique():
        vector_stats = data[data['ENSEMBLE'] == ensemble][vector].unstack(
        ).transpose()
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
