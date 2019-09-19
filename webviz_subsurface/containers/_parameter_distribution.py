from uuid import uuid4
import numpy as np
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output
import dash_table
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
from webviz_config.containers import WebvizContainer
from webviz_subsurface.datainput import load_parameters
import plotly.express as px


class ParameterDistribution(WebvizContainer):
    '''### ParameterDistribution

This container shows parameter distribution as a histogram.
Parameter statistics are shown in a table.

* `ensembles`: Which ensembles in `container_settings` to visualize.
'''

    def __init__(self, app, container_settings,
                 ensembles):

        self.ensembles = tuple(
            (ens, container_settings['scratch_ensembles'][ens])
            for ens in ensembles)
        self.parameters = load_parameters(
            ensemble_paths=self.ensembles, ensemble_set_name='EnsembleSet')
        self.parameter_columns = [col for col in list(
            self.parameters.columns) if col not in ['REAL', 'ENSEMBLE']]
        self.calculations = ['Ensemble', 'Min', 'Mean', 'Max', 'Stddev']
        self.uid = f'{uuid4()}'
        self.table_id = f'table-id-{self.uid}'
        self.histogram_id = f'histogram-id-{self.uid}'
        self.pcol_id = f'pcol-id-{self.uid}'
        self.set_callbacks(app)

    def set_grid_layout(self, columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout('2fr 4fr'),
            children=[
                html.Div([
                    html.Div([
                    html.H5('Select parameter'),
                    dcc.Dropdown(
                        id=self.pcol_id,
                        options=[{'value': col, 'label': col}
                                 for col in self.parameter_columns],
                        value=self.parameter_columns[0],
                        clearable=False),
                    html.Br(),html.Br(),html.Br(),html.Br(),
                    html.H5('Parameter statistics'),
                    dash_table.DataTable(
                        id=self.table_id,
                        columns=[{"name": i, "id": i}
                                 for i in self.calculations])
                    ]),
                ]),
                html.Div([
                    html.H5(style={'textAlign':'center'}, children='Parameter distribution'),
                    wcc.Graph(id=self.histogram_id)
                ])

            ])

    def set_callbacks(self, app):
        @app.callback([
            Output(self.histogram_id, 'figure'),
            Output(self.table_id, 'data')],
            [Input(self.pcol_id, 'value')])
        def _set_parameter(column):
            param = self.parameters[[column, 'REAL', 'ENSEMBLE']]
            plot = px.histogram(param, x=column, y='REAL', color="ENSEMBLE",
                                barmode='overlay', nbins=10, marginal='rug')

            stat = [{
                    'Ensemble': ensemble,
                    'Min': f'{df[column].min():.2f}',
                    'Mean': f'{df[column].mean():.2f}',
                    'Max': f'{df[column].max():.2f}',
                    'Stddev': f'{df[column].std():.2f}'
                    } for ensemble, df in param.groupby('ENSEMBLE')]
            return plot, stat

    def add_webvizstore(self):
        return [(load_parameters, [{
            'ensemble_paths': self.ensembles,
            'ensemble_set_name': 'EnsembleSet'}])]
