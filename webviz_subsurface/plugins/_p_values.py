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
        title='This is an example plot with example values, not finished',
        autosize=False,
        width=600,
        height=500,
        plot_bgcolor='#FFFFFF'
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