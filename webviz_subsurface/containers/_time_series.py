import itertools
from uuid import uuid4
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_plotly.graph_objs import FanChart
from webviz_config.containers import WebvizContainer
from plotly.colors import DEFAULT_PLOTLY_COLORS
from webviz_subsurface.datainput import load_ensemble_set, get_time_series_data, \
    get_time_series_statistics, get_time_series_fielgains


# Todo:
#   - caching
#   - history
#   - fieldgains
#   - layout => griding
#   - button logic to boolean


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
    def tab_id(self):
        return f'_tab_id-{self.uid}'

    @property
    def btn_show_uncertainty_id(self):
        return f'show-history-uncertainty-{self.uid}'

    @property
    def btn_show_fieldgains_id(self):
        return f'show-fieldgains-{self.uid}'    

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
                    html.Div([
                        html.Button('Show *H',
                            id=self.btn_show_uncertainty_id,
                        ),
                        html.Button('Fieldgains',
                            id=self.btn_show_fieldgains_id,
                        ),
                    ]),
                ], style={"float":"left", 'display': 'inline-block'}),

                html.Div([
                    dcc.Tabs(id=self.tab_id, value='summary_data', children=[
                        dcc.Tab(label='Summary Vector', value='summary_data'),
                        dcc.Tab(label='Statistics', value='summary_stats'),
                    ]),
                    html.Div(id='tabs-content'),
                    html.Div(id=self.chart_id)
                ], style={'width': '80%', 'display': 'inline-block'}),

            ]),
        ])


# =============================================================================
# Callbacks
# =============================================================================

    def set_callbacks(self, app):

        @app.callback(Output(self.chart_id, 'children'),
                      [Input(self.dropwdown_vector_id, 'value'),
                       Input(self.tab_id, 'value'),
                       Input(self.btn_show_uncertainty_id, 'n_clicks'),
                       Input(self.btn_show_fieldgains_id, 'n_clicks')])
        def update_plot(
                vector: str, 
                plot_type: str,
                n_clicks_history: int = 0,
                n_clicks_fieldgians: int = 0,):

            # to be replaced by boolen
            # show history uncertainty
            if n_clicks_history == None:
                n_clicks_history = 0
                show_history_vector = False
            if (n_clicks_history % 2 == 0):
                show_history_vector = False
            if (n_clicks_history % 2 == 1):
                show_history_vector = True

            # show fieldgains
            if n_clicks_fieldgians == None:
                n_clicks_fieldgians = 0
                show_fieldgains = False
            if (n_clicks_fieldgians % 2 == 0):
                show_fieldgains = False
            if (n_clicks_fieldgians % 2 == 1):
                show_fieldgains = True


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
                      'ensemble_set_name': self.title}]
                ),
        ]


# =============================================================================
# Render functions
# =============================================================================

def render_realization_plot(
        ensemble_paths: tuple,
        time_index: str,
        column_keys: tuple,
        vector: str,
        ensemble_set_name: str,
        smry_history_columns: tuple,
        show_history_vector: bool,
        show_fieldgains: bool,
    ):


    cycle_list = itertools.cycle(DEFAULT_PLOTLY_COLORS)
    history_vector = (vector + 'H')


    # summary- and history-vector-traces
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


    # feildgain traces
    if show_fieldgains:
        field_gains = get_time_series_fielgains(
            ensemble_paths=ensemble_paths,
            time_index=time_index,
            column_keys=column_keys,
            ensemble_set_name=ensemble_set_name
        )
        print(field_gains.shape)

    smry_data.dropna(subset=[vector])

    plot_traces = []
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

# caching leads to an err. in FanChart()
def render_stat_plot(
        ensemble_paths: tuple,
        time_index: str,
        column_keys: tuple,
        vector: str):

    smry_stats = get_time_series_statistics(
        ensemble_paths=ensemble_paths,
        column_keys=column_keys,
        time_index=time_index)

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

