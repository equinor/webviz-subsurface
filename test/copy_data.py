#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import datetime
from pathlib import Path, PosixPath, WindowsPath

import dash

import webviz_config
import webviz_config.plugins
from webviz_config.themes import installed_themes
from webviz_config.webviz_store import WEBVIZ_STORAGE
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.common_cache import CACHE
from webviz_config.utils import deprecate_webviz_settings_attribute_in_dash_app

logging.getLogger().setLevel(logging.WARNING)

theme = webviz_config.WebvizConfigTheme("equinor")
theme.from_json((Path(__file__).resolve().parent / "theme_settings.json").read_text())

app = dash.Dash()
app.config.suppress_callback_exceptions = True

# Create the common webviz_setting object that will get passed as an
# argument to all plugins that request it.
webviz_settings: webviz_config.WebvizSettings = webviz_config.WebvizSettings(
    shared_settings=webviz_config.SHARED_SETTINGS_SUBSCRIPTIONS.transformed_settings(
        {'scratch_ensembles': {'sens_run': '../reek_fullmatrix/realization-*/iter-0', 'iter-0': '../reek_history_match/realization-*/iter-0', 'iter-3': '../reek_history_match/realization-*/iter-3', 'drogon-iter-0': '/scratch/fmu/cott/16_drogon_ahm/realization-*/iter-0/', 'drogon-iter-3': '/scratch/fmu/cott/16_drogon_ahm/realization-*/iter-3/'}}, PosixPath('/private/tnatt/git_folder/webviz-subsurface-testdata/webviz_examples'), False 
    ),
    theme=theme,
)

# Previously, webviz_settings was piggybacked onto the Dash application object.
# For a period of time, keep it but mark access to the webviz_settings attribute
# on the Dash application object as deprecated.
deprecate_webviz_settings_attribute_in_dash_app()
app._deprecated_webviz_settings = {
    "shared_settings" : webviz_settings.shared_settings,
    "theme" : webviz_settings.theme
}

CACHE.init_app(app.server)

WEBVIZ_STORAGE.storage_folder = Path(__file__).resolve().parent / "resources" / "webviz_storage"

# The lines below can be simplified when assignment
# expressions become available in Python 3.8
# (https://www.python.org/dev/peps/pep-0572)

plugins = []








plugins.append(webviz_config.plugins.InplaceVolumes(app=app, webviz_settings=webviz_settings, **{'ensembles': ['sens_run'], 'volfiles': {'geogrid': 'geogrid--oil.csv', 'simgrid': 'simgrid--oil.csv'}, 'csvfile_vol': None, 'csvfile_parameters': None, 'volfolder': 'share/results/volumes', 'drop_constants': True}))





plugins.append(webviz_config.plugins.InplaceVolumes(app=app, webviz_settings=webviz_settings, **{'ensembles': ['drogon-iter-0', 'drogon-iter-3'], 'volfiles': {'geogrid': 'geogrid--vol.csv', 'simgrid': 'simgrid--vol.csv'}, 'csvfile_vol': None, 'csvfile_parameters': None, 'volfolder': 'share/results/volumes', 'drop_constants': True}))




for plugin in plugins:
    if hasattr(plugin, "add_webvizstore"):
        WEBVIZ_STORAGE.register_function_arguments(plugin.add_webvizstore())

WEBVIZ_ASSETS.make_portable(Path(__file__).resolve().parent / "resources" / "assets")

WEBVIZ_STORAGE.build_store()