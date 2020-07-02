import dash_html_components as html
import dash_core_components as dcc
import plotly.graph_objects as go
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC

""" Example output from the calculations of p-values in dictionary form """
p_values = {
    'FWL' : 0.032,
    'INTERPOLATE_WO' : 0.867,
    'MULTIFLT_F3' : 0.231,
    'INTERPOLATE_GO' : 0.047,
    'MULTIFLT_F4' : 0.567
}

class PValues(WebvizPluginABC):
    def __init__(self, app):
        super().__init__()

    @property
    def layout(self):
        return wcc.FlexBox(
            children=[
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
    values = list(p_sorted.values())
    
    """ Making the bar chart plot """
    fig = go.Figure([
        go.Bar(
            x=parameters,
            y=values,
            marker_color=["#FF1243" if val<0.05 else "slategray" for val in values])])
    
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
        y0=0.05, 
        y1=0.05,
        x0=-0.5,
        x1=len(values)-0.5,
        xref='x',
        line=dict(
            color='#222A2A',
            width=2
        )
    )
    return fig