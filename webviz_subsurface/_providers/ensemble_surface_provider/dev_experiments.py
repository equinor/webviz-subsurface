import logging
from pathlib import Path

import flask_caching

from ._provider_impl_sumo import ProviderImplSumo
from .ensemble_surface_provider import (
    EnsembleSurfaceProvider,
    ObservedSurfaceAddress,
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    SurfaceStatistic,
)
from .ensemble_surface_provider_factory import EnsembleSurfaceProviderFactory


def main() -> None:
    print()
    print("## Running EnsembleSurfaceProvider experiments")
    print("## =================================================")

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)-3s [%(name)s]: %(message)s",
    )
    logging.getLogger("webviz_subsurface").setLevel(level=logging.DEBUG)

    root_storage_dir = Path("/home/sigurdp/buf/webviz_storage_dir")
    root_cache_dir = Path("/home/sigurdp/buf/webviz_cache_dir")

    # fmt:off
    # ensemble_path = "../webviz-subsurface-testdata/01_drogon_ahm/realization-*/iter-0"
    ensemble_path = "../hk-webviz-subsurface-testdata/01_drogon_ahm/realization-*/iter-0"
    # fmt:on

    # WEBVIZ_FACTORY_REGISTRY.initialize(
    #     WebvizInstanceInfo(WebvizRunMode.NON_PORTABLE, root_storage_dir), None
    # )
    # factory = EnsembleSurfaceProviderFactory.instance()

    factory = EnsembleSurfaceProviderFactory(
        root_storage_folder=root_storage_dir,
        root_cache_folder=root_cache_dir,
        allow_storage_writes=True,
        avoid_copying_surfaces=False,
    )

    # provider: EnsembleSurfaceProvider = factory.create_from_ensemble_surface_files(
    #     ensemble_path
    # )

    cache = flask_caching.backends.FileSystemCache(root_cache_dir)
    provider: EnsembleSurfaceProvider = ProviderImplSumo(
        cache_dir=root_cache_dir,
        cache=cache,
        sumo_id_of_case="9f184b7b-9382-6b3d-164a-2a704ccb7dfd",
        iteration_id="0",
        use_access_token=False,
        access_token=None,
    )

    all_attributes = provider.attributes()
    print()
    print("all_attributes:")
    print("------------------------")
    print(*all_attributes, sep="\n")

    print()
    print("attributes for names:")
    print("------------------------")
    for attr in all_attributes:
        print(f"attr={attr}:")
        print(f"  surf_names={provider.surface_names_for_attribute(attr)}")
        print(f"  surf_dates={provider.surface_dates_for_attribute(attr)}")

    print()
    all_realizations = provider.realizations()
    print(f"all_realizations={all_realizations}")

    #########################
    if provider.__class__.__name__ == "ProviderImplFile":
        surf = provider.get_surface(
            SimulatedSurfaceAddress(
                attribute="oilthickness",
                name="therys",
                datestr="20200701_20180101",
                realization=1,
            )
        )
        print(surf)

        surf = provider.get_surface(
            ObservedSurfaceAddress(
                attribute="amplitude_mean",
                name="basevolantis",
                datestr="20180701_20180101",
            )
        )
        print(surf)

        # surf = provider.get_surface(
        #     StatisticalSurfaceAddress(
        #         attribute="amplitude_mean",
        #         name="basevolantis",
        #         datestr="20180701_20180101",
        #         statistic=SurfaceStatistic.P10,
        #         realizations=[0, 1],
        #     )
        # )
        # print(surf)

        # surf = provider.get_surface(
        #     StatisticalSurfaceAddress(
        #         attribute="amplitude_mean",
        #         name="basevolantis",
        #         datestr="20180701_20180101",
        #         statistic=SurfaceStatistic.P10,
        #         realizations=all_realizations,
        #     )
        # )
        # print(surf)

        surf = provider.get_surface(
            StatisticalSurfaceAddress(
                attribute="ds_extract_postprocess-refined8",
                name="topvolantis",
                datestr=None,
                statistic=SurfaceStatistic.P10,
                realizations=all_realizations,
            )
        )
        print(surf)

    #########################
    if provider.__class__.__name__ == "ProviderImplSumo":
        surf = provider.get_surface(
            SimulatedSurfaceAddress(
                attribute="ds_extract_geogrid",
                name="Therys Fm. Top",
                datestr=None,
                realization=1,
            )
        )
        print(surf)


# Running:
#   python -m webviz_subsurface._providers.ensemble_surface_provider.dev_experiments
# -------------------------------------------------------------------------
if __name__ == "__main__":
    main()
