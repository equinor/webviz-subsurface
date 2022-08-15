import pathlib
from selenium.webdriver.common.by import By

from dash.testing.composite import Browser
import dash
from webviz_config import WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.themes import default_theme
from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
from webviz_config.webviz_instance_info import WEBVIZ_INSTANCE_INFO, WebvizRunMode

import webviz_core_components as wcc


class WebvizPageMixin:
    pass


class WebvizComposite(Browser, WebvizPageMixin):
    def __init__(self, server, **kwargs):
        super().__init__(**kwargs)
        self.app = dash.Dash(__name__)
        self.server = server
        self.init_app()
        self.plugin = None

    def init_app(self):
        WEBVIZ_INSTANCE_INFO.initialize(
            dash_app=self.app,
            run_mode=WebvizRunMode.NON_PORTABLE,
            theme=default_theme,
            storage_folder=pathlib.Path(__file__).resolve().parent,
        )
        try:
            WEBVIZ_FACTORY_REGISTRY.initialize(None)
        except RuntimeError:
            pass

        self.app.css.config.serve_locally = True
        self.app.scripts.config.serve_locally = True
        self.app.config.suppress_callback_exceptions = True
        CACHE.init_app(self.app.server)

    def start_server(self, plugin, **kwargs):
        """Start the local server with app."""

        self.app.layout = dash.html.Div(
            className="layoutWrapper",
            children=[
                wcc.WebvizContentManager(
                    id="webviz-content-manager",
                    children=[
                        wcc.WebvizSettingsDrawer(
                            id="settings-drawer",
                            children=plugin.get_all_settings(),
                        ),
                        wcc.WebvizPluginsWrapper(
                            id="plugins-wrapper",
                            children=plugin.plugin_layout(),
                        ),
                    ],
                ),
            ],
        )
        self.plugin = plugin
        # start server with app and pass Dash arguments
        self.server(self.app, **kwargs)

        # set the default server_url, it implicitly call wait_for_page
        self.server_url = self.server.url

    def toggle_webviz_drawer(self):
        """Open the plugin settings drawer"""
        self.driver.find_element(
            getattr(By, "CSS_SELECTOR"), ".WebvizSettingsDrawer__ToggleOpen"
        ).click()

    def find_shared_settings_group_unique_id(
        self, settings_group_id: str, component_unique_id: str
    ):
        unique_id = (
            self.plugin.shared_settings_group(settings_group_id)
            .component_unique_id(component_unique_id)
            .to_string()
        )
        return self.driver.find_element(getattr(By, "CSS_SELECTOR"), f"#{unique_id}")

    def find_view_setting_group_unique_id(
        self, view_id: str, settings_group_id: str, component_unique_id: str
    ):
        unique_id = (
            self.plugin.view(view_id)
            .settings_group(settings_group_id)
            .component_unique_id(component_unique_id)
            .to_string()
        )
        return self.driver.find_element(getattr(By, "CSS_SELECTOR"), f"#{unique_id}")
