from pathlib import Path

import pytest
import xtgeo

from webviz_subsurface._models.surface_set_model import SurfaceSetModel
from webviz_subsurface._datainput.fmu_input import find_surfaces


@pytest.mark.usefixtures("app")
def test_surface_set_model(testdata_folder):
    ensemble_paths = {
        "iter-0": str(
            Path(testdata_folder / "reek_history_match" / "realization-*" / "iter-0")
        )
    }

    surface_table = find_surfaces(ensemble_paths)
    surface_table = surface_table.drop("ENSEMBLE", axis=1)

    smodel = SurfaceSetModel(surface_table)
    assert set(smodel.attributes) == set(
        [
            "average_pressure",
            "average_swat",
            "average_permz",
            "amplitude_max",
            "average_soil",
            "average_permx",
            "average_sgas",
            "amplitude_rms",
            "amplitude_min",
            "facies_fraction_channel",
            "perm_average",
            "oilthickness",
            "poro_average",
            "zonethickness_average",
            "timeshift",
            "ds_extracted_horizons",
            "facies_fraction_crevasse",
            "stoiip",
            "average_poro",
        ]
    )
    assert set(smodel.names_in_attribute("ds_extracted_horizons")) == set(
        ["topupperreek", "baselowerreek", "toplowerreek", "topmidreek"]
    )
    real_surf = smodel.get_realization_surface(
        attribute="ds_extracted_horizons", name="topupperreek", realization=0
    )
    assert isinstance(real_surf, xtgeo.RegularSurface)
    assert real_surf.values.mean() == pytest.approx(1706.35, 0.00001)
    stat_surf = smodel.calculate_statistical_surface(
        attribute="ds_extracted_horizons", name="topupperreek"
    )
    assert isinstance(stat_surf, xtgeo.RegularSurface)
    assert stat_surf.values.mean() == pytest.approx(1706.42, 0.00001)

    stat_surf = smodel.calculate_statistical_surface(
        attribute="ds_extracted_horizons", name="topupperreek", realizations=[2, 4, 5]
    )
    assert stat_surf.values.mean() == pytest.approx(1707.07, 0.00001)
