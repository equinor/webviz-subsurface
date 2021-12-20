import webviz_core_components as wcc
import webviz_subsurface_components as wsc


def main_layout(get_uuid):
    return wcc.FlexBox(
        children=[
            wcc.Frame(
                style={"flex": 1, "height": "90vh"},
                children=[
                    wcc.Selectors(
                        label="Mode",
                        children=wcc.Dropdown(
                            id=get_uuid("mode"),
                            options=[
                                {"label": mode, "value": mode}
                                for mode in ["Realization", "Mean"]
                            ],
                            value="Realization",
                            clearable=False,
                        ),
                    ),
                ],
            ),
            wcc.Frame(
                style={"flex": 5},
                children=[
                    wsc.DeckGLMap(
                        id=get_uuid("map-component"),
                        bounds=[0, 0, 10, 10],
                        zoom=-4,
                        layers=[
                            {
                                "@@type": "Hillshading2DLayer",
                                "bounds": [0, 0, 10, 10],
                                "valueRange": [0, 1],
                                "image": "/surface.png",
                                "pickable": False,
                            },
                        ],
                    )
                ],
            ),
        ]
    )
