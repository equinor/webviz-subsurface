from pathlib import Path

import pytest
import xtgeo

from webviz_subsurface._datainput.fmu_input import find_surfaces
from webviz_subsurface._models.surface_set_model import SurfaceSetModel


@pytest.mark.usefixtures("app")
def test_surface_set_model(testdata_folder):
    ensemble_paths = {
        "iter-0": str(
            Path(testdata_folder / "01_drogon_ahm" / "realization-*" / "iter-0")
        )
    }

    surface_table = find_surfaces(ensemble_paths)
    surface_table = surface_table.drop("ENSEMBLE", axis=1)

    smodel = SurfaceSetModel(surface_table)
    assert set(smodel.attributes) == set(
        [
            "ds_extract_postprocess",
            "amplitude_mean",
            "ds_extract_geogrid",
            "amplitude_rms",
            "oilthickness",
        ]
    )
    assert set(smodel.names_in_attribute("ds_extract_postprocess")) == set(
        ["basevolantis", "topvolantis", "toptherys", "topvolon"]
    )
    real_surf = smodel.get_realization_surface(
        attribute="ds_extract_postprocess", name="topvolon", realization=0
    )
    assert isinstance(real_surf, xtgeo.RegularSurface)
    assert real_surf.values.mean() == pytest.approx(1735.42, 0.00001)
    stat_surf = smodel.calculate_statistical_surface(
        attribute="ds_extract_postprocess", name="topvolon"
    )
    assert isinstance(stat_surf, xtgeo.RegularSurface)
    assert stat_surf.values.mean() == pytest.approx(1741.04, 0.00001)

    stat_surf = smodel.calculate_statistical_surface(
        attribute="ds_extract_postprocess", name="topvolon", realizations=[0, 1]
    )
    assert stat_surf.values.mean() == pytest.approx(1741.04, 0.00001)
