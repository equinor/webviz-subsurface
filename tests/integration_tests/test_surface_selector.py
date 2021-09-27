import json

import dash
import pandas as pd
from dash.dependencies import Input, Output

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
    "name": "lowerreek",
    "attribute": "oilthickness",
    "date": "20030101_20010601",
}


def test_surface_selector(dash_duo: dash.testing.composite.DashComposite) -> None:

    app = dash.Dash(__name__)
    app.config.suppress_callback_exceptions = True
    realizations = pd.read_csv("tests/data/realizations.csv")
    surface_selector = SurfaceSelector(app, surface_context, realizations)

    app.layout = dash.html.Div(
        children=[surface_selector.layout, dash.html.Pre(id="pre", children="ok")]
    )

    @app.callback(
        Output("pre", "children"), [Input(surface_selector.storage_id, "data")]
    )
    def _test(data: str) -> str:
        return json.dumps(json.loads(data))

    dash_duo.start_server(app)

    dash_duo.wait_for_contains_text("#pre", json.dumps(return_value), timeout=4)
