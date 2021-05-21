from webviz_subsurface.plugins._well_completions import extract_stratigraphy


def test_extract_stratigraphy():

    layer_zone_mapping = {1: "ZoneA.1", 2: "ZoneA.2", 3: "ZoneB.1"}
    stratigraphy = [
        {
            "name": "ZoneA",
            "color": "#000000",
            "subzones": [{"name": "ZoneA.1"}, {"name": "ZoneA.2"}, {"name": "ZoneA.3"}],
        },
        {
            "name": "ZoneB",
            "subzones": [{"name": "ZoneB.1", "subzones": [{"name": "ZoneB.1.1"}]}],
        },
        {
            "name": "ZoneC",
        },
    ]
    zone_color_mapping = {"ZoneA": "#111111", "ZoneA.1": "#222222"}
    theme_colors = ["#FFFFFF"]

    result = extract_stratigraphy(
        layer_zone_mapping, stratigraphy, zone_color_mapping, theme_colors
    )
    assert result == [
        {
            "name": "ZoneA",
            "color": "#000000",  # colors given in the stratigraphy has priority
            "subzones": [
                {
                    "name": "ZoneA.1",
                    "color": "#222222",  # color from zone_color_mapping
                },
                {"name": "ZoneA.2", "color": "#FFFFFF"}  # color from theme_colors
                # ZoneA.3 is not here because it is not in the layer_zone_mapping
            ],
        },
        {
            "name": "ZoneB",
            "color": "#808080",  # Since it's not a leaf, color is set to grey
            "subzones": [
                {
                    "name": "ZoneB.1",
                    "color": "#FFFFFF"  # color from theme_colors
                    # No subzones here because ZoneB.1.1 is not in the layer_zone_mapping
                }
            ],
        },
        # ZoneC is removed since it's not in the layer_zone_mapping
    ]
