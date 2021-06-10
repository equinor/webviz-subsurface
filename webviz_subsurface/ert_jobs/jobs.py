from pathlib import Path
from pkg_resources import resource_filename

try:
    from ert_shared.plugins.plugin_manager import hook_implementation
    from ert_shared.plugins.plugin_response import plugin_response
except ModuleNotFoundError:
    # ert is not installed - use dummy/transparent function decorators.
    def hook_implementation(func):
        return func

    def plugin_response(plugin_name):  # pylint: disable=unused-argument
        def decorator(func):
            return func

        return decorator


@hook_implementation
@plugin_response(plugin_name="webviz-subsurface")
def installable_jobs():
    resource_directory = Path(
        resource_filename("webviz_subsurface", "ert_jobs/config_jobs")
    )
    return {
        "EXPORT_CONNECTION_STATUS": str(resource_directory / "EXPORT_CONNECTION_STATUS")
    }
