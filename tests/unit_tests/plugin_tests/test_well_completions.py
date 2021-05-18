from webviz_subsurface.plugins._well_completions import extract_stratigraphy


def test_extract_stratigraphy():

    layer_zone_mapping = {1: "ZoneA.1", 2: "ZoneA.2", 3: "ZoneB.1", 4: "ZoneD"}
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
        }
    ]
    zone_color_mapping = {"ZoneA": "#111111", "ZoneA.1": "#222222"}
    theme_colors = ["#FFFFFF"]

    result = extract_stratigraphy(
        layer_zone_mapping, stratigraphy, zone_color_mapping, theme_colors
    )
    # Merging of stratigraphy and layer_zone_mapping logic
    top_level_zones = [zonedict["name"] for zonedict in result]
    zoneA_subzones = [zonedict["name"] for zonedict in result[0]["subzones"]] # pylint: disable=invalid-name
    assert result[0]["name"] == "ZoneA"
    assert result[1]["name"] == "ZoneB"
    assert (
        "ZoneC" not in top_level_zones
    )  # ZoneC is not in the layer_zone_mapping and should be removed
    assert (
        result[2]["name"] == "ZoneD"
    )  # ZoneD is in the layer_zone_mapping and not in the stratigrapy. Should be added to the end
    assert (
        "ZoneA.3" not in zoneA_subzones
    )  # ZoneA.3 is not in the layer_zone_mapping and should be removed
    assert (
        "subzones" not in result[1]["subzones"][0]
    )  # The subzones of ZoneB.1 should be removed since they are not in the layer_zone_mapping

    # Colors logic
    assert result[0]["color"] == "#000000"  # colors in stratigraphy have priority
    assert (
        "color" not in result[1]
    )  # no color specified for ZoneA in the stratigraphy or zone_color_map
    assert (
        result[0]["subzones"][0]["color"] == "#222222"
    )  # Zone A.1 should get it's color from the zone_color_map
    assert (
        result[1]["subzones"][0]["color"] == "#FFFFFF"
    )  # Zone B.1 is a leaf and should have theme color
    assert (
        result[2]["color"] == "#FFFFFF"
    )  # Zone D is a leaf and should have theme color
