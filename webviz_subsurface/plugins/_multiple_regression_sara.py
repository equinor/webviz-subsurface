import dash_html_components as html
import dash_core_components as dcc

import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff

import webviz_core_components as wcc
from webviz_config import WebvizPluginABC

import numpy as np
import math

"""Example output"""
coefs = {
    'FWL' : 600,
    'INTERPOLATE_WO' : 23,
    'MULTIFLT_F3' : -30,
    'INTERPOLATE_GO' : 17,
    'MULTIFLT_F4' : -40
}


class PlotCoefficientsSara(WebvizPluginABC):

    def __init__(self, app):
        super().__init__()

        #self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        #self.set_callbacks(app)

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
                        id='coefficient_plot03',
                        figure=make_arrow_plot(self, coefs)
                    )
                )
            ]
        )

def make_arrow_plot(self, coefs):
    """Sorting dictionary in descending order. 
    Saving parameters and values of coefficients in lists.
    Saving plot-function to variable fig."""
    coefs = dict(sorted(coefs.items(), key=lambda x: x[1], reverse=True))
    params = list(coefs.keys())
    vals = list(coefs.values())
    sgn = signs(self, vals)
    colors = color_array(self, vals, params, sgn)

    fig = arrow_plot(self, coefs, vals, params, sgn, colors)

    return fig

def signs(self, vals): #vals a list
    """Saving signs of coefficients to array sgn"""
    sgn = np.zeros(len(vals))
    for i, v in enumerate(vals):
        sgn[i] = np.sign(v)
    return sgn

def arrow_plot(self, coefs, vals, params, sgn, colors): #vals, params lists
    steps = 2/(len(coefs)-1)
    points = len(coefs)

    x = np.linspace(0, 2, points)
    y = np.zeros(len(x))

    global fig
    fig = px.scatter(x,y, opacity=0)
    fig.update_xaxes(
        ticktext=[p for p in params],
        tickvals=[steps*i for i in range(points)],
    )
    fig.update_yaxes(showticklabels=False)
    fig.update_layout(
        yaxis=dict(range=[-0.125, 0.125], title=f'', showgrid=False), 
        xaxis=dict(range=[-0.2, x[-1]+0.2], title='Parameters', showgrid=False, zeroline=False),
        title='Sign of coefficient of the key parameter combination',
        autosize=False,
        width=800,
        height=500,
        plot_bgcolor='#FFFFFF',
    )
    fig.add_annotation(
        x=-0.18,
        y=0.025,
        text="Great positive",
        showarrow=False
    )
    fig.add_annotation(
        x=-0.18,
        y=0.015,
        text="coefficient",
        showarrow=False
    )
    fig.add_annotation(
        x=x[-1]+0.18,
        y=0.025,
        text="Great negative",
        showarrow=False
    )
    fig.add_annotation(
        x=x[-1]+0.18,
        y=0.015,
        text="coefficient",
        showarrow=False
    )
    """Adding zero-line along y-axis"""
    fig.add_shape(
        # Line Horizontal
            type="line",
            x0=-0.18,
            y0=0,
            x1=x[-1]+0.18,
            y1=0,
            line=dict(
                color='#222A2A',
                width=0.75,
            ),
    )
    fig.add_shape(
        type="path",
        path=" M -0.2 0 L -0.18 -0.005 L -0.18 0.005 Z",
        #fillcolor="LightPink",
        line_color="#222A2A",
        line_width=0.75,
    )
    fig.add_shape(
        type="path",
        path=f" M {x[-1]+0.2} 0 L {x[-1]+0.18} -0.005 L {x[-1]+0.18} 0.005 Z",
        #fillcolor="LightPink",
        line_color="#222A2A",
        line_width=0.75,
    )

    """Adding arrows to figure"""
    for i, s in enumerate(sgn):
        if s == 1:
            fig.add_shape(
                type="path",
                path=f" M {x[i]} 0 L {x[i]} 0.1 L {x[i]-0.05} 0.075 L {x[i]} 0.1 L {x[i]+0.05} 0.075",
                line_color=colors[i],     
            )
        else:
            fig.add_shape(
                type="path",
                path=f" M {x[i]} 0 L {x[i]} -0.1 L {x[i]-0.05} -0.075 L {x[i]} -0.1 L {x[i]+0.05} -0.075",
                line_color=colors[i],
            )

    return fig

def color_array(self, vals, params, sgn):
    """Function to scale coefficients to a green-red color range"""
    max_val = vals[0]
    min_val = vals[-1]
    r = 250
    g = 250
    const=222
    b=0

    color_arr = ['rgba(255, 255, 255, 1)']*len(params)

    global k
    k=0
    for s, v in zip(sgn, vals):
        if s == 1:
            scaled_val_max = v/max_val
            #print(round(255-r*scaled_val_max, 3), round(g*scaled_val_max,3), sep='\t')
            color_arr[k] = f'rgba({int(r-r*scaled_val_max)}, {const}, {b}, 1)'
        else:
            scaled_val_min = v/min_val
            #print(round(255-r*scaled_val_min, 3), round(g*scaled_val_min,3), sep='\t')
            color_arr[k] = f'rgba({int(const)}, {int(g-g*scaled_val_min)}, {b}, 1)'
        k += 1
    
    return color_arr