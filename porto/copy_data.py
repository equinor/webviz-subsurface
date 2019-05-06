#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dash
import os.path as path
from webviz_config.webviz_store import webviz_storage
from webviz_config.webviz_assets import webviz_assets
from webviz_config.common_cache import cache
from pathlib import Path, PosixPath
import webviz_config.containers as standard_containers


app = dash.Dash()
app.config.suppress_callback_exceptions = True

cache.init_app(app.server)

webviz_storage.storage_folder = path.join(path.dirname(path.realpath(__file__)),
                                          'webviz_storage')

# The lines below can be simplified when assignment
# expressions become available in Python 3.8
# (https://www.python.org/dev/peps/pep-0572)

containers = []




containers.append(standard_containers.BannerImage(**{'image': PosixPath('/private/stcr/venvs/webviz_mar2019/webviz-subsurface/examples/example_banner.png'), 'title': 'My banner image'}))







containers.append(standard_containers.SummaryStats(app=app, **{'ensembles': ['ens-0', 'ens-1'], 'column_keys': ['FOP*', 'FGP*'], 'container_settings': {'scratch_ensembles': {'ens-0': '/scratch/troll_fmu/rnyb/09_troll_r003/realization-*/iter-0', 'ens-1': '/scratch/troll_fmu/rnyb/15_troll_r004/realization-*/iter-0'}}}))




for container in containers:
    if hasattr(container, 'add_webvizstore'):
        webviz_storage.register_function_arguments(container.add_webvizstore())

webviz_storage.build_store()

webviz_assets.make_portable(path.join(path.dirname(path.realpath(__file__)),
                                      'assets'))