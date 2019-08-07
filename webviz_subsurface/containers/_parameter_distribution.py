from uuid import uuid4
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
import dash_daq as daq
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
from webviz_config.containers import WebvizContainer
from ..datainput import scratch_ensemble


class Widgets:

    @staticmethod
    def dropdown_from_dict(dom_id, d):
        return dcc.Dropdown(id=dom_id,
                            options=[{'label': k, 'value': v}
                                     for k, v in d.items()],
                            value=list(d.values())[0])


class ParameterDistribution(WebvizContainer):
    '''### Parameter distribution

This container shows parameter distribution as histogram,
and correlation between the parameters as a correlation matrix.

* `ensembles`: Which ensembles in `container_settings` to visualize.
'''

    def __init__(self, app, container_settings, ensembles):

        self.ensembles = {ens: container_settings['scratch_ensembles'][ens]
                          for ens in ensembles}
        self.uid = f'{uuid4()}'
        self.p1_drop_id = f'p1-dropd-{self.uid}'
        self.p2_drop_id = f'p2-dropd-{self.uid}'
        self.scatter_id = f'scatter-id-{self.uid}'
        self.scatter_color_id = f'scatter-color-id-{self.uid}'
        self.scatter_size_id = f'scatter-size-id-{self.uid}'
        self.matrix_id = f'chart-id-{self.uid}'
        self.ens_matrix_id = f'ens-matrix-id-{self.uid}'
        self.ens_p1_id = f'ens-p1-id-{self.uid}'
        self.ens_p2_id = f'ens-p2-id-{self.uid}'
        self.density_id = f'density-id-{self.uid}'

        self.set_callbacks(app)

    @property
    def p_cols(self):
        dfs = [get_parameters(ens) for ens in self.ensembles.values()]
        return sorted(list(pd.concat(dfs).columns))

    @property
    def matrix_plot(self):
        return dcc.Graph(
            id=self.matrix_id,
            clickData={'points': [
                {'x': self.p_cols[0],
                 'y': self.p_cols[0]}]},
            config={
                'displaylogo': False,
                'modeBarButtonsToRemove': ['sendDataToCloud']
            })

    @property
    def control_div(self):
        return html.Div(
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
                        html.Label('Parameter horisontal axis', style={
                            'font-weight': 'bold'}),
                        html.Div(
                            style={'padding-bottom': 20, 'display': 'grid',
                                   'grid-template-columns': '3fr 2fr'},
                            children=[
                                dcc.Dropdown(
                                    id=self.p1_drop_id,
                                    options=[{'label': p, 'value': p}
                                             for p in self.p_cols],
                                    value=self.p_cols[0]),
                                Widgets.dropdown_from_dict(
                                    self.ens_p1_id, self.ensembles),
                            ]),
                        html.Label('Parameter vertical axis', style={
                            'font-weight': 'bold'}),
                        html.Div(style={
                            'padding-bottom': 20,
                            'display': 'grid',
                            'grid-template-columns': '3fr 2fr'},
                            children=[
                            dcc.Dropdown(
                                id=self.p2_drop_id,
                                options=[{'label': p, 'value': p}
                                         for p in self.p_cols],
                                value=self.p_cols[0]),
                            Widgets.dropdown_from_dict(
                                self.ens_p2_id, self.ensembles)
                        ]),
                        html.Label('Color scatter by',
                                   style={'font-weight': 'bold'}),
                        dcc.Dropdown(
                            id=self.scatter_color_id,
                            options=[{'label': p, 'value': p}
                                     for p in self.p_cols])]),
                html.Div(style={'padding-top': 20, 'display': 'grid',
                                'grid-template-columns': '3fr 1fr 4fr'},
                         children=[
                    html.Label('Show density plot',
                               style={'font-weight': 'bold'}),
                    daq.ToggleSwitch(id=self.density_id, value=True)])
            ])

    @property
    def layout(self):
        return html.Div(
            children=[
                html.Div(
                    style={'display': 'grid',
                           'grid-template-columns': '3fr 2fr'},
                    children=[
                        html.Div(
                            children=[self.matrix_plot]), self.control_div]),
                dcc.Graph(
                    id=self.scatter_id,
                    config={
                        'displaylogo': False,
                        'modeBarButtonsToRemove': ['sendDataToCloud']
                    }),
            ])

    def set_callbacks(self, app):
        @app.callback(Output(self.matrix_id, 'figure'),
                      [Input(self.ens_matrix_id, 'value'),
                       Input(self.p1_drop_id, 'value'),
                       Input(self.p2_drop_id, 'value')])
        def update_matrix(ens, p1, p2):
            '''Renders correlation matrix.
            Currently also re-renders matrix to update currently
            selected cell. This is not optimal, but hard to prevent
            as an Output object only can have one callback attached,
            and it is not possible to assign callbacks to individual
            elements of a Plotly graph object
            '''
            fig = render_matrix(ens)
            # Finds index of the currently selected cell
            x_index = list(fig['data'][0]['x']).index(p1)
            y_index = list(fig['data'][0]['y']).index(p2)
            # Adds a shape to highlight the selected cell
            shape = [
                {
                    'xref': 'x',
                    'yref': 'y',
                    'x0': x_index-0.5,
                    'y0': y_index-0.5,
                    'x1': x_index+0.5,
                    'y1': y_index+0.5,
                    'type': 'rect',
                    'line': {
                        'color': 'black',
                    }
                }]
            fig['layout']['shapes'] = shape
            return fig

        @app.callback(Output(self.scatter_id, 'figure'),
                      [Input(self.ens_p1_id, 'value'),
                       Input(self.p1_drop_id, 'value'),
                       Input(self.ens_p2_id, 'value'),
                       Input(self.p2_drop_id, 'value'),
                       Input(self.scatter_color_id, 'value'),
                       Input(self.density_id, 'value')])
        def update_scatter(ens1, p1, ens2, p2, color, density):
            return render_scatter(ens1, p1, ens2, p2, color, density)

        @app.callback([Output(self.p1_drop_id, 'value'),
                       Output(self.p2_drop_id, 'value'),
                       Output(self.ens_p1_id, 'value'),
                       Output(self.ens_p2_id, 'value')],
                      [Input(self.matrix_id, 'clickData'),
                       Input(self.ens_matrix_id, 'value')]
                      )
        def update_from_click(cd, ens):
            try:
                points = cd['points'][0]
            # TypeError is returned if no cells are clicked
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
def render_scatter(ens1, x_col, ens2, y_col, color, density):
    if ens1 == ens2:
        real_text = [f'Realization:{r}'
                     for r in get_parameters(ens1)['REAL']]
    else:
        real_text = [f'Realization:{r}(x)'
                     for r in get_parameters(ens2)['REAL']]

    x = get_parameters(ens1)[x_col]
    y = get_parameters(ens2)[y_col]
    color = get_parameters(ens1)[color] if color else None
    data = []
    data.append({
        'x': x,
        'y': y,
        'marker': {
            'color': color
        },
        'text': real_text,
        'type': 'scatter',
        'mode': 'markers',
        'showlegend': False
    })
    data.append({
        'x': x,
        'type': 'histogram',
        'yaxis': 'y2',
        'showlegend': False,
        'marker': {'color': 'rgb(31, 119, 180)'},
    })
    data.append({
        'y': y,
        'type': 'histogram',
        'xaxis': 'x2',
        'showlegend': False,
        'marker': {'color': 'rgb(31, 119, 180)'}
    })
    if density:
        data.append({
            'x': x,
            'y': y,
            'hoverinfo': 'none',
            'autocolorscale': False,
            'showlegend': False,
            'colorscale': [
                [0, 'rgb(255,255,255)'],
                [0.125, 'rgb(37, 52, 148)'],
                [0.25, 'rgb(34, 94, 168)'],
                [0.375, 'rgb(29, 145, 192)'],
                [0.5, 'rgb(65, 182, 196)'],
                [0.625, 'rgb(127, 205, 187)'],
                [0.75, 'rgb(199, 233, 180)'],
                [0.875, 'rgb(237, 248, 217)'],
                [1, 'rgb(255, 255, 217)']],
            'contours': {
                'coloring': 'fill',
                # 'end': 80.05,
                'showlines': True,
                'size': 5,
                'start': 5
            },
            'name': 'density',
            'ncontours': 20,
            'reversescale': False,
            'showscale': False,
            'type': 'histogram2dcontour',
        })
    layout = {
        'margin': {'t': 20, 'b': 50, 'l': 200, 'r': 200},
        'bargap': 0.05,
        'xaxis': {
            'title': x_col,
            'domain': [0, 0.85],
            'showgrid': False,
            'showline': False,
            'zeroline': False,
            'showlegend': False
        },
        'xaxis2': {
            'domain': [0.85, 1],
            'showgrid': False,
            'showline': False,
            'zeroline': False,
            'showticklabels': False
        },
        'yaxis': {
            'title': y_col,
            'domain': [0, 0.85],
            'showgrid': False,
            'zeroline': False,

        },
        'yaxis2': {
            'domain': [0.85, 1],
            'showgrid': False,
            'zeroline': False,
            'showticklabels': False,
            'showline': False
        }
    }

    return {'data': data, 'layout': layout}


@cache.memoize(timeout=cache.TIMEOUT)
def render_matrix(ensemble_path):

    data = get_parameters(ensemble_path).apply(pd.to_numeric, errors='coerce')\
                                        .dropna(how='all', axis='columns')
    values = list(data.corr().values)

    data = {
        'type': 'heatmap',
        'x': data.columns,
        'y': data.columns,
        'z': values,
        'zmin': -1,
        'zmax': 1
    }

    layout = {
        'uirevision': 'keep_matrix',
        'title': 'Pairwise correlation matrix',
        'margin': {'t': 50, 'b': 50},
        'xaxis': {'ticks': '', 'showticklabels': False},
        'yaxis': {'ticks': '', 'showticklabels': False},
    }

    return {'data': [data], 'layout': layout}
