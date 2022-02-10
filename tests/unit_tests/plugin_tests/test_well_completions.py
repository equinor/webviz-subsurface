import numpy as np
import pandas as pd
import pytest
from pandas._testing import assert_frame_equal

from webviz_subsurface._datainput.well_completions import remove_invalid_colors
from webviz_subsurface.plugins._well_completions._business_logic import (
    extract_stratigraphy,
    merge_compdat_and_connstatus,
)


def test_remove_invalid_colors():
    """Tests that colors that are not 6 digit hexadecimal are removed from the lyr
    parse zone list
    """
    zonelist = [
        {"name": "ZoneA", "color": "#FFFFFF"},
        {"name": "ZoneB", "color": "#FFF"},
    ]
    assert remove_invalid_colors(zonelist) == [
        {"name": "ZoneA", "color": "#FFFFFF"},
        {
            "name": "ZoneB",
        },
    ]


def test_extract_stratigraphy():
    """Checks that the merging of the layer_zone_mapping and the stratigraphy is
    correct and that the colors are added following the correct prioritization
    rules
    """
    zone_names = ["ZoneA.1", "ZoneA.2", "ZoneB.1"]
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
        zone_names, stratigraphy, zone_color_mapping, theme_colors
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


def test_extract_stratigraphy_errors():
    """Checks that a ValueError is raised when a Zone is in the layer_zone_mapping, but
    not in the stratigraphy.
    """
    layer_zone_mapping = {1: "ZoneA", 2: "ZoneB", 3: "ZoneD"}
    stratigraphy = [
        {
            "name": "ZoneA",
        },
        {
            "name": "ZoneB",
        },
    ]
    with pytest.raises(ValueError):
        extract_stratigraphy(layer_zone_mapping, stratigraphy, {}, [])


def test_merge_compdat_and_connstatus():
    """Tests the functionality of the merge_compdat_and_connstatus function.

    The following functionality is covered:
    * The two first rows of df_compdat is replaced with the two first from
    df_connstatus, except for the KH (which is only available in df_compdat).
    KH is taken from the first of the two compdat rows
    * The A2 well is not available in df_connstatus and will be taken as is
    from df_compdat
    * the fourth row in df_compdat (WELL: A1, REAL:1) is ignored because A1 is
    in df_connstatus, but not REAL 1. We don't mix compdat and connstatus data
    for the same well
    * The fourth row in df_compdat has KH=Nan. This will be 0 in the output
    """
    df_compdat = pd.DataFrame(
        data={
            "DATE": [
                "2021-01-01",
                "2021-05-01",
                "2021-01-01",
                "2021-01-01",
                "2022-01-01",
            ],
            "REAL": [0, 0, 0, 1, 0],
            "WELL": ["A1", "A1", "A2", "A1", "A3"],
            "I": [1, 1, 1, 1, 1],
            "J": [1, 1, 1, 1, 1],
            "K1": [1, 1, 1, 1, 1],
            "OP/SH": ["SHUT", "OPEN", "OPEN", "OPEN", "OPEN"],
            "KH": [100, 1000, 10, 100, np.nan],
        }
    )
    df_connstatus = pd.DataFrame(
        data={
            "DATE": ["2021-03-01", "2021-08-01", "2021-01-01"],
            "REAL": [0, 0, 0],
            "WELL": ["A1", "A1", "A3"],
            "I": [1, 1, 1],
            "J": [1, 1, 1],
            "K1": [1, 1, 1],
            "OP/SH": ["OPEN", "SHUT", "OPEN"],
        }
    )
    df_output = pd.DataFrame(
        data={
            "DATE": ["2021-03-01", "2021-08-01", "2021-01-01", "2021-01-01"],
            "REAL": [0, 0, 0, 0],
            "WELL": ["A1", "A1", "A3", "A2"],
            "I": [1, 1, 1, 1],
            "J": [1, 1, 1, 1],
            "K1": [1, 1, 1, 1],
            "OP/SH": ["OPEN", "SHUT", "OPEN", "OPEN"],
            "KH": [100.0, 100.0, 0.0, 10.0],
        }
    )
    df_result = merge_compdat_and_connstatus(df_compdat, df_connstatus)
    assert_frame_equal(
        df_result, df_output, check_like=True
    )  # Ignore order of rows and columns
