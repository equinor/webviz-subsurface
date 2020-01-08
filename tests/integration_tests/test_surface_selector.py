import json
import pandas as pd
import dash
from dash.dependencies import Input, Output
import dash_html_components as html
from webviz_subsurface._private_plugins.surface_selector import SurfaceSelector


surface_context = {
    "oilthickness": {
        "names": ["lowerreek", "upperreek", "all", "midreek"],
        "dates": [
            "20030101_20010601",
            "20010601_20000101",
            "20010601",
            "20000101",
            "20030101",
            "20030101_20000101",
            "20010601_20010604",
        ],
    },
    "ds_extracted_horizons": {
        "names": ["toplowerreek", "topmidreek", "topupperreek", "baselowerreek"],
        "dates": [None],
    },
}

return_value = {
    "attribute": "oilthickness",
    "name": "lowerreek",
    "date": "20030101_20010601",
    "ensemble": "iter-0",
    "aggregation": "mean",
    "realization": [0, 1, 2],
    "sensname": None,
    "senscase": None,
    "all_senscases": [],
}


def test_surface_selector(dash_duo):

    app = dash.Dash(__name__)
    app.config.suppress_callback_exceptions = True
    realizations = pd.read_csv("tests/data/realizations.csv")
    s = SurfaceSelector(app, surface_context, realizations)

    app.layout = html.Div(children=[s.layout, html.Pre(id="pre", children="ok")])

    @app.callback(Output("pre", "children"), [Input(s.storage_id, "children")])
    def _test(data):
        return json.dumps(json.loads(data))

    dash_duo.start_server(app)

    dash_duo.wait_for_contains_text("#pre", json.dumps(return_value), timeout=4)
