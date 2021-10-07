from typing import List, Tuple, Callable, Dict

from webviz_subsurface._datainput.fmu_input import find_surfaces

from .models import SurfaceSetModel
from .classes.surface_context import SurfaceContext
from .classes.surface_mode import SurfaceMode


# def get_surface_contexts(
#     surface_set_models: List[SurfaceSetModel],
# ) -> List[SurfaceContext]:
#     for ens, surface_set in surface_set_models.items():
#         for attr in surface_set.attributes:
#             pass


def webviz_store_functions(
    surface_set_models: List[SurfaceSetModel], ensemble_paths: Dict[str, str]
) -> List[Tuple[Callable, list]]:
    store_functions: List[Tuple[Callable, list]] = [
        (
            find_surfaces,
            [
                {
                    "ensemble_paths": ensemble_paths,
                    "suffix": "*.gri",
                    "delimiter": "--",
                }
            ],
        )
    ]
    for surf_set in surface_set_models.values():
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
