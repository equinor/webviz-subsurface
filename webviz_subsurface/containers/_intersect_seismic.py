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
from ..datainput import (get_file_paths, get_realizations,
                         make_well_trace, make_surface_traces,
                         make_cube_trace, well_to_df, surface_to_df)


class IntersectSeismic(WebvizContainer):
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
        'grid-template-columns': '1fr',
    }
    CONTROL_STYLE = {
        'display': 'grid',
        'align-content': 'space-around',
        'justify-content': 'space-between',
        'grid-template-columns': '1fr 1fr 1fr 1fr 1fr',
        'padding-right': '20px',
        'padding-left': '20px',
        'font-size': '10px'
    }

    def __init__(self, app, container_settings, ensemble,
                 well_path, surface_cat, surface_names,
                 cube_path, cubes: list, well_suffix='.rmswell'):

        self.well_path = well_path
        self.cube_path = cube_path
        self.cubes = cubes
        self.ensemble_path = container_settings['scratch_ensembles'][ensemble]
        self.ensemble = ensemble
        self.well_suffix = well_suffix
        self.surface_cat = surface_cat
        self.surface_names = surface_names
        self.assign_ids()
        self.set_callbacks(app)

    def assign_ids(self):
        unique_id = f'{uuid4()}'
        self.well_list_id = f'well-list-id-{unique_id}'
        self.cube_list_id = f'cube-list-id-{unique_id}'
        self.real_list_id = f'real-list-id-{unique_id}'
        self.surf_list_id = f'surf-list-id-{unique_id}'
        self.color_scale_id = f'color-scale-id-{unique_id}'
        self.intersection_id = f'intersection-id-{unique_id}'

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
        return {surf: IntersectSeismic.COLORS[i % len(IntersectSeismic.COLORS)]
                for i, surf in enumerate(self.surface_names)}

    def get_seis_path(self, cube):
        return os.path.join(self.cube_path, f'{cube}.segy')

    @cache.memoize(timeout=cache.TIMEOUT)
    def plot_xsection(self, cube, well, reals, surf_names,
                      color_scale, tvdmin=0):
        '''Plots all lines in intersection'''
        traces = []
        layout = self.graph_layout
        cube_trace = make_cube_trace(
            well, self.get_seis_path(cube)).to_dict('rows')
        cube_trace[0]['colorscale'] = color_scale
        cube_trace[0]['name'] = cube
        cube_trace[0]['colorbar'] = {'x': 1, 'showticklabels': False}
        layout['xaxis']['range'] = [cube_trace[0]['x0'], cube_trace[0]['xmax']]
        layout['xaxis']['autorange'] = False
        layout['yaxis']['range'] = [cube_trace[0]['ymax'], cube_trace[0]['y0']]
        layout['yaxis']['autorange'] = False

        for s_name in surf_names:
            traces.extend(
                make_surface_traces(
                    well, reals, s_name, self.surface_cat,
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

    @property
    def view_layout(self):
        return html.Div(style=IntersectSeismic.CONTROL_STYLE,
            children=[
            html.Div([
                    html.P('Seismic cube:', style={'font-weight': 'bold'}),
                    dcc.Dropdown(
                        style={'width': '100%'},
                        id=self.cube_list_id,
                        options=[{'label': c, 'value': c}
                                 for c in self.cubes],
                        value=self.cubes[0],
                        clearable=False
                    )]),
                  html.Div([
                         html.P('Seismic color:', style={
                              'font-weight': 'bold'}),
                         dcc.Dropdown(
                             # style={'width': '50%'},
                             id=self.color_scale_id,
                             options=[{'label': c, 'value': c}
                                      for c in IntersectSeismic.COLOR_SCALES],
                             value='RdBu',
                             clearable=False
                         )]),
                     html.Div([
                         html.P('Well:', style={'font-weight': 'bold'}),
                         dcc.Dropdown(
                              # style={'width': '50%'},
                              id=self.well_list_id,
                              options=[{'label': PurePath(well).stem, 'value': well}
                                       for well in self.well_names],
                              value=self.well_names[0],
                              clearable=False
                              )]),
                     html.Div([
                         html.P('Surfaces:', style={
                              'font-weight': 'bold'}),
                         dcc.Dropdown(
                             id=self.surf_list_id,
                             options=[{'label': r, 'value': r}
                                      for r in self.surface_names],
                             value=self.surface_names[0],
                             multi=True,
                             placeholder='All surfaces'
                         )]),
                     html.Div([
                         html.P('Realizations:', style={
                              'font-weight': 'bold'}),
                         dcc.Dropdown(
                             id=self.real_list_id,
                             options=[{'label': real, 'value': path}
                                      for path, real in self.realizations.items()],
                             value=list(self.realizations.keys())[0],
                             multi=True,
                             placeholder='All realizations'
                         )])
                ])

    @property
    def layout(self):
        return html.Div(style=IntersectSeismic.LAYOUT_STYLE,
                        children=[
                            html.Div(children=[self.view_layout]),
                            html.Div(children=[
                                dcc.Graph(id=self.intersection_id)
                            ])
                        ])
        

    def set_callbacks(self, app):
        @app.callback(
            Output(self.intersection_id, 'figure'),
            [Input(self.cube_list_id, 'value'),
             Input(self.well_list_id, 'value'),
             Input(self.real_list_id, 'value'),
             Input(self.surf_list_id, 'value'),
             Input(self.color_scale_id, 'value')])
        def set_fence(_cube_path, _well_path, _reals, _surfs, color_scale):
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
            xsect = self.plot_xsection(
                _cube_path, _well_path, _reals, s_names, color_scale)
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
            funcs.append((make_cube_trace, [{'well': well,
                                             'cube': self.get_seis_path(cube)}
                                            for cube in self.cubes]))
        for surf in self.surface_names:
            for path in self.realizations.keys():
                funcs.append((surface_to_df, [
                    {'s_name': surf,
                             'real_path': path,
                             'surface_cat': self.surface_cat}]))
        return funcs
