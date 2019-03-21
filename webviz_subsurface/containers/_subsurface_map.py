from uuid import uuid4
import pandas as pd
import dash_html_components as html
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
from webviz_subsurface_components import Map
from ..datainput import scratch_ensemble


class SubsurfaceMap:
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
                 flow_value: str, time_step, title: str = 'Subsurface map'):

        self.title = title
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
                   html.H2(self.title),
                   Map(id=self.map_id, data=self.map_data.to_json())
               ])

    def add_webvizstore(self):
        return [(get_map_data, [{'ensemble_path': self.ensemble_path,
                                 'map_value': self.map_value,
                                 'flow_value': self.flow_value,
                                 'time_step': self.time_step}])]


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_map_data(ensemble_path, map_value, flow_value,
                 time_step) -> pd.DataFrame:

    ens = scratch_ensemble('', ensemble_path)

    grid = ens.get_eclgrid([map_value, f'{flow_value}I+', f'{flow_value}J+'],
                           report=time_step)

    grid['value'] = grid[map_value]
    grid['FLOWI+'] = grid[f'{flow_value}I+']
    grid['FLOWJ+'] = grid[f'{flow_value}J+']

    # Webviz map component uses different corner point terminology than libecl
    for (new, old) in [('x0', 'x1'), ('x1', 'x2'), ('x2', 'x4'),
                       ('y0', 'y1'), ('y1', 'y2'), ('y2', 'y4')]:
        grid[new] = grid[old]

    return grid
