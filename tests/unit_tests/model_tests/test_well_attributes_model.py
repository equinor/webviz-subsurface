import io
import json

import numpy as np
import pandas as pd
import pytest

from webviz_subsurface._models.well_attributes_model import WellAttributesModel

LOAD_DATA_FUNCTION = (
    "webviz_subsurface._models.well_attributes_model.WellAttributesModel._load_data"
)


def test_simplest_possible_input(mocker):
    mocker.patch(
        LOAD_DATA_FUNCTION,
        lambda self: io.BytesIO(json.dumps({"version": "0.1", "wells": []}).encode()),
    )
    well_attr = WellAttributesModel("ens_name", "ens_path", "file_name")
    assert well_attr.data == {}


def test_not_implemented_version(mocker):
    mocker.patch(
        LOAD_DATA_FUNCTION,
        lambda self: io.BytesIO(json.dumps({"version": "0.2", "wells": []}).encode()),
    )
    with pytest.raises(NotImplementedError):
        WellAttributesModel("ens_name", "ens_path", "file_name")


def test_object_properties(mocker):
    mock_data = {
        "version": "0.1",
        "wells": [
            {
                "alias": {"eclipse": "OP_1"},
                "attributes": {
                    "attr1": "value1",
                    "attr2": "value2",
                },
                "name": "OP_1",
            },
            {
                "alias": {"eclipse": "OP_2"},
                "attributes": {
                    "attr1": "value1",
                },
                "name": "OP_2",
            },
        ],
    }
    mocker.patch(
        LOAD_DATA_FUNCTION,
        lambda self: io.BytesIO(json.dumps(mock_data).encode()),
    )
    well_attr = WellAttributesModel("ens_name", "ens_path", "file_name")

    # Test categories
    assert set(well_attr.categories) == {"attr1", "attr2"}

    # Test data
    assert well_attr.data == {
        "OP_1": {
            "attr1": "value1",
            "attr2": "value2",
        },
        "OP_2": {
            "attr1": "value1",
        },
    }

    # Test category_dict (This will replace nan with Undefined)
    assert well_attr.category_dict == {
        "attr1": ["value1"],
        "attr2": ["value2", "Undefined"],
    }

    # Test dataframe
    pd.testing.assert_frame_equal(
        well_attr.dataframe,
        pd.DataFrame(
            columns=["WELL", "attr1", "attr2"],
            data=[["OP_1", "value1", "value2"], ["OP_2", "value1", np.nan]],
        ),
    )

    # Test melted dataframe
    df_melted = well_attr.dataframe_melted
    assert df_melted.shape[0] == 4
    assert df_melted.shape[1] == 3
    assert set(df_melted["WELL"]) == {"OP_1", "OP_2"}
    assert set(df_melted["CATEGORY"]) == {"attr1", "attr2"}
    assert set(df_melted["VALUE"]) == {"value1", "value2", np.nan}

    # This is the expected dataframe, but I'm not able to test it with
    # assert_frame_equal because the row order of the melted dataframe is
    # randomly changing.
    #
    # exp_df_melted = pd.DataFrame(
    #     columns=["WELL", "CATEGORY", "VALUE"],
    #     data=[
    #         ["OP_1", "attr1", "value1"],
    #         ["OP_2", "attr1", "value1"],
    #         ["OP_1", "attr2", "value2"],
    #         ["OP_2", "attr2", np.nan],
    #     ],
    # )
    # pd.testing.assert_frame_equal(df, exp_df, check_like=True)
