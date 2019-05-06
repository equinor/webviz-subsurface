#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import socket
import dash
import dash_auth
import dash_core_components as dcc
import dash_html_components as html
import os.path as path
from pathlib import Path, PosixPath
from flask_talisman import Talisman
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webviz_storage
from webviz_config.webviz_assets import webviz_assets
import webviz_config.containers as standard_containers


app = dash.Dash(__name__, external_stylesheets=[])
server = app.server

app.title = 'Webviz subsurface example of usage'
app.css.config.serve_locally = True
app.scripts.config.serve_locally = True
app.config.suppress_callback_exceptions = True

cache.init_app(server)

CSP = {'default-src': "'self'", 'prefetch-src': "'self'", 'style-src': ["'self'", "'unsafe-inline'", 'https://webviz-cdn.azureedge.net'], 'script-src': ["'self'", "'unsafe-eval'", "'sha256-jZlsGVOhUAIcH+4PVs7QuGZkthRMgvT2n0ilH6/zTM0='"], 'img-src': ["'self'", 'data:', 'https://sibwebvizcdn.blob.core.windows.net'], 'navigate-to': "'self'", 'base-uri': "'self'", 'form-action': "'self'", 'frame-ancestors': "'none'", 'object-src': "'none'", 'font-src': ['https://webviz-cdn.azureedge.net']}
FEATURE_POLICY = {'camera': "'none'", 'geolocation': "'none'", 'microphone': "'none'", 'payment': "'none'"}

Talisman(server, content_security_policy=CSP, feature_policy=FEATURE_POLICY)

webviz_storage.use_storage = True
webviz_storage.storage_folder = path.join(path.dirname(path.realpath(__file__)),
                                          'webviz_storage')

webviz_assets.portable = True


tab_active_style = {
'background-color': 'var(--menuLinkBackgroundSelected)',
'color': 'var(--menuLinkColorSelected)',
}

app.layout = dcc.Tabs(parent_className="layoutWrapper",
                      content_className='pageWrapper',
                      vertical=True, children=[
   

    dcc.Tab(id='logo',className='styledButton',

            children=[
                 standard_containers.BannerImage(**{'image': PosixPath('/private/stcr/venvs/webviz_mar2019/webviz-subsurface/examples/example_banner.png'), 'title': 'My banner image'}).layout,
                 dcc.Markdown(r'''Webviz created from configuration file.''')
                 ]
    ),

    dcc.Tab(id='last_page',label='Summary stats',
            selected_style = tab_active_style,
            selected_className='selectedButton',className='styledButton',

            children=[
                 standard_containers.SummaryStats(app=app, **{'ensembles': ['ens-0', 'ens-1'], 'column_keys': ['FOP*', 'FGP*'], 'container_settings': {'scratch_ensembles': {'ens-0': '/scratch/troll_fmu/rnyb/09_troll_r003/realization-*/iter-0', 'ens-1': '/scratch/troll_fmu/rnyb/15_troll_r004/realization-*/iter-0'}}}).layout
                 ]
    )]
)

if __name__ == '__main__':
    # This part is ignored when the webviz app is started
    # using Docker container and uwsgi (e.g. when hosted on Azure).

    dash_auth.BasicAuth(app, {'some_username': 'some_password'})
    app.run_server(host='localhost', port=8050, ssl_context=('server.crt', 'server.key'), dev_tools_hot_reload=True)