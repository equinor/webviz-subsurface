from webviz_subsurface.plugins._map_viewer_fmu.color_tables import default_color_tables

# Source: https://waldyrious.net/viridis-palette-generator/ + matplotlib._cm_listed
CO2LEAKAGE_COLOR_TABLES = default_color_tables + [
    {
        "name": "Viridis",
        "discrete": False,
        "colors": [
            [0.0, 253, 231, 37],
            [0.25, 94, 201, 98],
            [0.50, 33, 145, 140],
            [0.75, 59, 82, 139],
            [1.0, 68, 1, 84],
        ],
    },
    {
        "name": "Inferno",
        "discrete": False,
        "colors": [
            [0.0, 252, 255, 164],
            [0.25, 249, 142, 9],
            [0.5, 188, 55, 84],
            [0.75, 87, 16, 110],
            [1.0, 0, 0, 4],
        ],
    },
    {
        "name": "Magma",
        "discrete": False,
        "colors": [
            [0.0, 252, 253, 191],
            [0.25, 252, 137, 97],
            [0.5, 183, 55, 121],
            [0.75, 81, 18, 124],
            [1.0, 0, 0, 4],
        ],
    },
    {
        "name": "Plasma",
        "discrete": False,
        "colors": [
            [0.0, 240, 249, 33],
            [0.25, 248, 149, 64],
            [0.5, 204, 71, 120],
            [0.75, 126, 3, 168],
            [1.0, 13, 8, 135],
        ],
    },
    {
        "name": "Cividis",
        "discrete": False,
        "colors": [
            [0.0, 0, 32, 77],
            [0.25, 64, 77, 107],
            [0.5, 124, 123, 120],
            [0.75, 188, 175, 111],
            [1.0, 255, 234, 70],
        ],
    },
]
