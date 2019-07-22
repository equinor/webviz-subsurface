from uuid import uuid4
import json
import pandas as pd
import dash_html_components as html
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
from webviz_config.containers import WebvizContainer
from webviz_subsurface_components import Map
from ..datainput import scratch_ensemble


class SubsurfaceMap(WebvizContainer):
    '''### Subsurface map

This container visualizes the subsurface. Currently only supporting reservoir
model grid maps. In addition to show a map, it can visualize the flow pattern
in the simulation output using streamlines.

* `ensemble`: Which ensemble in `container_settings` to visualize.
* `map_value`: Which property to show in the map (e.g. `PERMX`).
* `flow_value`: Which property to use for the streamlines animation
  (e.g. `FLOWAT`).
* `time_step`: Which report or time step to use in the simulation output.
* `title`: Optional title for the container.
'''

    def __init__(self, container_settings, ensemble, map_value: str,
                 flow_value: str, time_step):

        self.map_id = 'map-{}'.format(uuid4())
        self.map_value = map_value
        self.flow_value = flow_value
        self.time_step = time_step

        self.ensemble_path = container_settings['scratch_ensembles'][ensemble]
        self.map_data = get_map_data(self.ensemble_path, self.map_value,
                                     self.flow_value, self.time_step)

    @property
    def layout(self):
        return html.Div([
                   Map(id=self.map_id, data=self.map_data)
               ])

    def add_webvizstore(self):
        return [(get_uncompressed_data, [{'ensemble_path': self.ensemble_path,
                                          'map_value': self.map_value,
                                          'flow_value': self.flow_value,
                                          'time_step': self.time_step}])]


@cache.memoize(timeout=cache.TIMEOUT)
def get_map_data(ensemble_path, map_value, flow_value,
                 time_step):
    '''Returns map data in the format of a JSON string, suitable for the
    corresponding subsurface map component in
    https://github.com/equinor/webviz-subsurface-components
    '''

    grid = get_uncompressed_data(ensemble_path, map_value, flow_value,
                                 time_step)

    INDICES_COL = ['i', 'j', 'k']
    X_COL = ['x0', 'x1', 'x2', 'x3']
    Y_COL = ['y0', 'y1', 'y2', 'y3']
    FLOW_COL = ['FLOWI+', 'FLOWJ+']

    RESOLUTION = 1000

    grid = grid[INDICES_COL + X_COL + Y_COL + ['value'] + FLOW_COL]
    grid = grid[grid['value'] > 0]

    xmin, xmax = grid[X_COL].values.min(), grid[X_COL].values.max()
    ymin, ymax = grid[Y_COL].values.min(), grid[Y_COL].values.max()

    flowmin, flowmax = grid[FLOW_COL].values.min(), grid[FLOW_COL].values.max()

    valmin, valmax = grid['value'].min(), grid['value'].max()

    if (xmax - xmin) > (ymax - ymin):
        coord_scale = RESOLUTION/(xmax - xmin)
    else:
        coord_scale = RESOLUTION/(ymax - ymin)

    grid[X_COL] = (grid[X_COL] - xmin) * coord_scale
    grid[Y_COL] = (grid[Y_COL] - ymin) * coord_scale
    grid[X_COL + Y_COL] = grid[X_COL + Y_COL].astype(int)

    flow_scale = RESOLUTION/(flowmax - flowmin)
    grid[FLOW_COL] = (grid[FLOW_COL] - flowmin) * flow_scale
    grid[FLOW_COL] = grid[FLOW_COL].astype(int)

    val_scale = RESOLUTION/(valmax - valmin)
    grid['value'] = (grid['value'] - valmin) * val_scale
    grid['value'] = grid['value'].astype(int)

    grid[INDICES_COL] = grid[INDICES_COL].astype(int)

    data = {
            'values': grid.values.tolist(),
            'linearscales': {
                'coord': [float(coord_scale), float(xmin), float(ymin)],
                'value': [float(val_scale), float(valmin)],
                'flow': [float(flow_scale), float(flowmin)]
                            }
            }

    return json.dumps(data, separators=(',', ':'))


@webvizstore
def get_uncompressed_data(ensemble_path, map_value, flow_value,
                          time_step) -> pd.DataFrame:

    ens = scratch_ensemble('', ensemble_path)

    properties = [map_value, f'{flow_value}I+', f'{flow_value}J+']
    if 'PERMX' not in properties:
        properties.append('PERMX')

    grid = ens.get_eclgrid(properties, report=time_step)

    grid = grid[grid['PERMX'] > 0]  # Remove inactive grid cells

    grid['value'] = grid[map_value]
    grid['FLOWI+'] = grid[f'{flow_value}I+']
    grid['FLOWJ+'] = grid[f'{flow_value}J+']

    # Webviz map component uses different corner point terminology than libecl
    for (new, old) in [('x0', 'x1'), ('x1', 'x2'), ('x2', 'x4'),
                       ('y0', 'y1'), ('y1', 'y2'), ('y2', 'y4')]:
        grid[new] = grid[old]

    return grid
