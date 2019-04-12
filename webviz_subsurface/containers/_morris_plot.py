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

    def __init__(self, app, csv_file: Path,
                 title: str = 'Morris plot'):

        self.title = title
        self.graph_id = 'graph-{}'.format(uuid4())
        self.vector_id = 'vector-{}'.format(uuid4())
        self.csv_file = csv_file
        self.morris_data = read_csv(self.csv_file)
        self.vector_names = self.morris_data['name'].unique()
        self.output = [
            {'mean': 0.0, 'max': 0.0, 'min': 0.0, 'time': '2000-01-01T00:00:00'}, 
            {'mean': 1821300.2, 'max': 2022804.5, 'min': 900429.1, 'time': '2001-01-01T00:00:00'}, 
            {'mean': 3595926.9, 'max': 5060090.5, 'min': 1161664.8, 'time': '2002-01-01T00:00:00'}, 
            {'mean': 4919365.7, 'max': 7102369.0, 'min': 2150000.5, 'time': '2003-01-01T00:00:00'}]

        self.parameters = [
            {'main': [0.0, 1327720.5, 3439176.1, 5311292.8], 'name': 'FWL', 'interactions': [0.0, 1116199.0, 2541439.9, 2836076.4]},
            {'main': [0.0, 844.65, 5093.1, 12363.55], 'name': 'MULTFLT_F1', 'interactions': [0.0, 1231.4, 4597.0, 13793.5]},
            {'main': [0.0, 908911.5, 1506246.1, 2000438.5], 'name': 'RANGE_PAR', 'interactions': [0.0, 1396000.4, 1900671.3, 1933889.5]},
            {'main': [0.0, 10.1, 7413.1, 322.3], 'name': 'MULTZ_MIDREEK', 'interactions': [0.0, 211.1, 3098.9, 5619.7]}, 
            {'main': [0.0, 1010601.3, 1822840.3, 2869195.5], 'name': 'AZIMUTH', 'interactions': [0.0, 1262311.8, 1822908.7, 2833047.4]},
            {'main': [0.0, 167888.5, 398770.5, 598481.5], 'name': 'MEANPERMMULT', 'interactions': [0.0, 114457.6, 180225.4, 201267.2]}]

        self.parameter = 'FOPT'
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
                    id=self.graph_id, 
                    output=self.output,
                    parameters=self.parameters,
                    parameter=self.parameter)
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
            for name in df['name'].unique():
                name_df = df[df['name'] == name]
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
