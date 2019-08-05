from uuid import uuid4
import numpy as np
import dash_html_components as html
import dash_core_components as dcc
import dash_table
from dash.dependencies import Input, Output
from webviz_config.common_cache import cache
from webviz_config.containers import WebvizContainer
from ..datainput import extract_volumes


class InplaceVolumes(WebvizContainer):
    '''### Volumetrics

This container visualizes inplace volumetrics results from
csv files stored on standard format.

* `ensembles`: Which ensembles in `container_settings` to visualize.
* `volfiles`:  Key/value pair of csv files E.g. (geogrid: geogrid--oil.csv)
* `volfolder`: Optional local folder for csv files
* `response`: Optional initial visualized volume response

'''

    RESPONSES = {
        'BULK_OIL': 'Bulk Volume (Oil)',
        'NET_OIL': 'Net Volume (Oil)',
        'PORE_OIL': 'Pore Volume (Oil)',
        'HCPV_OIL': 'Hydro Carbon Pore Volume (Oil)',
        'STOIIP_OIL': 'Stock Tank Oil Initially Inplace',
        'BULK_GAS': 'Bulk Volume (Gas)',
        'NET_GAS': 'Net Volume (Gas)',
        'PORE_GAS': 'Pore Volume (Gas)',
        'HCPV_GAS': 'Hydro Carbon Pore Volume (Gas)',
        'GIIP_GAS': 'Gas Initially in-place',
        'RECOVERABLE_OIL': 'Recoverable Volume (Oil)',
        'RECOVERABLE_GAS': 'Recoverable Volume (Gas)'
    }

    def __init__(self, app, container_settings, ensembles: list,
                 volfiles: dict, volfolder: str = 'share/results/volumes',
                 response: str = 'STOIIP_OIL'):

        self.ens_paths = tuple((ens,
                                container_settings['scratch_ensembles'][ens])
                               for ens in ensembles)
        self.volfiles = tuple(volfiles.items())
        self.volfolder = volfolder
        self.initial_response = response
        self.volumes = extract_volumes(self.ens_paths,
                                       self.volfolder,
                                       self.volfiles)
        self.radio_plot_type_id = 'radio-plot-type-{}'.format(uuid4())
        self.response_id = 'response-{}'.format(uuid4())
        self.chart_id = 'chart-{}'.format(uuid4())
        self.radio_selectors_id = 'radio-selectors-{}'.format(uuid4())
        self.selectors_id = {
            x: str(uuid4())
            for x in self.selectors}
        self.table_cols = ['response', 'selector', 'mean',
                           'stddev', 'minimum', 'p90', 'p10', 'maximum']

        self.set_callbacks(app)

    def add_webvizstore(self):
        return [(extract_volumes, [
            {
                'ensemble_paths': self.ens_paths,
                'volfolder': self.volfolder,
                'volfiles': self.volfiles
            }])]

    @property
    def vol_columns(self):
        '''List of all columns in dataframe'''
        return list(self.volumes.columns)

    @property
    def all_selectors(self):
        '''List of all possible selectors'''
        return ['SOURCE', 'ENSEMBLE', 'ZONE', 'REGION', 'FACIES', 'LICENSE']

    @property
    def plot_types(self):
        '''List of available plots'''
        return ['Histogram', 'Per realization', 'Box Plot', 'Table']

    @property
    def selectors(self):
        '''List of available selector columns in dframe'''
        return [x
                for x in self.all_selectors
                if x in self.vol_columns]

    @property
    def responses(self):
        '''List of available volume responses in dframe'''
        return [x
                for x in self.vol_columns
                if x not in self.selectors and x != 'REAL']

    @property
    def vol_callback_inputs(self):
        '''Returns all Dash inputs for selecting and filtering volumes
        The number of inputs will vary depending on the available
        selector columns in the volumes dataframe
        '''
        inputs = []
        inputs.append(Input(self.response_id, 'value'))
        inputs.append(Input(self.radio_plot_type_id, 'value'))
        inputs.append(Input(self.radio_selectors_id, 'value'))
        for selector in self.selectors:
            inputs.append(Input(
                self.selectors_id[selector], 'value'))
        return inputs

    @property
    def selector_dropdowns(self):
        '''Makes dropdowns for each selector.
        Args:
            dframe - Volumetrics Dataframe
            selectors - List of selector columns
        Return:
            dcc.Dropdown objects
        '''
        dropdowns = []
        for selector in self.selectors:
            elements = list(self.volumes[selector].unique())
            multi = True

            value = elements
            if selector == 'ENSEMBLE' or selector == 'SOURCE':
                value = elements[0]
            dropdowns.append(
                html.Div(children=[
                    html.Details(open=True, children=[
                        html.Summary(selector.lower().capitalize()),
                        dcc.Dropdown(
                            id=self.selectors_id[selector],
                            options=[{'label': i, 'value': i}
                                     for i in elements],
                            value=value,
                            multi=multi)
                    ])
                ])
            )
        return dropdowns

    @property
    def style_plot_options(self):
        '''Simple grid layout for the selector row'''
        return {
            'display': 'grid',
            'align-content': 'space-around',
            'justify-content': 'space-between',
            'grid-template-columns': '2fr 1fr 1fr 1fr'
        }

    @property
    def style_layout(self):
        '''Simple grid layout for the main elements'''
        return {
            'display': 'grid',
            'align-content': 'space-around',
            'justify-content': 'space-between',
            'grid-template-columns': '5fr 1fr'
        }

    @staticmethod
    def group_radio_options(selectors):
        '''Returns options for a radio button used for grouping
        volume results on a dataframe column.
        The option 'NONE' is added to allow no grouping
        '''
        options = ['NONE']
        options.extend(selectors)
        return [{'label': i.lower().capitalize(), 'value': i} for i in options]

    @property
    def plot_options_layout(self):
        '''Row layout of dropdowns for plot options'''
        return html.Div(style=self.style_plot_options, children=[
                        html.Div(children=[
                            html.P('Response:', style={
                                'font-weight': 'bold'}),
                            dcc.Dropdown(
                                id=self.response_id,
                                options=[
                                    {'label': InplaceVolumes.RESPONSES.get(
                                        i, i), 'value': i}
                                    for i in self.responses],
                                value=self.initial_response
                                if self.initial_response in self.responses
                                else self.responses[0])
                        ]),
                        html.Div(children=[
                            html.P('Plot type:', style={
                                'font-weight': 'bold'}),
                            dcc.Dropdown(
                                id=self.radio_plot_type_id,
                                options=[{'label': i, 'value': i}
                                         for i in self.plot_types],
                                value='Per realization'),
                        ]),
                        html.Div(children=[
                            html.P('Group by:', style={
                                'font-weight': 'bold'}),
                            dcc.Dropdown(
                                id=self.radio_selectors_id,
                                options=self.group_radio_options(
                                    self.selectors),
                                value='NONE')]),
                        ])

    @property
    def layout(self):
        '''Main layout'''
        return html.Div([
            html.Div(style=self.style_layout, children=[
                html.Div(children=[
                    self.plot_options_layout,
                    html.Div(id=self.chart_id),
                ]),
                html.Div(children=[
                    html.P('Filters:', style={'font-weight': 'bold'}),
                    html.Div(
                        children=self.selector_dropdowns
                    ),
                ])

            ]),
        ])

    def set_callbacks(self, app):
        @app.callback(
            Output(self.chart_id, 'children'),
            self.vol_callback_inputs)
        def render_vol_chart(*args):
            '''Renders a volume visualization which could either by a dcc.Graph
            or a Dash table object.
            The arguments are given by the vol_callback_inputs property
            Args:
                response: The volumetrics response to plot
                plot_type: The type of graph/table to plot
                group: The selector to group the data by
                selections: Active values from the selector columns
            Return:
                dcc.Graph/dash_table.DataTable
            '''
            response = args[0]
            plot_type = args[1]
            group = args[2]
            selections = args[3:]
            data = self.volumes
            data = filter_dataframe(data, self.selectors, selections)
            # If not grouped make one trace
            if group == 'NONE':
                dframe = data.groupby('REAL').sum().reset_index()
                traces = [plot_data(plot_type, dframe, response, 'Total')]

            # Else make one trace for each group member
            else:
                traces = []
                for name, vol_group_df in data.groupby(group):
                    dframe = vol_group_df.groupby('REAL').sum().reset_index()
                    trace = plot_data(plot_type, dframe, response, name)
                    if trace is not None:
                        traces.append(trace)
            # Make a dash table if table is selected
            if plot_type == 'Table':
                return dash_table.DataTable(
                    columns=[{'name': i, 'id': i} for i in self.table_cols],
                    data=traces)
            # Else make a graph object
            else:
                return dcc.Graph(figure={
                    'data': traces,
                    'layout': plot_layout(plot_type, response)}
                )

        @app.callback(
            [Output(self.selectors_id['ENSEMBLE'], 'multi'),
             Output(self.selectors_id['ENSEMBLE'], 'value')],
            [Input(self.radio_selectors_id, 'value')])
        def set_iteration_selector(group_by):
            '''If iteration is selected as group by set the iteration
            selector to allow multiple selections, else use single selection
            '''
            if group_by == 'ENSEMBLE':
                return True, list(self.volumes['ENSEMBLE'].unique())
            else:
                return False, list(self.volumes['ENSEMBLE'].unique())[0]

        @app.callback(
            [Output(self.selectors_id['SOURCE'], 'multi'),
             Output(self.selectors_id['SOURCE'], 'value')],
            [Input(self.radio_selectors_id, 'value')])
        def set_source_selector(group_by):
            '''If iteration is selected as group by set the iteration
            selector to allow multiple selections, else use single selection
            '''
            if group_by == 'SOURCE':
                return True, list(self.volumes['SOURCE'].unique())
            else:
                return False, list(self.volumes['SOURCE'].unique())[0]


@cache.memoize(timeout=cache.TIMEOUT)
def plot_data(plot_type, dframe, response, name):
    values = dframe[response]

    if plot_type == 'Histogram':
        if values.nunique() == 1:
            values = values[0]
        return {
            'x': values,
            'type': 'histogram',
            'name': name
        }
    if plot_type == 'Box Plot':
        return {
            'y': values,
            'name': name,
            'type': 'box'
        }
    if plot_type == 'Per realization':
        return {
            'y': values,
            'x': dframe['REAL'],
            'name': name,
            'type': 'bar'
        }
    values.replace(0, np.nan, inplace=True)
    if plot_type == 'Table':
        try:
            return {
                'response': response,
                'selector': str(name),
                'minimum': f'{values.min():.2e}',
                'maximum': f'{values.max():.2e}',
                'mean': f'{values.mean():.2e}',
                'stddev': f'{values.std():.2e}',
                'p10': f'{np.percentile(values, 90):.2e}',
                'p90': f'{np.percentile(values, 10):.2e}'
            }
        except KeyError:
            return None


@cache.memoize(timeout=cache.TIMEOUT)
def plot_layout(plot_type, response):

    if plot_type == 'Histogram':
        return {
            'bargap': 0.05,
            'xaxis': {'title': response},
            'yaxis': {'title': 'Count'}
        }
    if plot_type == 'Box Plot':
        return {'yaxis': {'title': response}}

    if plot_type == 'Per Realization':
        return {
            'margin': {
                'l': 40,
                'r': 40,
                'b': 30,
                't': 10},
            'yaxis': {'title': response},
            'xaxis': {'title': 'Realization'}}


@cache.memoize(timeout=cache.TIMEOUT)
def filter_dataframe(dframe, columns, column_values):
    df = dframe.copy()
    if not isinstance(columns, list):
        columns = [columns]
    for filt, col in zip(column_values, columns):
        if isinstance(filt, list):
            df = df.loc[df[col].isin(filt)]
        else:
            df = df.loc[df[col] == filt]
    return df
