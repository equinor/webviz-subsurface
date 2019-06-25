import os
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
from webviz_config.webviz_store import webvizstore
from webviz_config.containers import WebvizContainer
from ..datainput import (scratch_ensemble, get_cfence, get_gfence,
                         get_wfence, get_hfence, well_to_df, surface_to_df)


class IntersectGrid(WebvizContainer):
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
* `cube_path`: File folder containing seismic cubes
* `cubes`: List of cube names
'''
    COLORS = ['#543005', '#8c510a', '#bf812d', '#dfc27d',
              '#f6e8c3', '#f5f5f5', '#c7eae5', '#80cdc1',
              '#35978f', '#01665e', '#003c30']
    COLOR_SCALES = ['Blackbody',
                    'Bluered',
                    'Blues',
                    'Earth',
                    'Electric',
                    'Greens',
                    'Greys',
                    'Hot',
                    'Jet',
                    'Picnic',
                    'Portland',
                    'Rainbow',
                    'RdBu',
                    'Reds',
                    'Viridis',
                    'YlGnBu',
                    'YlOrRd']
    LAYOUT_STYLE = {
        'display': 'grid',
        'align-content': 'space-around',
        'justify-content': 'space-between',
        'grid-template-columns': '1fr 1fr',
    }
    CONTROL_STYLE = {
        'display': 'grid',
        'align-content': 'space-around',
        'justify-content': 'space-between',
        'grid-template-columns': '1fr 1fr 1fr 1fr 1fr',
        'padding-right': '20px',
        'padding-left': '20px',
        'font-size':'10px'
    }
    def __init__(self, app, container_settings, ensemble,
                 well_path, surface_cat, surface_names,
                 grid_model, parameters: list, well_suffix='.rmswell', views= 1):

        self.well_path = well_path
        self.grid_model = grid_model
        self.parameters = parameters
        self.ensemble_path = container_settings['scratch_ensembles'][ensemble]
        self.ensemble = ensemble
        self.well_suffix = well_suffix
        self.surface_cat = surface_cat
        self.surface_names = surface_names
        self.unique_id = f'{uuid4()}'
        self.views = views
        self.well_list_id = self.assign_ids('well-list-id')
        self.parameters_id = self.assign_ids('parameters-list-id')
        self.real_list_id = self.assign_ids('real-list-id')
        self.surf_list_id = self.assign_ids('surf-list-id')
        self.color_scale_id = self.assign_ids('color-scale-id')
        self.table_id = self.assign_ids('table-id')
        self.well_tvd_id = self.assign_ids('well-tvd-id')
        self.zoom_state_id = self.assign_ids('ui-state-id')
        self.intersection_id = self.assign_ids('intersection-id')
        self.set_callbacks(app)

    
    def assign_ids(self, domId):
        return [f'{domId}-{i}-{self.unique_id}' for i in range(self.views)]


    @property
    def realizations(self):
        df = get_realizations(self.ensemble, self.ensemble_path)
        return pd.Series(df['REAL'].values, index=df['PATH']).to_dict()

    @property
    def well_names(self):
        df = get_file_paths(self.well_path, self.well_suffix)
        return df['PATH'].tolist()

    @property
    def surface_colors(self):
        return {surf: IntersectGrid.COLORS[i % len(IntersectGrid.COLORS)]
                for i, surf in enumerate(self.surface_names)}

    def get_grid_path(self, real):
        return os.path.join(real, 'share/results/grids', f'{self.grid_model}.roff')

    def get_param_path(self, real, parameter):
        return os.path.join(real, 'share/results/grids', f'{self.grid_model}--{parameter}.roff')

    @cache.memoize(timeout=cache.TIMEOUT)
    def plot_xsection(self, parameter, well, real, surf_names,
                      color_scale, tvdmin=0):
        '''Plots all lines in intersection'''
        traces = []

        layout = self.graph_layout
        cube_trace = make_param_trace(
            well, 
            self.get_grid_path(real),
            self.get_param_path(real, parameter)).to_dict('rows')

        cube_trace[0]['colorscale'] = color_scale
        cube_trace[0]['name'] = parameter
        cube_trace[0]['colorbar'] = {'x': 1, 'showticklabels': False}
        layout['xaxis']['range'] = [cube_trace[0]['x0'], cube_trace[0]['xmax']]
        layout['xaxis']['autorange'] = False
        layout['yaxis']['range'] = [cube_trace[0]['ymax'], cube_trace[0]['y0']]
        layout['yaxis']['autorange'] = False

        for s_name in surf_names:
            traces.extend(
                make_surface_traces(
                    well, [real], s_name, self.surface_cat,
                    self.surface_colors[s_name]).to_dict('rows'))
        traces.append(make_well_trace(well, tvdmin))
        traces.extend(cube_trace)
        return {'data': traces, 'layout': layout}

    @property
    def graph_layout(self):
        '''Styling the graph'''
        return {
            'margin': {'t': 0}, 
            'yaxis': {'autorange': 'reversed',
                      'zeroline': False, 'title': 'TVD'},
            'xaxis': {'zeroline': False,
                      'title': 'Well horizontal distance'}

        }

    
    def view_layout(self, view):
        return html.Div([
            html.Div(style=IntersectGrid.CONTROL_STYLE,
                   children=[
                   html.Div([
                        html.P('Parameter:', style={'font-weight': 'bold'}),
                        dcc.Dropdown(
                            # style={'width': '100%'},
                            id=self.parameters_id[view],
                            options=[{'label': c, 'value': c}
                                     for c in self.parameters],
                            value=self.parameters[0],
                            clearable=False
                        )]),
                    html.Div([
                        html.P('Seismic color:', style={'font-weight': 'bold'}),
                        dcc.Dropdown(
                            # style={'width': '50%'},
                            id=self.color_scale_id[view],
                            options=[{'label': c, 'value': c}
                                     for c in IntersectGrid.COLOR_SCALES],
                            value='RdBu',
                            clearable=False
                        )]),
                    html.Div([
                        html.P('Well:', style={'font-weight': 'bold'}),
                        dcc.Dropdown(
                            # style={'width': '50%'},
                            id=self.well_list_id[view],
                            options=[{'label': PurePath(well).stem, 'value': well}
                                     for well in self.well_names],
                            value=self.well_names[0],
                            clearable=False
                        )]),
                    html.Div([
                        html.P('Surfaces:', style={'font-weight': 'bold'}),
                        dcc.Dropdown(
                            id=self.surf_list_id[view],
                            options=[{'label': r, 'value': r}
                                     for r in self.surface_names],
                            value=self.surface_names[0],
                            multi=True,
                            placeholder='All surfaces'
                        )]),
                    html.Div([
                        html.P('Realizations:', style={'font-weight': 'bold'}),
                        dcc.Dropdown(
                            id=self.real_list_id[view],
                            options=[{'label': real, 'value': path}
                                     for path, real in self.realizations.items()],
                            value=list(self.realizations.keys())[0],
                            multi=False,
                            placeholder='All realizations'
                        )])
                ]),
            html.Div(children=[
                    dcc.Graph(id=self.intersection_id[view])
                ])])

    @property
    def layout(self):
        return html.Div([
            html.Div(style=IntersectGrid.LAYOUT_STYLE, children=[self.view_layout(i) for i in range(self.views)]
                
            )
        ])

    def set_callbacks(self, app):
        for view in range(self.views):
            @app.callback(
                Output(self.intersection_id[view], 'figure'),
                [Input(self.parameters_id[view], 'value'),
                 Input(self.well_list_id[view], 'value'),
                 Input(self.real_list_id[view], 'value'),
                 Input(self.surf_list_id[view], 'value'),
                 Input(self.color_scale_id[view], 'value')])
            def set_fence(_parameter, _well_path, _reals, _surfs, color_scale):
                '''Callback to update intersection on data change'''
                if not isinstance(_surfs, list):
                    _surfs = [_surfs]

                if not _surfs:
                    _surfs = self.surface_names
                s_names = [s for s in self.surface_names if s in _surfs]
                xsect = self.plot_xsection(
                    _parameter, _well_path, _reals, s_names, color_scale)
                xsect['layout']['uirevision'] = 'keep'
                return xsect

    def add_webvizstore(self):
        funcs = []
        funcs.append(
            (get_realizations, [{'ens': self.ensemble,
                                 'ens_path': self.ensemble_path}]))
        funcs.append(
            (get_file_paths, [{'folder': self.well_path,
                               'suffix': self.well_suffix}]))
        for well in self.well_names:
            funcs.append((well_to_df, [{'well_name': well}]))
            for real in self.realizations.keys():
                funcs.append((make_param_trace, [{'well': well,
                                                  'grid': self.get_grid_path(real),
                                                  'parameter':self.get_param_path(real, p)}
                                                    for p in self.parameters]))
        for surf in self.surface_names:
            for path in self.realizations.keys():
                funcs.append((surface_to_df, [
                    {'s_name': surf,
                             'real_path': path,
                             'surface_cat': self.surface_cat}]))
        return funcs


@cache.memoize(timeout=cache.TIMEOUT)
def make_well_trace(well, tvdmin=0):
    '''Creates well trace for graph'''
    x = [trace[3]
         for trace in get_wfence(well, nextend=2, tvdmin=tvdmin).values]
    y = [trace[2]
         for trace in get_wfence(well, nextend=2, tvdmin=tvdmin).values]
    # Filter out elements less than tvdmin
    # https://stackoverflow.com/questions/17995302/filtering-two-lists-simultaneously
    try:
        y, x = zip(*((y_el, x) for y_el, x in zip(y, x) if y_el >= tvdmin))
    except ValueError:
        pass
    x = x[1:-1]
    y = y[1:-1]
    return {
        'x': x,
        'y': y,
        'name': PurePath(well).stem,
        'fill': None,
        'mode': 'lines',
        'marker': {'color': 'black'}
    }


@cache.memoize(timeout=cache.TIMEOUT)
def make_surface_traces(well, reals, surf_name, cat, color):
    '''Creates surface traces for graph'''
    plot_data = []
    x = [trace[3] for trace in get_wfence(well, nextend=200, tvdmin=0).values]
    for j, real in enumerate(reals):
        y = get_hfence(well, surf_name, real, cat)['fence']
        showlegend = True if j == 0 else False
        plot_data.append(
            {
                'x': x,
                'y': y,
                'name': surf_name,
                'hoverinfo': 'none',
                'legendgroup': surf_name,
                'showlegend': showlegend,
                'real': real,
                'marker': {'color': color}
            })
    return pd.DataFrame(plot_data)


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def make_param_trace(well, grid, parameter) -> pd.DataFrame:

    try:
        hmin, hmax, vmin, vmax, values = get_gfence(well, grid, parameter)
    except TypeError:
        return pd.DataFrame([{
        'x0' : 0,
        'xmax' : 0,
        'dx' : 0,
        'y0' : 0,
        'ymax' : 0,
        'dy' : 0,
        'type' : 'heatmap',
        'z':  [[]]}])
    x_inc = (hmax-hmin)/values.shape[1]
    y_inc = (vmax-vmin)/values.shape[0]
    return pd.DataFrame([{
        'type': 'heatmap',
        'z': values.tolist(),
        'x0': hmin,
        'xmax': hmax,
        'dx': x_inc,
        'y0': vmin,
        'ymax': vmax,
        'dy': y_inc,
        'zsmooth': 'best'
    }])


@webvizstore
def get_realizations(ens, ens_path) -> pd.DataFrame:
    ensemble = scratch_ensemble(ens, ens_path)
    paths = [ensemble._realizations[real]._origpath
             for real in ensemble._realizations]
    reals = [real for real in ensemble._realizations]
    return pd.DataFrame({'REAL': reals, 'PATH': paths})\
        .sort_values(by=['REAL'])


@webvizstore
def get_file_paths(folder, suffix) -> pd.DataFrame:
    glob_pattern = f'{folder}/*{suffix}'
    files = sorted([f for f in glob(glob_pattern)])
    return pd.DataFrame({'PATH': files})
