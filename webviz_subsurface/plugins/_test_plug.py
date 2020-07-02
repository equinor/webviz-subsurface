from uuid import uuid4

import dash_html_components as html
from dash.dependencies import Input, Output
from webviz_config import WebvizPluginABC
from numpy.random import rand
from pathlib import Path

class ExamplePlugin(WebvizPluginABC):

    def __init__(self, app):
        super().__init__()

    @property
    def layout(self):
        return wcc.FlexBox(
            children=[
                html.Div([
                         html.H2('Multiple regression of parameters and responses')
                        ]),
                html.Div(
                    style={'flex': 2},
                    children=wcc.Graph(
                        id='p_values_plot',
                        figure=make_p_values_plot(self, p_values)
                    )
                )
            ])

    def make_p_values_plot(self, p_values):
        
        """ Sorting the dictionary in ascending order and making lists for parameters and p-values """
        p_sorted = dict(sorted(p_values.items(), key=lambda x: x[1]))
        parameters = list(p_sorted.keys())
        calc_p_values = list(p_sorted.values())
        
        """ Making an array for the corresponding colors """
        col_values = [int(i*100) for i in calc_p_values]
        colors = ['#FF1243']*len(parameters) # Red Equinor color
        
        for i, v in enumerate(col_values):
            if v <= 5:
                colors[i] = '#5AC864' # Green color

        """ Making the bar chart plot """
        fig = go.Figure([go.Bar(x=parameters, y=calc_p_values, marker_color=colors)])
        fig.update_layout(
            yaxis=dict(range=[0,1], title=f'p-values'), 
            xaxis=dict(title='Parameters'),
            title='P-values for the key parameter combination',
            autosize=False,
            width=800,
            height=600,
            )

        """ Adding a line at p = 0.05 """
        fig.add_shape(
            type='line', 
            y0=0.05, y1=0.05, x0=-0.5, x1=len(p_values.keys())-0.5, xref='x',
            line=dict(
                color='#222A2A',
                width=2
            )
        )
        return fig


def load_data(parameter_path: Path = None,
              timeseries_path: Path = None,
              inplace_path: Path = None
              ):
    para_df = pd.read_parquet(parameter_path)
    inpl_df = pd.read_parquet(inplace_path)
    ts_df = pd.read_parquet(timeseries_path)

    ts_df.columns = [col.replace(":", "_") for col in ts_df.columns]
    inpl_df.columns = [col.replace(":", "_") for col in inpl_df.columns]
    para_df.columns = [col.replace(":", "_") for col in para_df.columns]

    return (para_df, inpl_df, ts_df)