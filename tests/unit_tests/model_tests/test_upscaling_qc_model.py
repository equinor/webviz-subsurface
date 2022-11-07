from pathlib import Path

import pytest

from pandas.api.types import CategoricalDtype
from webviz_subsurface.plugins._upscaling_qc.models.upscaling_qc_model import (
    UpscalingQCModel,
)


@pytest.fixture
def qcm_model() -> Path:
    model_folder = Path("../upscaling_qc")
    yield UpscalingQCModel(model_folder=model_folder)


def test_upscaling_qc_model_init(qcm_model):
    assert set(qcm_model.selectors) == set(["ZONE", "FACIES"])
    assert set(qcm_model.properties) == set(["PHIT", "KLOGH"])
    assert set(qcm_model.get_unique_selector_values("ZONE")) == set(
        ["Valysar", "Volon", "Therys"]
    )
    assert all(
        isinstance(qcm_model._grid_df[col].dtype, CategoricalDtype)
        for col in qcm_model.selectors
    )


def test_upscaling_qc_model_dataframe(qcm_model):
    df = qcm_model.get_dataframe(
        selectors=["ZONE"], selector_values=[["Volon"]], responses=["PHIT"]
    )

    assert (set(df.columns)) == set(["ZONE", "PHIT"])
    assert df.shape[0] == 204017
    assert df["PHIT"].mean() == pytest.approx(0.1794, abs=0.0001)


def test_upscaling_qc_model_reduce_points(qcm_model):
    df = qcm_model.get_dataframe(
        selectors=["ZONE"],
        selector_values=[["Volon"]],
        responses=["PHIT"],
        max_points=100000,
    )
    assert df.shape[0] == 103917
    assert df["PHIT"].mean() == pytest.approx(0.18, abs=0.01)
