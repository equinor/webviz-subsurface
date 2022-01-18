import datetime
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import pytest
from _pytest.fixtures import SubRequest

from webviz_subsurface._providers import EnsembleSummaryProvider
from webviz_subsurface._providers.ensemble_summary_provider._provider_impl_arrow_presampled import (
    ProviderImplArrowPresampled,
)
from webviz_subsurface.plugins._group_tree._ensemble_group_tree_data import add_nodetype

ADD_NODETYPE_CASES = [
    # Group leaf nodes:
    # NODE1 has summary data>0 and will be classified as prod and inj
    # NODE2 has summary data==0 and will be classified as other
    # NODE3 has no summary data and will be classified as other
    # FIELD and TMPL are classified as all three types
    (
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
            columns=[
                "DATE",
                "REAL",
                "GGPR:NODE1",
                "GGIR:NODE1",
                "GGPR:NODE2",
                "GGIR:NODE2",
            ],
            data=[
                [datetime.date(2000, 1, 1), 0, 1, 1, 0, 0],
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
    ),
    # Well leaf nodes:
    # WELL1 has WSTAT==1 and will be classified as producer
    # WELL2 has WSTAT==2 and will be classified as injector
    # WELL3 has first WSTAT==1 and then WSTAT==2 and will be classified as both
    # WELL4 has WSTAT==0 and will be classified as other
    # TMPL_A is classified as prod and inj
    # TMPL_B is classified as other
    (
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
                "REAL",
                "WSTAT:WELL1",
                "WSTAT:WELL2",
                "WSTAT:WELL3",
                "WSTAT:WELL4",
            ],
            data=[
                [datetime.date(2000, 1, 1), 0, 1, 2, 1, 0],
                [datetime.date(2000, 2, 1), 0, 1, 2, 2, 0],
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
    ),
]


@pytest.fixture(
    name="testdata",
    params=ADD_NODETYPE_CASES,
)
def fixture_provider(
    request: SubRequest, tmp_path: Path
) -> Tuple[pd.DataFrame, EnsembleSummaryProvider, pd.DataFrame]:

    input_py = request.param
    storage_dir = tmp_path
    gruptree_df = input_py[0]
    smry_df = input_py[1]
    expected_df = input_py[2]

    ProviderImplArrowPresampled.write_backing_store_from_ensemble_dataframe(
        storage_dir, "dummy_key", smry_df
    )
    new_provider = ProviderImplArrowPresampled.from_backing_store(
        storage_dir, "dummy_key"
    )

    if not new_provider:
        raise ValueError("Failed to create EnsembleSummaryProvider")

    return gruptree_df, new_provider, expected_df


def test_add_nodetype(
    testdata: Tuple[pd.DataFrame, EnsembleSummaryProvider, pd.DataFrame]
) -> None:
    """Test functionality for the add_nodetype function"""
    gruptree_df = testdata[0]
    provider = testdata[1]
    expected_df = testdata[2]

    columns_to_check = [
        "DATE",
        "CHILD",
        "KEYWORD",
        "PARENT",
        "IS_PROD",
        "IS_INJ",
        "IS_OTHER",
    ]

    wells: List[str] = gruptree_df[gruptree_df["KEYWORD"] == "WELSPECS"][
        "CHILD"
    ].unique()

    output = add_nodetype(gruptree_df, provider, wells)
    pd.testing.assert_frame_equal(
        output[columns_to_check], expected_df[columns_to_check]
    )
