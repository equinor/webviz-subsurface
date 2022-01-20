import glob
import json
import pathlib
from typing import Dict, List, Optional

import jsonschema
import webviz_config
import yaml
from pkg_resources import DistributionNotFound, get_distribution

from webviz_subsurface._utils.vector_calculator import (
    PREDEFINED_EXPRESSIONS_JSON_SCHEMA,
    ConfigExpressionData,
)

from webviz_subsurface._utils.user_defined_vector_description import (
    USER_DEFINED_VECTOR_DESCRIPTION_JSON_SCHEMA,
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
def subscribe_predefined_expressions(
    predefined_expressions: Optional[Dict[str, str]],
    config_folder: pathlib.Path,
    portable: bool,
) -> Dict[str, pathlib.Path]:

    output: Dict[str, pathlib.Path] = {}

    if predefined_expressions is None:
        return output

    for key, path in predefined_expressions.items():

        if not pathlib.Path(path).is_absolute():
            output[key] = config_folder / path

        if not portable:
            predefined_expressions_data: Dict[
                str, ConfigExpressionData
            ] = yaml.safe_load(output[key].read_text())

            try:
                jsonschema.validate(
                    instance=predefined_expressions_data,
                    schema=PREDEFINED_EXPRESSIONS_JSON_SCHEMA,
                )
            except jsonschema.exceptions.ValidationError as err:
                raise ValueError from err

    return output


@webviz_config.SHARED_SETTINGS_SUBSCRIPTIONS.subscribe(
    "user_defined_vector_descriptions"
)
def subscribe_user_defined_vector_descriptions(
    user_defined_vector_descriptions: Optional[Dict[str, str]],
    config_folder: pathlib.Path,
    portable: bool,
) -> Dict[str, pathlib.Path]:

    output: Dict[str, pathlib.Path] = {}

    if user_defined_vector_descriptions is None:
        return output

    for key, path in user_defined_vector_descriptions.items():

        if not pathlib.Path(path).is_absolute():
            output[key] = config_folder / path

        if not portable:
            vector_descriptions: Dict[str, str] = yaml.safe_load(
                output[key].read_text()
            )

            try:
                jsonschema.validate(
                    instance=vector_descriptions,
                    schema=USER_DEFINED_VECTOR_DESCRIPTION_JSON_SCHEMA,
                )
            except jsonschema.exceptions.ValidationError as err:
                raise ValueError from err

    return output
