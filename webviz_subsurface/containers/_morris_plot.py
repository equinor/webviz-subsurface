from uuid import uuid4
from pathlib import Path
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
from webviz_subsurface_components import Morris

class MorrisPlot:
    '''### Morris

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

    def __init__(self, app, csv_file: Path,
                 title: str = 'Morris plot'):

        self.title = title
        self.graph_id = 'graph-{}'.format(uuid4())
        self.vector_id = 'vector-{}'.format(uuid4())
        self.csv_file = csv_file
        self.morris_data = read_csv(self.csv_file)
        self.vector_names = self.morris_data['name'].unique()
        self.set_callbacks(app)

    @property
    def layout(self):
        return html.Div([
                   html.H2(self.title),
                    dcc.Dropdown(id=self.vector_id,
                         clearable=False,
                         options=[{'label': i, 'value': i}
                                  for i in list(self.vector_names)],
                         value=self.vector_names[0]),
                   Morris(
                    id=self.graph_id)
               ])

    def add_webvizstore(self):
        return [(read_csv, [{'csv_file': self.csv_file}])]

    def set_callbacks(self, app):
        @app.callback([
            Output(self.graph_id, 'output'),
            Output(self.graph_id, 'parameter'),
            Output(self.graph_id, 'parameters')],
            [Input(self.vector_id, 'value')])
        def update_plot(vector):
            df = self.morris_data[self.morris_data['name'] == vector]
            df = df.sort_values('time')
            output = df[['mean', 'max', 'min', 'time']]
            output = output.drop_duplicates()
            output = output.to_dict(orient='records')
            parameters = []

            for name in self.morris_data['name'].unique():
                if name != vector:
                    name_df = self.morris_data[self.morris_data['name'] == name]
                    parameters.append({
                        'main': list(name_df['morris_main']),
                        'name': str(name),
                        'interactions': list(name_df['morris_interaction'])
                        })
            return output, vector, parameters


cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file)
