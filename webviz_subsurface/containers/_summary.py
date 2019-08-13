import itertools
from uuid import uuid4
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_config.containers import WebvizContainer
from webviz_config.common_cache import cache
from plotly.colors import DEFAULT_PLOTLY_COLORS
import plotly.graph_objs as go
from webviz_subsurface.datainput import get_time_series_data, \
    get_time_series_statistics, get_time_series_fielgains


# Todo:
#   - caching
#   - fieldgains
#   - layout => griding
#   - button logic to boolean


# =============================================================================
# Container
# =============================================================================

class Summary(WebvizContainer):
    """Plot of time series data based on fmu-ensemble summary data.
    Data are loaded from scratch an process via fmu-ensemble utilities.

    Args:
        ensembles: key-value-pait = ensemble-name: ensemble-path
        column_keys: list = list of preselected vectors to be selectable
        sampling: str = time-index / time-steps of summary-data
    """

    def __init__(
            self,
            app,
            container_settings,
            ensembles,
            column_keys=None,
            sampling: str = 'monthly',
            base_ensembles: list = None,
            delta_ensembles: list = None):

        self.title = 'EnsembleSet'
        self.uid = f'{uuid4()}'
        self.time_index = sampling
        self.column_keys = tuple(column_keys) if isinstance(
            column_keys, (list, tuple)) else None
        self.ensemble_paths = tuple(
            (ensemble,
             container_settings['scratch_ensembles'][ensemble])
            for ensemble in ensembles)
        self.base_ensembles = tuple(base_ensembles if base_ensembles else [
            i[0] for i in self.ensemble_paths])
        self.delta_ensembles = tuple(delta_ensembles if delta_ensembles else [
            i[0] for i in self.ensemble_paths])
        self.set_callbacks(app)

    @property
    def base_ens(self):
        return self.ensemble_combinations[0]

    @property
    def delta_ens(self):
        return self.ensemble_combinations[1]

    @property
    def dropwdown_vector_id(self):
        return f'dropdown-vector-{self.uid}'

    @property
    def chart_id(self):
        return f'chart-id-{self.uid}'

    @property
    def tab_id(self):
        return f'_tab_id-{self.uid}'

    @property
    def chlst(self):
        return f'chlst-{self.uid}'

    @property
    def dropdown_iorens_id(self):
        return f'dropdown-iorens-{self.uid}'

    @property
    def dropdown_refens_id(self):
        return f'dropdown-refens-{self.uid}'

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

    @property
    def chlst_options(self):
        options = []
        options.append(['Fieldgains', 'show_fieldgains'])
        if len(self.smry_history_columns) > 0:
            options.append(['Show H-Vctr', 'show_h_vctr'])
        return options


# =============================================================================
# Layout
# =============================================================================

    @property
    def layout(self):
        return html.Div([
            html.H2(self.title),
            html.Div([
                html.Div([
                    html.P('Time Series:', style={'font-weight': 'bold'}),
                    dcc.Dropdown(id=self.dropwdown_vector_id,
                                 clearable=False,
                                 options=[{'label': i, 'value': i}
                                          for i in self.smry_vector_columns],
                                 value=self.smry_vector_columns[0]),
                    html.Div([
                        dcc.Checklist(
                            id=self.chlst,
                            options=[{'label': l, 'value': v}
                                     for l, v in self.chlst_options],
                            labelStyle={'display': 'inline-block'},
                            value=[],
                        ),
                        html.Div([
                            dcc.Dropdown(
                                id=self.dropdown_iorens_id,
                                placeholder="Base case",
                                options=[{'label': i, 'value': i}
                                         for i in self.base_ensembles]
                            ),
                            dcc.Dropdown(
                                id=self.dropdown_refens_id,
                                placeholder="Select ensembles",
                                options=[{'label': i, 'value': i}
                                         for i in self.delta_ensembles],
                                multi=True,
                            ),
                        ])
                    ]),
                ], style={'width': '20%', "float": "left"}),

                html.Div([
                    dcc.Tabs(id=self.tab_id, value='summary_data', children=[
                        dcc.Tab(label='Realizations', value='summary_data'),
                        dcc.Tab(label='Statistics', value='summary_stats'),
                    ]),
                    html.Div(id='tabs-content'),
                    html.Div(id=self.chart_id)
                ], style={'width': '80%', "float": "right"}),

            ]),
        ])


# =============================================================================
# Callbacks
# =============================================================================

    def set_callbacks(self, app):

        @app.callback(Output(self.chart_id, 'children'),
                      [Input(self.dropwdown_vector_id, 'value'),
                       Input(self.tab_id, 'value'),
                       Input(self.chlst, 'value'),
                       Input(self.dropdown_iorens_id, 'value'),
                       Input(self.dropdown_refens_id, 'value')])
        def update_plot(
                vector: str,
                plot_type: str,
                chlst: list,
                iorens: str,
                refens: str):

            show_history_vector = True if 'show_h_vctr' in chlst else False
            show_fieldgains = True if 'show_fieldgains' in chlst else False

            if plot_type == 'summary_data':

                return render_realization_plot(
                    ensemble_paths=self.ensemble_paths,
                    column_keys=self.column_keys,
                    time_index=self.time_index,
                    vector=vector,
                    ensemble_set_name=self.title,
                    smry_history_columns=self.smry_history_columns,
                    show_history_vector=show_history_vector,
                    show_fieldgains=show_fieldgains,
                    iorens=iorens,
                    refens=refens,
                    base_ensembles=self.base_ensembles,
                    delta_ensembles=self.delta_ensembles,
                )

            if plot_type == 'summary_stats':

                return render_stat_plot(
                    ensemble_paths=self.ensemble_paths,
                    column_keys=self.column_keys,
                    time_index=self.time_index,
                    vector=vector
                )

        @app.callback(Output('tabs-content', 'children'),
                      [Input('tabs', 'value')])
        def render_content(tab):
            if tab == 'tab-1':
                return html.Div([
                    html.H3('Tab content 1')
                ])
            elif tab == 'tab-2':
                return html.Div([
                    html.H3('Tab content 2')
                ])


# =============================================================================
# Webvizstore
# =============================================================================

    def add_webvizstore(self):
        return [(get_time_series_data,
                 [{'ensemble_paths': self.ensemble_paths,
                   'column_keys': self.column_keys,
                   'time_index': self.time_index,
                   'ensemble_set_name': self.title}]
                 ),
                (get_time_series_statistics,
                 [{'ensemble_paths': self.ensemble_paths,
                   'time_index': self.time_index,
                   'column_keys': self.column_keys}]
                 ),
                (get_time_series_fielgains,
                 [{'ensemble_paths': self.ensemble_paths,
                   'time_index': self.time_index,
                   'column_keys': self.column_keys,
                   'base_ensembles': self.base_ensembles,
                   'delta_ensembles': self.delta_ensembles,
                   'ensemble_set_name': self.title}]
                 ),
                ]


# =============================================================================
# Render functions
# =============================================================================

@cache.memoize(timeout=cache.TIMEOUT)
def render_realization_plot(
        ensemble_paths: tuple,
        time_index: str,
        column_keys: tuple,
        vector: str,
        ensemble_set_name: str,
        smry_history_columns: tuple,
        show_history_vector: bool,
        show_fieldgains: bool,
        iorens: str,
        refens: str,
        base_ensembles: tuple,
        delta_ensembles: tuple
    ):
    """ Callback for a dcc.Graph-obj that shows traces (one per realization
    and one color per tracegroup <=> ensemble) of a selected vector per
    selected time-step.

    Args:
        ensemble_paths: tuple = list of ensemble-paths
        time_index: str = time-index
        column_keys: tuple = tuple of pre selected-vectors
        vector: str = vector to be plotted
        ensemble_set_name: str = name of enesmble-set
        smry_history_columns: tuple = tuple of history-vectors
        show_history_vector: bool = show history vector (if present)
        show_fieldgains: bool = shwo fieldgains
    Retuns:
        dcc.Graph (scatter-plot) of summary-data aggregated over given
        ensembles. x: time, y: vector-value
    """

    cycle_list = itertools.cycle(DEFAULT_PLOTLY_COLORS)
    history_vector = (vector + 'H')

    # process data ------------------------------------------------------------
    if history_vector in smry_history_columns:

        smry_data = get_time_series_data(
            ensemble_paths=ensemble_paths,
            column_keys=column_keys,
            time_index=time_index,
            ensemble_set_name=ensemble_set_name)[
                ['REAL', 'DATE', 'ENSEMBLE', vector, history_vector]]

    else:

        smry_data = get_time_series_data(
            ensemble_paths=ensemble_paths,
            column_keys=column_keys,
            time_index=time_index,
            ensemble_set_name=ensemble_set_name)[
                ['REAL', 'DATE', 'ENSEMBLE', vector]]

    if show_fieldgains:
        field_gains = get_time_series_fielgains(
            ensemble_paths=ensemble_paths,
            time_index=time_index,
            column_keys=column_keys,
            base_ensembles=base_ensembles,
            delta_ensembles=delta_ensembles,
            ensemble_set_name=ensemble_set_name,
        )


    # plot traces -------------------------------------------------------------
    plot_traces = []
    if not (show_fieldgains and iorens and refens):
        for ens in smry_data.ENSEMBLE.unique():

            plot_traces += trace_group(
                ens_smry_data=smry_data[smry_data['ENSEMBLE'] == ens],
                ens=ens,
                vector=vector,
                color=next(cycle_list))

            if (history_vector in smry_history_columns
                    and show_history_vector):

                plot_traces += trace_group(
                    ens_smry_data=smry_data[smry_data['ENSEMBLE'] == ens],
                    ens=ens,
                    vector=history_vector,
                    color='black')


    if (show_fieldgains and iorens and refens):
        for i in refens:

            compared_ensembles = f'{iorens} - {i}'
            field_gain = field_gains[
                field_gains['IROENS - REFENS'] == compared_ensembles
            ]
            field_gain[['REAL', 'DATE', vector]]

            plot_traces += trace_group(
                ens_smry_data=field_gain,
                ens=f'{iorens} - {i}',
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


@cache.memoize(timeout=cache.TIMEOUT)
def render_stat_plot(
        ensemble_paths: tuple,
        time_index: str,
        column_keys: tuple,
        vector: str):
    """ Render statistics plot renders one fanchart-plot per given ensemble.

    Args:
        ens_smry_data: pd.DataFrame = Dataframe containing all ensmelbes.
        time_index: str = time-index
        column_keys: tuple = tuple of pre selected-vectors
        vector: str = vector to be plotted
    Returns:
        dcc.Graph objects as fancharts of summary statistics.
    """

    smry_stats = get_time_series_statistics(
        ensemble_paths=ensemble_paths,
        column_keys=column_keys,
        time_index=time_index)

    plotly_colors_rgb = itertools.cycle([
        (31, 119, 180),
        (255, 127, 14),
        (44, 160, 44),
        (214, 39, 40),
        (148, 103, 189),
        (140, 86, 75),
        (227, 119, 194),
        (127, 127, 127),
        (188, 189, 34),
        (23, 190, 207)
    ])

    data = []
    for ens in smry_stats.ENSEMBLE.unique():
        vector_stats = smry_stats[
            smry_stats['ENSEMBLE'] == ens]
        data += time_series_confidence_interval_traces(
            vector_stats=vector_stats[vector],
            color_rgb=next(plotly_colors_rgb),
            legend_group=ens
        )

    layout = go.Layout(
        yaxis=dict(title=vector),
        title='Time series statistics')

    return dcc.Graph(figure={'data': data, 'layout': layout},
                     config={
                         'displaylogo': False,
                         'modeBarButtonsToRemove': ['sendDataToCloud']})


# =============================================================================
# Auxiliary functions
# =============================================================================

def trace_group(ens_smry_data, ens, vector, color):
    """ Returns a plotly-graph-trace-group with one color and one name.
    The first trace gets plotted individually as is show up in the legend
    to represent the trace group.

    Args:
        ens_smry_data: pd.DataFrame = Dataframe containing all ensmelbes.
        ens: str = ensemble to be plotted
        vecotr: str = vector to be plotted
        color: str = trace color
    Returns:
        plotly-graph-obj-tracegroup
    """

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


def time_series_confidence_interval_traces(
        vector_stats,
        color_rgb,
        legend_group
    ):

    r, g, b = color_rgb

    trace_maximum = go.Scatter(
        name='maximum',
        x=vector_stats['maximum'].index.tolist(),
        y=vector_stats['maximum'].values,
        mode='lines',
        line=dict(width=0),
        legendgroup=legend_group,
        showlegend=False,
    )

    trace_p10 = go.Scatter(
        name='p10',
        x=vector_stats['p10'].index.tolist(),
        y=vector_stats['p10'].values,
        mode='lines',
        fill='tonexty',
        fillcolor='rgba({},{},{},{})'.format(r, g, b, 0.3),
        line=dict(width=0),
        legendgroup=legend_group,
        showlegend=False,
    )

    trace_mean = go.Scatter(
        name=legend_group,
        x=vector_stats['mean'].index.tolist(),
        y=vector_stats['mean'].values,
        mode='lines',
        fill='tonexty',
        fillcolor='rgba({},{},{},{})'.format(r, g, b, 0.3),
        line=dict(color='rgba({},{},{},{})'.format(r, g, b, 1)),
        legendgroup=legend_group,
        showlegend=True,
    )

    trace_p90 = go.Scatter(
        name='p90',
        x=vector_stats['p90'].index.tolist(),
        y=vector_stats['p90'].values,
        mode='lines',
        fill='tonexty',
        fillcolor='rgba({},{},{},{})'.format(r, g, b, 0.3),
        line=dict(width=0),
        legendgroup=legend_group,
        showlegend=False
    )

    trace_minimum = go.Scatter(
        name='minimum',
        x=vector_stats['minimum'].index.tolist(),
        y=vector_stats['minimum'].values,
        mode='lines',
        fill='tonexty',
        fillcolor='rgba({},{},{},{})'.format(r, g, b, 0.3),
        line=dict(width=0),
        legendgroup=legend_group,
        showlegend=False,
    )

    return [
        trace_maximum,
        trace_p10,
        trace_mean,
        trace_p90,
        trace_minimum
    ]
