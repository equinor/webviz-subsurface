from typing import Type
from pathlib import Path

from dash.development.base_component import Component
import pandas as pd
from pandas.errors import ParserError
from pandas.errors import EmptyDataError
from webviz_config import WebvizPluginABC

from ._error import error
from .views import PvtView
from ._pliginIds import PluginIds
from .shared_settings import Filter


class PvtPlotter(WebvizPluginABC):
    def __init__(
        self,
        pvt_relative_file_path: str = None,
    ) -> None:
        super().__init__()

        # Error messages
        self.error_message = ""

        try:
            self.pvt_df = pd.read_csv(pvt_relative_file_path)

        except PermissionError:
            self.error_message = f"Access to file '{pvt_relative_file_path}' denied"
            return

        except FileNotFoundError:
            self.error_message = f"File '{pvt_relative_file_path}' not found."
            return

        except ParserError:
            self.error_message = f"File '{pvt_relative_file_path}' could not be parsed."
            return

        except EmptyDataError:
            self.error_message = f"File '{pvt_relative_file_path}' is an empty file."

        except Exception:
            self.error_message = (
                f"'Unknown exception when trying to read {pvt_relative_file_path} '"
            )

        self.add_store(
            PluginIds.Stores.SELECTED_PHASE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_COLOR, WebvizPluginABC.StorageType.SESSION
        )

        self.add_shared_settings_group(
            Filter(self.pvt_df), PluginIds.SharedSettings.FILTER
        )

        self.add_view(
            PvtView(self.pvt_df), PluginIds.PvtID.INDICATORS, PluginIds.PvtID.GROUP_NAME
        )

    @property
    def layout(self) -> Type[Component]:
        return error(self.error_message)
