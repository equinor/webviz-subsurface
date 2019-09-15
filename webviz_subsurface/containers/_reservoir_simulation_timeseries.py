import itertools
from uuid import uuid4
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output, State
from webviz_config.containers import WebvizContainer
from webviz_config.common_cache import cache
from plotly.colors import DEFAULT_PLOTLY_COLORS
import plotly.graph_objs as go
from webviz_subsurface.datainput import get_time_series_data, \
    get_time_series_statistics, get_time_series_delta_ens, \
    get_time_series_delta_ens_stats


# =============================================================================
# Container
# =============================================================================

class ReservoirSimulationTimeSeries(WebvizContainer):
    '''### Time series from reservoir simulations

* `ensembles`: Which ensembles in `container_settings` to visualize.
* `column_keys`: List of vectors to extract. If not given, all vectors
                 from the simulations will be extracted. Wild card asterisk *
                 can be used.
* `sampling`: Time separation between extracted values. Can be e.g. `monthly`
              or `yearly`.
* `base_ensembles`: List of ensembles to use as base ensemble in delta
                    calculations.
* `delta_ensembles`: List of ensembles to be compared with base ensemble.
'''

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
        self.dropwdown_vector_id = f'dropdown-vector-{self.uid}'
        self.chart_id = f'chart-id-{self.uid}'
        self.tab_id = f'_tab_id-{self.uid}'
        self.chlst = f'chlst-{self.uid}'
        self.dropdown_iorens_id = f'dropdown-iorens-{self.uid}'
        self.dropdown_refens_id = f'dropdown-refens-{self.uid}'
        self.show_ens_selectors = f'show-ens-selectors-{self.uid}'
        self.vector_columns = sorted(
            list(
                get_time_series_data(
                    ensemble_paths=self.ensemble_paths,
                    time_index=self.time_index,
                    column_keys=self.column_keys).drop(
                        columns=[
                            'DATE',
                            'REAL',
                            'ENSEMBLE']).columns))
        self.history_vctr_cols = tuple(
            [vctr + 'H' for vctr in self.vector_columns
             if vctr + 'H' in self.vector_columns])
        self.vctr_cols_no_hist = tuple(
            [vctr for vctr in self.vector_columns
             if vctr not in self.history_vctr_cols])
        self.set_callbacks(app)

    @property
    def base_ens(self):
        """ extracts base-ensemble from passed ensemble-combinations list"""
        return self.ensemble_combinations[0]

    @property
    def delta_ens(self):
        """ extracts delta-ensemble from passed ensemble-combinations list """
        return self.ensemble_combinations[1]


# =============================================================================
# Layout
# =============================================================================

    @property
    def layout(self):
        return html.Div([
            html.Div([
                html.Div([
                    dcc.Dropdown(id=self.dropwdown_vector_id,
                                 clearable=False,
                                 options=[{'label': i, 'value': i}
                                          for i in self.vctr_cols_no_hist],
                                 value=self.vctr_cols_no_hist[0]),
                    html.Div([
                        dcc.Checklist(
                            id=self.chlst,
                            options=[{
                                'label': 'Delta time series',
                                'value': 'show_delta_series'
                            }],
                            labelStyle={'display': 'inline-block'},
                            value=[],
                        ),
                        html.Div(id=self.show_ens_selectors, children=[
                            dcc.Dropdown(
                                id=self.dropdown_iorens_id,
                                placeholder='Base case',
                                options=[{'label': i, 'value': i}
                                         for i in self.base_ensembles]
                            ),
                            dcc.Dropdown(
                                id=self.dropdown_refens_id,
                                placeholder='Select ensembles',
                                options=[{'label': i, 'value': i}
                                         for i in self.delta_ensembles],
                                multi=True,
                            ),
                        ], style={'display': 'none'}),
                    ]),
                ], style={'width': '20%', 'float': 'left'}),

                html.Div([
                    dcc.Tabs(id=self.tab_id, value='summary_data', children=[
                        dcc.Tab(label='Realizations', value='summary_data'),
                        dcc.Tab(label='Statistics', value='summary_stats'),
                    ]),
                    html.Div(id='tabs-content'),
                    html.Div(id=self.chart_id)
                ], style={'width': '80%', 'float': 'right'}),

            ]),
        ])


# =============================================================================
# Callbacks
# =============================================================================

    def set_callbacks(self, app):

        @app.callback(Output(self.show_ens_selectors, 'style'),
                      [Input(self.chlst, 'value')])
        def _func_show_ens_selectors(chlst: list):
            """ callback to update the styling of div that includes the
            ensemble selectors. The styling switches to hiden when Delta
            time series is not selected.

            Input:
                checklist values: list of strings = selected options
            Output:
                html.Div(...styling): dictionary describing styling
            """
            return {} if 'show_delta_series' in chlst else {'display': 'none'}

        @app.callback(Output(self.chlst, 'options'),
                      [Input(self.dropwdown_vector_id, 'value')])
        def _update_chlst(vctr: str):
            """ callback to update checklist options to include available
            plot options.

            Input:
                dropdown(vector selection): str = selected vector
            Output:
                checklist values: list of strings = selectable options
            """

            options = []
            options.append(['Delta time series', 'show_delta_series'])
            if vctr + 'H' in self.history_vctr_cols:
                options.append(['Show H-Vctr', 'show_h_vctr'])

            return [{'label': label, 'value': value}
                    for label, value in options]

        @app.callback(Output(self.chart_id, 'children'),
                      [Input(self.dropwdown_vector_id, 'value'),
                       Input(self.tab_id, 'value'),
                       Input(self.chlst, 'value'),
                       Input(self.dropdown_iorens_id, 'value'),
                       Input(self.dropdown_refens_id, 'value')])
        def _update_plot(
                vector: str,
                plot_type: str,
                chlst: list,
                iorens: str,
                refens: str):
            """ main plot

            Depending on selected tab a different type of plot gets rendered.
            *vals get calcualted within render-func.

            Input:
                dropdown(vector selection): str = selected vector
                tab: str = selected tab => for plot-type
                checklist values: list of strings = selectable options
                dropdown iorens: str = base-ensemlbe
                dropdown refens: list(str) = selected ensembles
            Output:
                wcc.Graph
            """

            show_history_vector = 'show_h_vctr' in chlst
            show_delta_series = 'show_delta_series' in chlst

            if plot_type == 'summary_data':

                return render_realization_plot(
                    ensemble_paths=self.ensemble_paths,
                    column_keys=self.column_keys,
                    time_index=self.time_index,
                    vector=vector,
                    ensemble_set_name=self.title,
                    history_vctr_cols=self.history_vctr_cols,
                    show_history_vector=show_history_vector,
                    show_delta_series=show_delta_series,
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
                    ensemble_set_name=self.title,
                    vector=vector,
                    show_delta_series=show_delta_series,
                    iorens=iorens,
                    refens=refens,
                    base_ensembles=self.base_ensembles,
                    delta_ensembles=self.delta_ensembles,
                )

        @app.callback(self.container_data_output,
                      [self.container_data_requested],
                      [State(self.tab_id, 'value'),
                       State(self.chlst, 'value')])
        def _user_download_data(
                data_requested,
                plot_type: str,
                chlst: list):
            """ Callback to download data as .csv (Summary)

                Reads summary data from scratch into memory as ps.DataFrame and
                stores them to .cvs

                Args:
                    data_requesed: button-click to fire the download request
                    tab: str = current selected tab
                    chlst: list = list of selected plot options [
                        delta_ens, history_vctr]
                Returns:
                    summary.csv: .csv stored to ~/Downloads
            """

            show_delta_series = 'show_delta_series' in chlst

            if plot_type == 'summary_data':

                if show_delta_series:

                    file_name = 'delta_time_series'
                    requested_data = get_time_series_delta_ens(
                        ensemble_paths=self.ensemble_paths,
                        time_index=self.time_index,
                        column_keys=self.column_keys,
                        base_ensembles=self.base_ensembles,
                        delta_ensembles=self.delta_ensembles,
                        ensemble_set_name=self.title,
                    )

                else:

                    file_name = 'time_series'
                    requested_data = get_time_series_data(
                        ensemble_paths=self.ensemble_paths,
                        column_keys=self.column_keys,
                        time_index=self.time_index,
                        ensemble_set_name=self.title
                    )

            if plot_type == 'summary_stats':

                if show_delta_series:

                    file_name = 'delta_time_series_statistics'
                    requested_data = get_time_series_delta_ens_stats(
                        ensemble_paths=self.ensemble_paths,
                        column_keys=self.column_keys,
                        time_index=self.time_index,
                        base_ensembles=self.base_ensembles,
                        delta_ensembles=self.delta_ensembles,
                        ensemble_set_name=self.title,
                    )

                else:

                    file_name = 'delta_time_series_statistics'
                    requested_data = get_time_series_statistics(
                        ensemble_paths=self.ensemble_paths,
                        column_keys=self.column_keys,
                        time_index=self.time_index,
                    )

            return WebvizContainer.container_data_compress(
                [{'filename': f'{file_name}.csv',
                  'content': requested_data.to_csv()}]
            ) if data_requested else ''


# =============================================================================
# Webvizstore
# =============================================================================

    def add_webvizstore(self):

        """ selections of functions to be added to webvizstore. They include
        data to be laoded and values to be calculated for the plots.
        """

        return [
            (get_time_series_data,
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
            (get_time_series_delta_ens,
             [{'ensemble_paths': self.ensemble_paths,
               'time_index': self.time_index,
               'column_keys': self.column_keys,
               'base_ensembles': self.base_ensembles,
               'delta_ensembles': self.delta_ensembles,
               'ensemble_set_name': self.title}]
             ),
            (get_time_series_delta_ens_stats,
             [{'ensemble_paths': self.ensemble_paths,
               'time_index': self.time_index,
               'column_keys': self.column_keys,
               'base_ensembles': self.base_ensembles,
               'delta_ensembles': self.delta_ensembles,
               'ensemble_set_name': self.title}]
             )
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
        history_vctr_cols: tuple,
        show_history_vector: bool,
        show_delta_series: bool,
        iorens: str,
        refens: str,
        base_ensembles: tuple,
        delta_ensembles: tuple
):
    """ Callback for a Plotly Graph-obj that shows traces (one per realization
    and one color per tracegroup <=> ensemble) of a selected vector per
    selected time-step.

    Args:
        ensemble_paths: tuple = list of ensemble-paths
        time_index: str = time-index
        column_keys: tuple = tuple of pre selected-vectors
        vector: str = vector to be plotted
        ensemble_set_name: str = name of enesmble-set
        history_vctr_cols: tuple = tuple of history-vectors
        show_history_vector: bool = show history vector (if present)
        show_delta_series: bool = shwo Delta time series
        iorens: str = selcted divergent ensembles
        refens: str = selected base or refernce ensemble
        base_ensembles: tuple = tuple of available divergent ensembles
        delta_ensembles: tuple = tuple of available base or refernce ensembles
    Retuns:
        wcc.Graph (scatter-plot) of summary-data aggregated over given
        ensembles. x: time, y: vector-value
    """

    cycle_list = itertools.cycle(DEFAULT_PLOTLY_COLORS)
    history_vector = (vector + 'H')

    # process data ------------------------------------------------------------
    if history_vector in history_vctr_cols:

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

    if show_delta_series:
        delta_vals = get_time_series_delta_ens(
            ensemble_paths=ensemble_paths,
            time_index=time_index,
            column_keys=column_keys,
            base_ensembles=base_ensembles,
            delta_ensembles=delta_ensembles,
            ensemble_set_name=ensemble_set_name,
        )

    # plot traces -------------------------------------------------------------
    plot_traces = []
    if not (show_delta_series and iorens and refens):
        for ens in smry_data.ENSEMBLE.unique():

            plot_traces += trace_group(
                ens_smry_data=smry_data[smry_data['ENSEMBLE'] == ens],
                ens=ens,
                vector=vector,
                color=next(cycle_list))

            if (history_vector in history_vctr_cols
                    and show_history_vector):

                plot_traces += trace_group(
                    ens_smry_data=smry_data[smry_data['ENSEMBLE'] == ens],
                    ens=ens,
                    vector=history_vector,
                    color='black')

    if (show_delta_series and iorens and refens):
        for i in refens:

            compared_ensembles = f'{iorens} - {i}'
            delta_val = delta_vals[
                delta_vals['IROENS - REFENS'] == compared_ensembles
            ]

            plot_traces += trace_group(
                ens_smry_data=delta_val[['REAL', 'DATE', vector]],
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

    return wcc.Graph(figure={'data': plot_traces, 'layout': layout})


@cache.memoize(timeout=cache.TIMEOUT)
def render_stat_plot(
        ensemble_paths: tuple,
        time_index: str,
        column_keys: tuple,
        vector: str,
        ensemble_set_name: str,
        show_delta_series: bool,
        iorens: str,
        refens: str,
        base_ensembles: tuple,
        delta_ensembles: tuple):
    """ Render statistics plot renders one fanchart-plot per given ensemble.

    Args:
        ensemble_paths: tuple = list of ensemble-paths
        time_index: str = time-index
        column_keys: tuple = tuple of pre selected-vectors
        vector: str = vector to be plotted
        ensemble_set_name: str = name of enesmble-set
        show_delta_series: bool = shwo Delta time series
        iorens: str = selcted divergent ensembles
        refens: str = selected base or refernce ensemble
        base_ensembles: tuple = tuple of available divergent ensembles
        delta_ensembles: tuple = tuple of available base or refernce ensembles
    Returns:
        wcc.Graph objects as fancharts of summary statistics.
    """

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

    if not (show_delta_series and iorens and refens):

        smry_stats = get_time_series_statistics(
            ensemble_paths=ensemble_paths,
            column_keys=column_keys,
            time_index=time_index
        )

        data = []
        for ens in smry_stats.ENSEMBLE.unique():
            vector_stats = smry_stats[
                smry_stats['ENSEMBLE'] == ens]
            data += time_series_confidence_interval_traces(
                vector_stats=vector_stats[vector],
                color_rgb=next(plotly_colors_rgb),
                legend_group=ens
            )

    if (show_delta_series and iorens and refens):

        delta_time_series_stats = get_time_series_delta_ens_stats(
            ensemble_paths=ensemble_paths,
            column_keys=column_keys,
            time_index=time_index,
            base_ensembles=base_ensembles,
            delta_ensembles=delta_ensembles,
            ensemble_set_name=ensemble_set_name,
        )

        data = []
        for i in refens:

            compared_ensembles = f'{iorens} - {i}'
            delta_val_stats = delta_time_series_stats[
                delta_time_series_stats['IROENS - REFENS']
                == compared_ensembles
            ]

            data += time_series_confidence_interval_traces(
                vector_stats=delta_val_stats[vector],
                color_rgb=next(plotly_colors_rgb),
                legend_group=compared_ensembles
            )

    layout = go.Layout(
        yaxis=dict(title=vector),
    )

    return wcc.Graph(figure={'data': data, 'layout': layout})


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
        'hovertext': f'Realization: {ens_smry_data.REAL.unique()[0]}',
        'hoverinfo': "y+x+text",
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
            'hovertext': f'Realization: {real}',
            'hoverinfo': "y+x+text",
            'name': ens,
            'type': 'line',
            'marker': {
                'color': color
            },
            'showlegend': False
        })

    return ens_traces


def single_trace(
        ens_smry_data,
        ens: str,
        vector: str,
        color: str):
    """ function to create a single trace that shows up in the legend.

    Args:
        smry_data: pd.df = calculated summary data (fmu-ensemble)
        ens: str = selected ensemble
        vector: str = selected vector to be plotted; passed as key
        color str = color
    Returns:
        trace-obj to be plotted in a plotly.fig
    """

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
        color_rgb: list,
        legend_group: str):
    """ function to create a convidence interval set of a selected ensemble.

    Args:
        smry_data: pd.df = calculated summary data (fmu-ensemble)
        color (r: int, g:int, b:int) = rgb of color to be ploted
        legend_group: str = selected ensemble
    Returns:
        list if trace-obj representing min, max, p10, p90 and mean
    """

    r, g, b = color_rgb

    trace_maximum = go.Scatter(
        name='maximum',
        x=vector_stats['maximum'].index.tolist(),
        y=vector_stats['maximum'].values,
        mode='lines',
        line={
            'width': 0,
            'color': f'rgba({r}, {g}, {b}, 1)'
        },
        legendgroup=legend_group,
        showlegend=False,
    )

    trace_p10 = go.Scatter(
        name='p10',
        x=vector_stats['p10'].index.tolist(),
        y=vector_stats['p10'].values,
        mode='lines',
        fill='tonexty',
        fillcolor=f'rgba({r}, {g}, {b}, 0.3)',
        line={
            'width': 0,
            'color': f'rgba({r}, {g}, {b}, 1)'
        },
        legendgroup=legend_group,
        showlegend=False,
    )

    trace_mean = go.Scatter(
        name=legend_group,
        x=vector_stats['mean'].index.tolist(),
        y=vector_stats['mean'].values,
        mode='lines',
        fill='tonexty',
        fillcolor=f'rgba({r}, {g}, {b}, 0.3)',
        line={'color': f'rgba({r}, {g}, {b}, 1)'},
        legendgroup=legend_group,
        showlegend=True,
    )

    trace_p90 = go.Scatter(
        name='p90',
        x=vector_stats['p90'].index.tolist(),
        y=vector_stats['p90'].values,
        mode='lines',
        fill='tonexty',
        fillcolor=f'rgba({r}, {g}, {b}, 0.3)',
        line={
            'width': 0,
            'color': f'rgba({r}, {g}, {b}, 1)'
        },
        legendgroup=legend_group,
        showlegend=False,
    )

    trace_minimum = go.Scatter(
        name='minimum',
        x=vector_stats['minimum'].index.tolist(),
        y=vector_stats['minimum'].values,
        mode='lines',
        fill='tonexty',
        fillcolor=f'rgba({r}, {g}, {b}, 0.3)',
        line={
            'width': 0,
            'color': f'rgba({r}, {g}, {b}, 1)'
        },
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
