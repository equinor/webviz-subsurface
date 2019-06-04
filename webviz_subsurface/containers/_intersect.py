from uuid import uuid4
from glob import glob
from pathlib import PurePath
from collections import OrderedDict
import numpy as np
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
from dash_table import DataTable
from webviz_config.common_cache import cache
from webviz_config.containers import WebvizContainer
from ..datainput import scratch_ensemble, load_surface, get_wfence, get_hfence


class Intersect(WebvizContainer):
    '''### Intersect

This container visualizes surfaces intersected along a well path.
The input are surfaces from a FMU ensemble stored on standardized
format with standardized naming (share/results/maps/name--category.gri)
and a folder of well files stored in RMS well format.

* `ensemble`: Which ensemble in `container_settings` to visualize.
* `well_path`: File folder with wells in rmswell format
* `surface_cat`: Surface category to look for in the file names
* `surface_names`: List of surface names to look for in the file names
* `well_suffix`:  Optional suffix for well files. Default is .rmswell
'''
    COLORS = ['#543005', '#8c510a', '#bf812d', '#dfc27d',
              '#f6e8c3', '#f5f5f5', '#c7eae5', '#80cdc1',
              '#35978f', '#01665e', '#003c30']

    LAYOUT_STYLE = {
        'display': 'grid',
        'align-content': 'space-around',
        'justify-content': 'space-between',
        'grid-template-columns': '2fr 6fr',
    }

    FENCE_OPTION_STYLE = {
        'display': 'grid',
        'align-content': 'space-around',
        'justify-content': 'space-between',
        'grid-template-columns': '1fr 1fr',
        'max-width': '50%'
    }

    TABLE_STYLE = {
        'maxHeight': '300',
        'overflowY': 'auto'
    }

    def __init__(self, app, container_settings, ensemble,
                 well_path, surface_cat, surface_names,
                 well_suffix='.rmswell'):

        self.well_path = well_path
        self.ensemble_path = container_settings['scratch_ensembles'][ensemble]
        self.ensemble = scratch_ensemble(ensemble, self.ensemble_path)
        self.well_suffix = well_suffix
        self.surface_cat = surface_cat
        self.surface_names = surface_names
        self.unique_id = f'{uuid4()}'
        self.well_list_id = f'well-list-id-{self.unique_id}'
        self.real_list_id = f'real-list-id-{self.unique_id}'
        self.surf_list_id = f'surf-list-id-{self.unique_id}'
        self.table_id = f'table-id-{self.unique_id}'
        self.well_tvd_id = f'well-tvd-id-{self.unique_id}'
        self.zoom_state_id = f'ui-state-id-{self.unique_id}'
        self.intersection_id = f'intersection-id-{self.unique_id}'
        self.set_callbacks(app)

    @property
    def realizations(self):
        d = {self.ensemble._realizations[real]._origpath: real
             for real in self.ensemble._realizations}
        return OrderedDict(sorted(d.items()))

    @property
    def well_names(self):
        well_folder = f'{self.well_path}/*{self.well_suffix}'
        return sorted([well for well in glob(well_folder)])

    @property
    def surface_colors(self):
        return {surf: Intersect.COLORS[i % len(Intersect.COLORS)]
                for i, surf in enumerate(self.surface_names)}

    # @cache.memoize(timeout=cache.TIMEOUT)
    # def agg_surfaces(self, surf_names, calc='avg'):
    #     agg = []
    #     for s_name in surf_names:
    #         s_arr = [self.load_surface_in_real(s_name, real).values
    #                  for real in self.ensemble._realizations]
    #         if calc=='avg':
    #             s.values = np.average(np.array(s_arr), axis=0)
    #             agg.append(s)
    #     return agg

    @cache.memoize(timeout=cache.TIMEOUT)
    def plot_xsection(self, well, reals, surf_names, tvdmin=0):
        '''Plots all lines in intersection'''
        traces = []
        for s_name in surf_names:
            traces.extend(
                make_surface_traces(
                    well, reals, s_name, self.surface_cat,
                    self.surface_colors[s_name]).to_dict('rows'))
        traces.append(make_well_trace(well, tvdmin))
        return traces

    @property
    def graph_layout(self):
        '''Styling the graph'''
        return {
            'yaxis': {'autorange': 'reversed',
                      'zeroline': False, 'title': 'TVD'},
            'xaxis': {'zeroline': False,
                      'title': 'Well horizontal distance'}

        }

    @property
    def layout(self):
        return html.Div([
            html.Div(style=Intersect.LAYOUT_STYLE, children=[
                html.Div([
                    html.P('Well:', style={'font-weight': 'bold'}),
                    dcc.Dropdown(
                        id=self.well_list_id,
                        options=[{'label': PurePath(well).stem, 'value': well}
                                 for well in self.well_names],
                        value=self.well_names[0],
                        clearable=False
                    ),
                    html.P('Realization:', style={'font-weight': 'bold'}),
                    dcc.Dropdown(
                        id=self.real_list_id,
                        options=[{'label': real, 'value': path}
                                 for path, real in self.realizations.items()],
                        value=list(self.realizations.keys())[0],
                        multi=True,
                        placeholder='All realizations'
                    ),

                    html.P('Surfaces:', style={'font-weight': 'bold'}),
                    dcc.Dropdown(
                        id=self.surf_list_id,
                        options=[{'label': r, 'value': r}
                                 for r in self.surface_names],
                        value=self.surface_names[0],
                        multi=True,
                        placeholder='All surfaces'
                    ),
                    html.Div(style=Intersect.TABLE_STYLE, children=[
                        DataTable(
                            id=self.table_id,
                            columns=[{"name": i, "id": i}
                                     for i in ['Name', 'TVDmin', 'TVDmean',
                                               'TVDmax', 'TVDstddev']]
                        )
                    ])
                ]),
                html.Div(style={'height': '80vh'}, children=[
                    dcc.Graph(style={'height': '80vh'},
                              id=self.intersection_id),
                    html.Div(style=Intersect.FENCE_OPTION_STYLE, children=[
                        html.P('Start depth:', style={'font-weight': 'bold'}),
                        html.P('Graph zoom level:', style={
                               'font-weight': 'bold'}),
                        dcc.Input(style={'overflow': 'auto'},
                                  id=self.well_tvd_id, type='number', value=0),
                        dcc.RadioItems(
                            id=self.zoom_state_id,
                            options=[{'label': k, 'value': v}
                                     for k, v in {
                                     'Keep on new data': True,
                                     'Reset on new data': False}.items()],
                            value=True,
                        ),
                    ])

                ])
            ])
        ])

    def set_callbacks(self, app):
        @app.callback(
            Output(self.intersection_id, 'figure'),
            [Input(self.well_list_id, 'value'),
             Input(self.real_list_id, 'value'),
             Input(self.surf_list_id, 'value'),
             Input(self.well_tvd_id, 'value'),
             Input(self.zoom_state_id, 'value')])
        def set_fence(_well_path, _reals, _surfs, _tvdmin, _keep_zoom_state):
            '''Callback to update intersection on data change'''
            if not isinstance(_surfs, list):
                _surfs = [_surfs]
            if not isinstance(_reals, list):
                _reals = [_reals]
            if not _reals:
                _reals = list(self.realizations.keys())
            if not _surfs:
                _surfs = self.surface_names
            s_names = [s for s in self.surface_names if s in _surfs]
            xsect = self.plot_xsection(_well_path, _reals, s_names, _tvdmin)
            layout = self.graph_layout
            if _keep_zoom_state:
                layout['uirevision'] = 'keep'
            return {'data': xsect, 'layout': layout}

        @app.callback(Output(self.table_id, 'data'),
                      [Input(self.intersection_id, 'hoverData')],
                      [State(self.intersection_id, 'figure'),
                       State(self.surf_list_id, 'value')])
        def hover(_data, _fig, _surfaces):
            '''Callback to update table on mouse over'''
            try:
                graph = _fig['data']
            except TypeError:
                return [{
                    'TVDmin': None,
                    'TVDmean': None,
                    'TVDmax': None,
                    'TVDstddev': None,
                    'Name': None
                }]
            if not isinstance(_surfaces, list):
                _surfaces = [_surfaces]
            if not _surfaces:
                _surfaces = self.surface_names
            names = {s: {'vals': [], 'min': None, 'max': None}
                     for s in _surfaces}

            for i, p in enumerate(_data['points']):
                try:
                    s_name = graph[i]['name']
                    real = self.realizations[graph[i]['real']]
                except KeyError:
                    continue
                names[s_name]['vals'].append(p['y'])
                if not names[s_name]['min']:
                    names[s_name]['min'] = p['y']
                    names[s_name]['min_real'] = real
                    names[s_name]['max'] = p['y']
                    names[s_name]['max_real'] = real
                else:
                    if names[s_name]['min'] > p['y']:
                        names[s_name]['min'] = p['y']
                        names[s_name]['min_real'] = real
                    if names[s_name]['max'] < p['y']:
                        names[s_name]['max'] = p['y']
                        names[s_name]['max_real'] = real

            return [{
                'TVDmin': f'{np.min(val["vals"]):.2f}({val["min_real"]})',
                'TVDmean': f'{np.mean(val["vals"]):.2f}',
                'TVDmax': f'{np.max(val["vals"]):.2f}({val["max_real"]})',
                'TVDstddev': f'{np.std(val["vals"]):.2f}',
                'Name': name}
                for name, val in names.items()]


@cache.memoize(timeout=cache.TIMEOUT)
def make_well_trace(well, tvdmin=0):
    '''Creates well trace for graph'''
    x = [trace[3] for trace in get_wfence(well, extend=2).values]
    y = [trace[2] for trace in get_wfence(well, extend=2).values]
    # Filter out elements less than tvdmin
    # https://stackoverflow.com/questions/17995302/filtering-two-lists-simultaneously
    try:
        y, x = zip(*((y_el, x) for y_el, x in zip(y, x) if y_el >= tvdmin))
    except ValueError:
        pass
    return {
        'x': x,
        'y': y,
        'name': PurePath(well).stem,
        'fill': None,
        'marker': {'color': 'black'}
    }


@cache.memoize(timeout=cache.TIMEOUT)
def make_surface_traces(well, reals, surf_name, cat, color):
    '''Creates surface traces for graph'''
    plot_data = []
    x = [trace[3] for trace in get_wfence(well).values]
    for j, real in enumerate(reals):
        try:
            surf = load_surface(surf_name, real, cat)
        except IOError:
            continue
        showlegend = True if j == 0 else False
        plot_data.append(
            {
                'x': x,
                'y': get_hfence(well, surf)[:, 2].copy().tolist(),
                'name': surf_name,
                'hoverinfo': 'none',
                'legendgroup': surf_name,
                'showlegend': showlegend,
                'real': real,
                'marker': {'color': color}
            })
    return pd.DataFrame(plot_data)
