import os
from uuid import uuid4
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache


class DiskUsage:
    '''### Disk usage

This container adds functionality for standard visualization of disk usage in
FMU projects. It adds a dashboard element where the user can choose between
showing disk usage, per user, either as a pie chart or as a bar chart.

* `scratch_dir`: Path to the directory you want to show disk usage for, e.g.
  `/scratch/fmu`.
* `title`: Optional title for the container.
'''

    def __init__(self, app, scratch_dir: str,
                 title: str = 'Disk usage'):

        self.title = title
        self.scratch_dir = scratch_dir
        self.chart_id = 'chart-id-{}'.format(uuid4())
        self.plot_type_id = 'plot-type-id-{}'.format(uuid4())
        self.disk_usage = get_disk_usage(self.scratch_dir)
        self.date = str(self.disk_usage['date'].unique()[0])
        self.users = self.disk_usage['userid']
        self.usage = self.disk_usage['usageKB']/(1024**2)
        self.set_callbacks(app)

    @property
    def layout(self):
        return html.Div([
                    html.H2(self.title),
                    html.P(
                        f'This is the disk usage on \
                        {self.scratch_dir} per user, \
                        as of {self.date}.'),
                    dcc.RadioItems(
                        id=self.plot_type_id,
                        options=[
                            {'label': i, 'value': i}
                            for i in ['Pie chart', 'Bar chart']],
                        value='Pie chart'),
                    dcc.Graph(
                        id=self.chart_id,
                        config={
                                'displaylogo': False,
                                'modeBarButtonsToRemove': ['sendDataToCloud']
                               }
                             )
               ])

    def set_callbacks(self, app):
        @app.callback(Output(self.chart_id, 'figure'),
                      [Input(self.plot_type_id, 'value')])
        def update_plot(plot_type):
            if plot_type == 'Pie chart':
                data = [{
                    'values': self.usage,
                    'labels': self.users,
                    'text': (self.usage).map('{:.2f} GB'.format),
                    'textinfo': 'label',
                    'textposition': 'inside',
                    'hoverinfo': 'label+text',
                    'type': 'pie'
                }]
                layout = {}

            elif plot_type == 'Bar chart':
                data = [{
                    'y': self.usage,
                    'x': self.users,
                    'text': (self.usage).map('{:.2f} GB'.format),
                    'hoverinfo': 'x+text',
                    'type': 'bar'
                }]
                layout = {
                    'yaxis': {
                        'title': 'Usage in Gigabytes',
                        'family': 'Equinor'
                    },
                    'xaxis': {
                        'title': 'User name',
                        'family': 'Equinor'
                    },
                }

            layout['height'] = 800
            layout['width'] = 1000
            layout['font'] = {'family': 'Equinor'}
            layout['hoverlabel'] = {'font': {'family': 'Equinor'}}

            return {'data': data, 'layout': layout}

    def add_webvizstore(self):
        return [(get_disk_usage, [{'scratch_dir': self.scratch_dir}])]


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def get_disk_usage(scratch_dir) -> pd.DataFrame:
    try:
        df = pd.read_csv(os.path.join(scratch_dir, 'disk_usage.csv'))
    except FileNotFoundError:
        raise FileNotFoundError(f'No disk usage file found at {scratch_dir}')

    last_date = sorted(list(df['date'].unique()))[-1]
    return df.loc[df['date'] == last_date]
