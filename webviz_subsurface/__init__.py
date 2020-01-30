import glob
import pathlib
from pkg_resources import get_distribution, DistributionNotFound

import webviz_config


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


@webviz_config.SHARED_SETTINGS_SUBSCRIPTIONS.subscribe("scratch_ensembles")
def subscribe(scratch_ensembles, config_folder, portable):
    if scratch_ensembles is not None:
        for ensemble_name, ensemble_path in scratch_ensembles.items():
            if not pathlib.Path(ensemble_path).is_absolute():
                scratch_ensembles[ensemble_name] = str(config_folder / ensemble_path)

            if not portable and not glob.glob(scratch_ensembles[ensemble_name]):
                raise ValueError(
                    f"Ensemble {ensemble_name} is said to be located at {ensemble_path},"
                    " but that wildcard path does not give any matches."
                )

    return scratch_ensembles
