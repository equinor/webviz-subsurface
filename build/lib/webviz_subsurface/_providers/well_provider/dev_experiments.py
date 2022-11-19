# pylint: skip-file
import logging
import time
from pathlib import Path

from .well_provider import WellProvider
from .well_provider_factory import WellProviderFactory


def main() -> None:
    print()
    print("## Running WellProvider experiments")
    print("## =================================================")

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)-3s [%(name)s]: %(message)s",
    )
    logging.getLogger("webviz_subsurface").setLevel(level=logging.DEBUG)

    root_storage_dir = Path("/home/sigurdp/buf/webviz_storage_dir")

    well_folder = "../hk-webviz-subsurface-testdata/01_drogon_ahm/realization-0/iter-0/share/results/wells"
    well_suffix = ".rmswell"
    md_logname = None

    factory = WellProviderFactory(root_storage_dir, allow_storage_writes=True)

    provider: WellProvider = factory.create_from_well_files(
        well_folder=well_folder,
        well_suffix=well_suffix,
        md_logname=md_logname,
    )

    all_well_names = provider.well_names()
    print()
    print("all_well_names:")
    print("------------------------")
    print(*all_well_names, sep="\n")

    start_tim = time.perf_counter()

    for name in all_well_names:
        # w = provider.get_well_xtgeo_obj(name)
        wp = provider.get_well_path(name)

    elapsed_time_ms = int(1000 * (time.perf_counter() - start_tim))
    print(f"## get all wells took: {elapsed_time_ms}ms")

    well_name = "55_33-A-4"

    w = provider.get_well_xtgeo_obj(well_name)
    print(w.describe())
    print("w.mdlogname=", w.mdlogname)

    wp = provider.get_well_path(well_name)
    # print(wp)

    # comparewell = xtgeo.well_from_file(
    #     wfile=Path(well_folder) / "55_33-A-4.rmswell", mdlogname=md_logname
    # )
    # print(comparewell.describe())
    # print("comparewell.mdlogname=", comparewell.mdlogname)


# Running:
#   python -m webviz_subsurface._providers.well_provider.dev_experiments
# -------------------------------------------------------------------------
if __name__ == "__main__":
    main()
