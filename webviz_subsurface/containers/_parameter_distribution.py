from uuid import uuid4
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
from ..datainput import scratch_ensemble


class Widgets:

    @staticmethod
    def dropdown_from_dict(dom_id, d):
        return dcc.Dropdown(id=dom_id,
                            options=[{'label': k, 'value': v}
                                     for k, v in d.items()],
                            value=list(d.values())[0])


class ParameterDistribution:
    '''### Parameter distribution

This container shows parameter distribution as histogram,
and correlation between the parameters as a correlation matrix.

* `ensemble`: Which ensemble in `container_settings` to visualize.
* `title`: Optional title for the container.
'''
    LAYOUT_STYLE = {
        'display': 'grid',
        'grid-template-areas':
            'matrix matrix controls controls'
            'matrix matrix scatter scatter '
            'p1 p2 scatter scatter'
    }
    GRAPH_STYPE = {
        'display': 'grid',
        'grid-template-columns': '1fr 1fr 1fr 1fr',
    }

    def __init__(self, app, container_settings, ensembles,
                 title: str = 'Parameter Distribution'):

        self.title = title
        self.ensembles = {ens: container_settings['scratch_ensembles'][ens]
                          for ens in ensembles}
        self.uid = f'{uuid4()}'
        self.p1_drop_id = f'p1-dropd-{self.uid}'
        self.p1_graph = f'p1-graph-{self.uid}'
        self.p2_drop_id = f'p2-dropd-{self.uid}'
        self.p2_graph = f'p2-graph-{self.uid}'
        self.scatter_id = f'scatter-id-{self.uid}'
        self.scatter_color_id = f'scatter-color-id-{self.uid}'
        self.scatter_size_id = f'scatter-size-id-{self.uid}'
        self.matrix_id = f'chart-id-{self.uid}'
        self.ens_matrix_id = f'ens-matrix-id-{self.uid}'
        self.ens_p1_id = f'ens-p1-id-{self.uid}'
        self.ens_p2_id = f'ens-p2-id-{self.uid}'

        self.set_callbacks(app)

    @property
    def parameter_columns(self):
        dfs = [get_parameters(ens) for ens in self.ensembles.values()]
        return sorted(list(pd.concat(dfs).columns))

    @property
    def matrix_plot(self):
        return dcc.Graph(
            id=self.matrix_id,
            clickData={'points': [
                {'x': self.parameter_columns[0]},
                {'y': self.parameter_columns[0]}]},
            config={
                'displaylogo': False,
                'modeBarButtonsToRemove': ['sendDataToCloud']
            })

    @property
    def control_div(self):
        return html.Div(
            className='controls',
            style={'padding-top': 10, 'padding-left': 100},
            children=[
                html.Div(
                    children=[
                        html.Label('Set ensemble in all plots:',
                                   style={'font-weight': 'bold'}),
                        html.Div(style={'padding-bottom': 20},
                                 children=[
                            Widgets.dropdown_from_dict(
                                self.ens_matrix_id, self.ensembles)
                        ]),
                        html.Label('Parameter 1', style={
                            'font-weight': 'bold'}),
                        html.Div(
                            style={'padding-bottom': 20},
                            children=[
                                dcc.Dropdown(
                                    id=self.p1_drop_id,
                                    options=[{'label': p, 'value': p}
                                             for p in self.parameter_columns],
                                    value=self.parameter_columns[0]),
                                Widgets.dropdown_from_dict(
                                    self.ens_p1_id, self.ensembles),
                            ]),
                        html.Label('Parameter 2', style={
                            'font-weight': 'bold'}),
                        html.Div(style={'padding-bottom': 20},
                                 children=[
                            dcc.Dropdown(
                                id=self.p2_drop_id,
                                options=[{'label': p, 'value': p}
                                         for p in self.parameter_columns],
                                value=self.parameter_columns[0]),
                            Widgets.dropdown_from_dict(
                                self.ens_p2_id, self.ensembles)
                        ]),
                        html.Label('Color scatter by', style={
                            'font-weight': 'bold'}),
                        html.Div(style={'padding-bottom': 20},
                                 children=[
                            dcc.Dropdown(
                                id=self.scatter_color_id,
                                options=[{'label': p, 'value': p}
                                         for p in self.parameter_columns])
                        ])
                    ])
            ])

    @property
    def layout(self):
        return html.Div(
            className="grid_container",
            children=[
                html.Div(
                    className='matrix',
                    children=[self.matrix_plot]),
                self.control_div,
                html.Div(
                    className='p1',
                    children=[
                        dcc.Graph(
                            id=self.p1_graph,
                            config={
                                'displaylogo': False,
                                'modeBarButtonsToRemove': ['sendDataToCloud']
                            }),
                    ]),
                html.Div(
                    className='p2',
                    children=[
                        dcc.Graph(
                            id=self.p2_graph,
                            config={
                                'displaylogo': False,
                                'modeBarButtonsToRemove': ['sendDataToCloud']
                            }),
                    ]),
                html.Div(
                    className='scatter',
                    children=[
                        dcc.Graph(
                            id=self.scatter_id,
                            config={
                                'displaylogo': False,
                                'modeBarButtonsToRemove': ['sendDataToCloud']
                            })
                    ])

            ])

    def set_callbacks(self, app):
        @app.callback(Output(self.matrix_id, 'figure'),
                      [Input(self.ens_matrix_id, 'value')])
        def update_matrix(ens):
            return render_matrix(ens)

        @app.callback(Output(self.p1_graph, 'figure'),
                      [Input(self.ens_p1_id, 'value'),
                       Input(self.p1_drop_id, 'value')])
        def update_p1(ens, p):
            return render_histogram(ens, p)

        @app.callback(Output(self.p2_graph, 'figure'),
                      [Input(self.ens_p2_id, 'value'),
                       Input(self.p2_drop_id, 'value')])
        def update_p2(ens, p):
            return render_histogram(ens, p)

        @app.callback(Output(self.scatter_id, 'figure'),
                      [Input(self.ens_p1_id, 'value'),
                       Input(self.p1_drop_id, 'value'),
                       Input(self.ens_p2_id, 'value'),
                       Input(self.p2_drop_id, 'value'),
                       Input(self.scatter_color_id, 'value')])
        def update_scatter(ens1, p1, ens2, p2, color):
            return render_scatter(ens1, p1, ens2, p2, color)

        @app.callback([Output(self.p1_drop_id, 'value'),
                       Output(self.p2_drop_id, 'value'),
                       Output(self.ens_p1_id, 'value'),
                       Output(self.ens_p2_id, 'value')],
                      [Input(self.matrix_id, 'clickData'),
                       Input(self.ens_matrix_id, 'value')])
        def update_from_click(cd, ens):
            try:
                points = cd['points'][0]
            except TypeError:

                return [None for i in range(4)]
            return [points['x'], points['y'], ens, ens]

    def add_webvizstore(self):
        return [([get_parameters, [{'ensemble_path': v}
                                   for v in self.ensembles.values()]])]


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_parameters(ensemble_path) -> pd.DataFrame:

    return scratch_ensemble('', ensemble_path).parameters


@cache.memoize(timeout=cache.TIMEOUT)
def render_scatter(ens1, x, ens2, y, color):
    if ens1 == ens2:
        real_text = [f'Realization:{r}'
                     for r in get_parameters(ens1)['REAL']]
    else:
        real_text = [f'Realization:{r}(x)'
                     for r in get_parameters(ens2)['REAL']]
    print(color)
    data = {
        'x': get_parameters(ens1)[x],
        'y': get_parameters(ens2)[y],
        'marker': {
            'color': get_parameters(ens1)[color] if color else None
        },
        'text': real_text,
        'type': 'scatter',
        'mode': 'markers'
    }
    layout = {
        'margin': {'t': 50, 'b': 50},
        'xaxis': {'title': x},
        'yaxis': {'title': y},
    }
    return {'data': [data], 'layout': layout}


@cache.memoize(timeout=cache.TIMEOUT)
def render_bar(ens, y):
    data = {
        'y': get_parameters(ens)[y],
        'x': [r for r in get_parameters(ens)['REAL']],
        'type': 'bar',
        # 'mode': 'markers'
    }
    layout = {
        'margin': {'t': 50, 'b': 50},
        'xaxis': {'title': 'Realization'},
        'yaxis': {'title': y},
    }
    return {'data': [data], 'layout': layout}


@cache.memoize(timeout=cache.TIMEOUT)
def render_histogram(ensemble_path, parameter):
    data = {
        'x': get_parameters(ensemble_path)[parameter],
        'type': 'histogram'
    }

    layout = {
        'margin': {'t': 50, 'b': 50},
        'bargap': 0.05,
        'xaxis': {'title': parameter},
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
        'title': 'Correlation matrix',
        'margin': {'t': 50, 'b': 50},
        'xaxis': {'showticklabels': False},
        'yaxis': {'showticklabels': False},
    }

    return {'data': [data], 'layout': layout}
