import os
from uuid import uuid4
import pathlib
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
import webviz_subsurface_components as wsc
from ..datainput import generate_surface, generate_well_path
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
import yaml


class View3D:
    '''### View3D

This container adds a page with a 3D scene for rendering subsurface data.

* `config`: Configuration file for the data.
'''
    def __init__(self, app, config: pathlib.Path):
        self.vizvaz_id = f'vizvaz-{uuid4()}'
        self.selectors_id = f'selectors-{uuid4()}'
        self.modal_id = f'modal-{uuid4()}'
        self.config_path = config
        self.config = self.read_config()
        self.set_callbacks(app)

    def read_config(self):
        with open(get_path(self.config_path), 'r') as stream:
            try:
                config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                raise(exc)
        return config

    @property
    def surfaces(self):
        return self.config['surfaces']

    @property
    def wells(self):
        return self.config['wells']

    @property
    def center_x(self):
        return self.config['center_x']

    @property
    def center_y(self):
        return self.config['center_y']

    @property
    def extent(self):
        return self.config['extent']

    @property
    def inc(self):
        return self.config['increment']

    @property
    def path(self):
        return self.config['path']

    @property
    def style_modal(self):
        return {
            'position': 'fixed',
            'top': '5%',
            'left': '20%',
            'z-index': '1000',
            'width': '20%',
            'height': '20%',
            }

    def selector(self, id, values, multi=False):
        return dcc.Dropdown(
            # inputStyle={'display':'table-'},
            id=id,
            options=[{'label': s, 'value':s}
                for s in values],
                clearable=False,
                value=values[0],
                multi=multi
                )
    @property
    def selectors(self):
        layout = []
        layout.append(html.H3('Surfaces'))
        for surf_type, surfs in self.surfaces.items():
            layout.append(html.P(surf_type))
            layout.append(self.selector(
                f'{surf_type}--{self.selectors_id}', surfs, multi=False))
        layout.append(html.H3('Wells'))
        layout.append(self.selector(
            f'wells--{self.selectors_id}', self.wells, multi=True))
        return layout

    @property
    def layout(self):
        return html.Div(children=[
            html.Div(
                id=self.modal_id,
                children=[
                    html.Div(
                        id=self.selectors_id,
                        children=self.selectors,
                        style=self.style_modal)
                ]),
            html.Div(children=[wsc.View3D(
                id=self.vizvaz_id,
                center_x=self.center_x,
                center_y=self.center_y)])
        ])

    def set_callbacks(self, app):
        @app.callback(
            Output(self.vizvaz_id, 'surface'),
            [Input(f'depth--{self.selectors_id}', 'value')])
        def update_surface(s):
            surf_data = get_surface_data(self.path, s, 'depth', self.center_x,
                                         self.center_y, self.extent, self.inc)
            return surf_data

        @app.callback(
            Output(self.vizvaz_id, 'wells'),
            [Input(f'wells--{self.selectors_id}', 'value')])
        def update_wells(wells):
            well_data = get_well_path_data(self.path, wells)
            return well_data

    def add_webvizstore(self):
        funcs = []
        funcs.append((get_path,
            [{'config': self.config_path}]))
        for surf_type, surfs in self.surfaces.items():
            for surf in surfs:
                path = os.path.join(self.path, 'maps', surf+'--'+surf_type+'.gri')
                funcs.append((generate_surface,
                                [{
                                'path': path,
                                'x': self.center_x,
                                'y': self.center_y,
                                'extent': self.extent,
                                'inc': self.inc}]))
        for well in self.wells:
            path = os.path.join(self.path, 'wells', str(well)+'.rmswell')
            funcs.append((generate_well_path,[{'path': path, 'downsample':None}]))
        return funcs


@cache.memoize(timeout=cache.TIMEOUT)
def get_surface_data(path, surf_names, cat, x, y, extent, inc):
    if not isinstance(surf_names, list):
        surf_names = [surf_names]
    surf_paths = [os.path.join(path, 'maps', name+'--'+cat+'.gri')
                for name in surf_names]
    return [{
        'z': generate_surface(path, x, y, extent, inc).to_numpy().tolist(),
        'size': {'x': extent*2, 'y': extent*2},
        'name' : name} for name, path in zip(surf_names, surf_paths)]

@cache.memoize(timeout=cache.TIMEOUT)
def get_well_path_data(path, well_names):
    if not isinstance(well_names, list):
        well_names = [well_names]
    well_paths = [os.path.join(path, 'wells', str(well)+'.rmswell')
                for well in well_names]
    return [{
        'positionLog':(generate_well_path(wpath, downsample=None)).to_numpy().tolist(),
        'name' : name} for name, wpath in zip(well_names, well_paths)]

@webvizstore
def get_path(config) -> pathlib.Path:
    return config
