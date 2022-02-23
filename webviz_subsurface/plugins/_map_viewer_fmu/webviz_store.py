from typing import Callable, Dict, List, Tuple

from webviz_subsurface.plugins._map_viewer_fmu.providers.ensemble_surface_provider import (
    scrape_scratch_disk_for_surfaces,
)

from .providers.ensemble_surface_provider import SurfaceMode, EnsembleSurfaceProvider
from .types import SurfaceContext

# def get_surface_contexts(
#     ensemble_surface_providers: List[EnsembleSurfaceProvider],
# ) -> List[SurfaceContext]:
#     for ens, surface_set in ensemble_surface_providers.items():
#         for attr in surface_set.attributes:
#             pass


def webviz_store_functions(
    ensemble_surface_providers: Dict[str, EnsembleSurfaceProvider],
    ensemble_paths: Dict[str, str],
) -> List[Tuple[Callable, list]]:
    store_functions: List[Tuple[Callable, list]] = [
        (
            scrape_scratch_disk_for_surfaces,
            [
                {
                    "ensemble_paths": ensemble_paths,
                    "suffix": "*.gri",
                    "delimiter": "--",
                }
            ],
        )
    ]
    for surf_set in ensemble_surface_providers.values():
        store_functions.append(surf_set.webviz_store_realization_surfaces())
        for statistic in [
            SurfaceMode.MEAN,
            SurfaceMode.STDDEV,
            SurfaceMode.MINIMUM,
            SurfaceMode.MAXIMUM,
        ]:
            store_functions.append(
                surf_set.webviz_store_statistical_calculation(statistic)
            )

    return store_functions
