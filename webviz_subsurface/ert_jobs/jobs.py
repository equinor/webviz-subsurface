from typing import Callable
from pathlib import Path
from pkg_resources import resource_filename

try:
    # pylint: disable=import-error
    from ert_shared.plugins.plugin_manager import (
        hook_implementation,
    )

    from ert_shared.plugins.plugin_response import (
        plugin_response,
    )
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
@plugin_response(
    plugin_name="webviz-subsurface"
)  # pylint: disable=no-value-for-parameter
def installable_jobs() -> dict:
    resource_directory = Path(
        resource_filename("webviz_subsurface", "ert_jobs/config_jobs")
    )
    return {
        "EXPORT_CONNECTION_STATUS": str(resource_directory / "EXPORT_CONNECTION_STATUS")
    }
