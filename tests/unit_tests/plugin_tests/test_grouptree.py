import datetime

import pandas as pd
import pytest

from webviz_subsurface.plugins._group_tree.group_tree_data import add_nodetype_for_ens

ADD_NODETYPE_CASES = [
    # Group leaf nodes:
    # NODE1 has summary data>0 and will be classified as prod and inj
    # NODE2 has summary data==0 and will be classified as other
    # NODE3 has no summary data and will be classified as other
    # FIELD and TMPL are classified as all three types
    pytest.param(
        pd.DataFrame(
            columns=["DATE", "CHILD", "KEYWORD", "PARENT"],
            data=[
                ["2000-01-01", "FIELD", "GRUPTREE", None],
                ["2000-01-01", "TMPL", "GRUPTREE", "FIELD"],
                ["2000-01-01", "NODE1", "GRUPTREE", "TMPL"],
                ["2000-01-01", "NODE2", "GRUPTREE", "TMPL"],
                ["2000-01-01", "NODE3", "GRUPTREE", "TMPL"],
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
                ["2000-01-01", "TMPL", "GRUPTREE", "FIELD", True, True, True],
                ["2000-01-01", "NODE1", "GRUPTREE", "TMPL", True, True, False],
                ["2000-01-01", "NODE2", "GRUPTREE", "TMPL", False, False, True],
                ["2000-01-01", "NODE3", "GRUPTREE", "TMPL", False, False, True],
            ],
        ),
        id="add-nodetype-for-group-leaf-nodes",
    ),
    # Well leaf nodes:
    # WELL1 has WSTAT==1 and will be classified as producer
    # WELL2 has WSTAT==2 and will be classified as injector
    # WELL3 has first WSTAT==1 and then WSTAT==2 and will be classified as both
    # WELL4 has WSTAT==0 and will be classified as other
    # TMPL_A is classified as prod and inj
    # TMPL_B is classified as other
    pytest.param(
        pd.DataFrame(
            columns=["DATE", "CHILD", "KEYWORD", "PARENT"],
            data=[
                ["2000-01-01", "FIELD", "GRUPTREE", None],
                ["2000-01-01", "TMPL_A", "GRUPTREE", "FIELD"],
                ["2000-01-01", "TMPL_B", "GRUPTREE", "FIELD"],
                ["2000-01-01", "WELL1", "WELSPECS", "TMPL_A"],
                ["2000-01-01", "WELL2", "WELSPECS", "TMPL_A"],
                ["2000-01-01", "WELL3", "WELSPECS", "TMPL_A"],
                ["2000-01-01", "WELL4", "WELSPECS", "TMPL_B"],
            ],
        ),
        pd.DataFrame(
            columns=[
                "DATE",
                "WSTAT:WELL1",
                "WSTAT:WELL2",
                "WSTAT:WELL3",
                "WSTAT:WELL4",
            ],
            data=[
                [datetime.date(2000, 1, 1), 1, 2, 1, 0],
                [datetime.date(2000, 2, 1), 1, 2, 2, 0],
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
                ["2000-01-01", "TMPL_A", "GRUPTREE", "FIELD", True, True, False],
                ["2000-01-01", "TMPL_B", "GRUPTREE", "FIELD", False, False, True],
                ["2000-01-01", "WELL1", "WELSPECS", "TMPL_A", True, False, False],
                ["2000-01-01", "WELL2", "WELSPECS", "TMPL_A", False, True, False],
                ["2000-01-01", "WELL3", "WELSPECS", "TMPL_A", True, True, False],
                ["2000-01-01", "WELL4", "WELSPECS", "TMPL_B", False, False, True],
            ],
        ),
        id="add-nodetype-for-well-leaf-nodes",
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

    pd.testing.assert_frame_equal(output[columns_to_check], expected[columns_to_check])
