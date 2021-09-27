import importlib
from pathlib import Path
from typing import Callable, Optional

from pkg_resources import resource_filename

try:
    from ert_shared.plugins.plugin_manager import hook_implementation
    from ert_shared.plugins.plugin_response import plugin_response
except ModuleNotFoundError:
    # ert is not installed - use dummy/transparent function decorators.
    def hook_implementation(func: Callable) -> Callable:
        return func

    def plugin_response(
        plugin_name: str,
    ) -> Callable:
        # pylint: disable=unused-argument
        def decorator(func: Callable) -> Callable:
            return func

        return decorator


@hook_implementation
@plugin_response(  # pylint: disable=no-value-for-parameter
    plugin_name="webviz-subsurface"
)
def installable_jobs() -> dict:
    resource_directory = Path(
        resource_filename("webviz_subsurface", "ert_jobs/config_jobs")
    )
    return {
        "WELL_CONNECTION_STATUS": str(resource_directory / "WELL_CONNECTION_STATUS"),
        "SMRY2ARROW": str(resource_directory / "SMRY2ARROW"),
    }


def _get_module_variable_if_exists(
    module_name: str, variable_name: str, default: str = ""
) -> str:
    try:
        script_module = importlib.import_module(module_name)
    except ImportError:
        return default

    return getattr(script_module, variable_name, default)


@hook_implementation
@plugin_response(  # pylint: disable=no-value-for-parameter
    plugin_name="webviz-subsurface"
)
def job_documentation(job_name: str) -> Optional[dict]:
    webviz_subsurface_jobs = set(
        installable_jobs().data.keys()  # pylint: disable=no-member
    )
    if job_name not in webviz_subsurface_jobs:
        return None

    module_name = f"webviz_subsurface.ert_jobs.{job_name.lower()}"

    description = _get_module_variable_if_exists(
        module_name=module_name, variable_name="DESCRIPTION"
    )
    examples = _get_module_variable_if_exists(
        module_name=module_name, variable_name="EXAMPLES"
    )
    category = _get_module_variable_if_exists(
        module_name=module_name, variable_name="CATEGORY", default="other"
    )

    return {
        "description": description,
        "examples": examples,
        "category": category,
    }
