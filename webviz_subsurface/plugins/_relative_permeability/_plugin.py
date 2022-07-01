# import from python
from typing import Type
from pathlib import Path

# packages from installed stuff
from dash.development.base_component import Component
import pandas as pd
from webviz_config import WebvizPluginABC

# own imports
from ._error import error
from ._plugin_ids import PlugInIDs # importing the namespace
from .shared_settings import Filter

class RelativePermeability(WebvizPluginABC):
    def __init__(self, path_to_relpermfile: Path ) -> None:
        super().__init__(stretch=True) # super refer to class inhereted from, init from ABC

        # set a member, self first for all
        self.error_message = "" 

        # when reading from file must check that these are the keywords, if not raise ValueError

        try:
            self.relperm_df = pd.read_csv(path_to_relpermfile) # df = data frame
        except PermissionError:
            self.error_message = (
                f"Access to file '{path_to_relpermfile}' denied. "
                f"Please check your path for '{path_to_relpermfile}' and make sure you have access to it."
            )
            return
        except FileNotFoundError:
            self.error_message = (
                f"The file {path_to_relpermfile}' not found."
                "Please check you path"
            )
            return
        except pd.errors.ParserError:
            self.error_message = (
                f"The file '{path_to_relpermfile}' is not a valid csv file."
            )
        except pd.errors.EmptyDataError:
            self.error_message = (
                f"The file '{path_to_relpermfile}' is an empty file."
            )
        except Exception:
            self.error_message = (
                f"Unknown exception when trying to read '{path_to_relpermfile}"
            )