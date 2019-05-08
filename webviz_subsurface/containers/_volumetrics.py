from uuid import uuid4
import os
import numpy as np
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
import dash_table
from dash.dependencies import Input, Output
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webvizstore
from ..datainput import scratch_ensemble

class Volumetrics:
    """
    ### Volumetrics



    """
    print('init Volumetrics =================================================')
    def __init__(self,
                 app,
                 container_settings,
                 ensembles: list,
                 volfile: str,
                 title: str = 'Volumetrics'):

        self.title = title
        self.ensemble_names = ensembles
        self.ensemble_paths = tuple(
            (ens,
             container_settings['scratch_ensembles'][ens])
             for ens in ensembles)
        print('self.ensemble_paths: ', self.ensemble_paths)
        print('volfile: ', volfile)

        ensemble_dfs = []
        for ens, path in self.ensemble_paths:
            ensemble_i_df = scratch_ensemble(ens, path).load_csv(volfile)
            ensemble_i_df['ENSEMBLE'] = ens
            ensemble_dfs.append(ensemble_i_df)
        self.volumes = pd.concat(ensemble_dfs)
        print('concated dataframe dtypes: ', self.volumes.dtypes)
        print('concated dataframe shape: ', self.volumes.shape)

        self.radio_plot_type_id = 'radio-plot-type-{}'.format(uuid4())
        self.response_id = 'response-{}'.format(uuid4())
        self.chart_id = 'chart-{}'.format(uuid4())
        self.radio_selector_ids = 'radio-selectors-{}'.format(uuid4())
        self.selector_ids = {selector_id: str(uuid4())
                             for selector_id in self.selectors}
        self.table_cols = ["response", "selector", "mean", "stddev", "minimum",
                           "p90", "p10", "maximum"]

    print('add properties ---------------------------------------------------')

    @property
    def vol_columns(self):
        return list(self.volumes.columns)

    @property
    def all_selectors(self):
        return ['ENSEMBLE', 'ZONE', 'REGION', 'FACIES', 'LICENSE']

    @property
    def plot_types(self):
        return ['Histogram', 'Per Realization', 'Box Plot', 'Table']

    @property
    def selectors(self):
        return [selector
                for selector in self.all_selectors
                if selector in self.vol_columns]

    @property
    def responses(self):
        return [response
                for response in self.vol_columns
                if response not in self.selectors and response != 'REAL']

    @property
    def vol_callback_inputs(self):
        inputs = []
        inputs.append(Input(self.response_id, 'value'))
        inputs.append(Input(self.radio_plot_type_id, 'value'))
        inputs.append(Input(self.radio_selector_ids, 'value'))
        for selector in self.selectors:
            inputs.append(Input(self.selector_ids[selector], 'value'))
        return inputs

    @property
    def selector_dropdowns(self):
        dropdowns = []
        for selector in self.selectors:
            elements = list(self.volumes[selector].unique())
            multi = True
            value = elements
            if selector == 'ENSEMBLE':
                value = elements[0]
            dropdowns.append(
                html.Div(children=[
                    html.Details(children=[
                        html.Summary(selector),
                        dcc.Dropdown(
                            id=self.selector_ids[selector],
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
        return {
            'display': 'grid',
            'align-content': 'space-around',
            'justify-content': 'space-between',
            'grid-template-columns': 'repeat(4, 1fr)'
        }

    @property
    def style_layout(self):
        return {
            'display': 'grid',
            'align-content': 'space-around',
            'justify-content': 'space-between',
            'grid-template-columns': '5fr 1fr'
        }

    def group_radio_options(self, selectors):
        options = ['NONE']
        options.extend(selectors)
        return [{'label': i, 'value': i} for i in options]

    @property
    def plot_options_layout(self):
        return html.Div(style=self.style_plot_options,children=[
                        html.Div(children=[
                            html.P('Response:', style={
                                'font-weight': 'bold'}),
                            dcc.Dropdown(
                                id=self.response_id,
                                options=[{'label': i, 'value': i}
                                         for i in self.responses],
                                value=self.responses[0])
                        ]),
                        html.Div(children=[
                            html.P('Plot type:', style={
                                'font-weight': 'bold'}),
                            dcc.Dropdown(
                                id=self.radio_plot_type_id,
                                options=[{'label': i, 'value': i}
                                         for i in self.plot_types],
                                value='Histogram'),
                        ]),
                        html.Div(children=[
                            html.P('Group by:', style={
                                'font-weight': 'bold'}),
                            dcc.Dropdown(
                                id=self.radio_selector_ids,
                                options=self.group_radio_options(
                                    self.selectors),
                                value='NONE')]),
                        ])

    print('layout ===========================================================')
    @property
    def layout(self):
        return html.Div([
            html.H2(self.title),
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

    print('callback ---------------------------------------------------------')
    def set_callbacks(self, app):
        @app.callback(
            Output(self.chart_id, 'children'),
            self.vol_callback_inputs)
        def render_vol_chart(*args):
            response = args[0]
            plot_type = args[1]
            group = args[2]
            selections = args[3:]
            # data = filter_dataframe(self.volumes, ['REAL'], [reals])
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
                    columns=[{"name": i, "id": i} for i in self.table_cols],
                    data=traces)
            # Else make a graph object
            else:
                return dcc.Graph(figure={
                    'data': traces,
                    'layout': plot_layout(plot_type)}
                )

        @app.callback(
            Output(self.selector_ids['ENSEMBLE'], 'multi'),
            [Input(self.radio_selector_ids, 'value')])
        def set_iteration_selector(group):
            '''If iteration is selected as group by set the iteration
            selector to allow multiple selections, else use single selection
            '''
            if group == 'ENSEMBLE':
                return True
            else:
                return False

    print('cache ------------------------------------------------------------')
@cache.memoize(timeout=cache.TIMEOUT)
def plot_data(plot_type, dframe, response, name):
    values = dframe[response]
    values.replace(0, np.nan, inplace=True)
    if plot_type == 'Histogram':
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
    if plot_type == 'Per Realization':
        return {
            'y': values,
            'x': dframe['REAL'],
            'name': name,
            'type': 'bar'
        }
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
def plot_layout(plot_type):
    if plot_type == 'Histogram':
        return {
            'barmode': 'overlay',
            'bargap': 0.05
        }
    if plot_type == 'Box Plot':
        return {}
    if plot_type == 'Per Realization':
        return {
            'margin': {
                'l': 40,
                'r': 40,
                'b': 30,
                't': 10},
            'barmode': 'stack'}


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
