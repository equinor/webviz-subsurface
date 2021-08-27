from typing import Dict, List
import glob
import pathlib
import json
import jsonschema
import jsonschema.exceptions

from pkg_resources import get_distribution, DistributionNotFound
import webviz_config

from webviz_subsurface_components import ExpressionInfo
from webviz_subsurface._utils.vector_calculator import (
    ConfigExpressionData,
    expressions_from_config,
    PREDEFINED_EXPRESSIONS_JSON_SCHEMA,
)

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


@webviz_config.SHARED_SETTINGS_SUBSCRIPTIONS.subscribe("scratch_ensembles")
def subscribe_scratch_ensembles(
    scratch_ensembles: dict, config_folder: pathlib.Path, portable: bool
) -> dict:
    if scratch_ensembles is not None:
        for ensemble_name, ensemble_path in scratch_ensembles.items():
            if not pathlib.Path(ensemble_path).is_absolute():
                scratch_ensembles[ensemble_name] = str(config_folder / ensemble_path)

            if not portable and not glob.glob(
                str(pathlib.Path(scratch_ensembles[ensemble_name]) / "OK")
            ):
                if not glob.glob(scratch_ensembles[ensemble_name]):
                    raise ValueError(
                        f"Ensemble {ensemble_name} is said to be located at {ensemble_path},"
                        " but that wildcard path does not give any matches."
                    )
                raise ValueError(
                    f"No realizations with a valid target file ('OK') found for ensemble "
                    f"{ensemble_name} located at {ensemble_path}. This can occur when running "
                    "ERT if no simulations are finished, or all simulations have failed."
                )

    return scratch_ensembles


@webviz_config.SHARED_SETTINGS_SUBSCRIPTIONS.subscribe("predefined_expressions")
def subcribe_predefined_expressions(
    predefined_expressions: str,
    config_folder: pathlib.Path,
) -> List[ExpressionInfo]:
    predefined_expressions_list: List[ExpressionInfo] = []

    if predefined_expressions is not None:
        if not pathlib.Path(predefined_expressions).is_absolute():
            predefined_expressions = str(config_folder / predefined_expressions)

        json_file = open(predefined_expressions)
        predefined_expressions_data: Dict[str, ConfigExpressionData] = json.load(
            json_file
        )

        try:
            jsonschema.validate(
                instance=predefined_expressions_data,
                schema=PREDEFINED_EXPRESSIONS_JSON_SCHEMA,
            )
        except jsonschema.exceptions.ValidationError as err:
            raise ValueError from err

        predefined_expressions_list = expressions_from_config(
            predefined_expressions_data
        )
    return predefined_expressions_list
