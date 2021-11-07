import datetime

import pandas as pd
from pandas._testing import assert_frame_equal
import pytest

from webviz_subsurface.plugins._group_tree.group_tree_data import add_nodetype_for_ens

ADD_NODETYPE_CASES = [
    # Leaf nodes that are not wells:
    # NODE1 has summary data>0 and will be classified as prod and inj
    # NODE2 has summary data==0 and will be classified as other
    # NODE3 has no summary data and will be classified as other
    pytest.param(
        pd.DataFrame(
            columns=["DATE", "CHILD", "KEYWORD", "PARENT"],
            data=[
                ["2000-01-01", "FIELD", "GRUPTREE", None],
                ["2000-01-01", "NODE1", "GRUPTREE", "FIELD"],
                ["2000-01-01", "NODE2", "GRUPTREE", "FIELD"],
                ["2000-01-01", "NODE3", "GRUPTREE", "FIELD"],
            ],
        ),
        pd.DataFrame(
            columns=["DATE", "GGPR:NODE1", "GGIR:NODE1", "GGPR:NODE2", "GGIR:NODE2"],
            data=[
                [datetime.date(2000, 1, 1), 1, 1, 0, 0],
            ],
        ),
        pd.DataFrame(
            columns=[
                "DATE",
                "CHILD",
                "KEYWORD",
                "PARENT",
                "IS_PROD",
                "IS_INJ",
                "IS_OTHER",
            ],
            data=[
                ["2000-01-01", "FIELD", "GRUPTREE", None, True, True, True],
                ["2000-01-01", "NODE1", "GRUPTREE", "FIELD", True, True, False],
                ["2000-01-01", "NODE2", "GRUPTREE", "FIELD", False, False, True],
                ["2000-01-01", "NODE3", "GRUPTREE", "FIELD", False, False, True],
            ],
        ),
        id="simple-case-without-wells",
    ),
]


@pytest.mark.parametrize("gruptree, smry, expected", ADD_NODETYPE_CASES)
def test_add_nodetype(gruptree, smry, expected):
    """Test functionality of the add_nodetype_for_ens function"""
    columns_to_check = [
        "DATE",
        "CHILD",
        "KEYWORD",
        "PARENT",
        "IS_PROD",
        "IS_INJ",
        "IS_OTHER",
    ]
    output = add_nodetype_for_ens(gruptree, smry)
    print("output")
    print(output)

    pd.testing.assert_frame_equal(output[columns_to_check], expected[columns_to_check])
