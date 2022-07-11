# import from python builtin
from typing import Type, Optional, Union
from pathlib import Path

# packages from installed packages
from dash.development.base_component import Component
import pandas as pd
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_plugin_subclasses import ViewABC

import webviz_subsurface

# own imports
from ._error import error
from ._plugin_ids import PlugInIDs # importing the namespace
from .shared_settings import Filter, Selectors, Visualization , Scal_recommendation
from ..._datainput.fmu_input import load_csv
from ..._datainput.relative_permeability import load_satfunc, load_scal_recommendation
from .views import RelpermCappres

class TestView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        TestViewID = "test-view-id"

    def __init__(self, population_df: pd.DataFrame) -> None:
        super().__init__("Population indicators")
"""
class RelativePermeabilityNew(WebvizPluginABC):
    
    '''
    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: list,
        relpermfile: str = None,
        scalfile: Path = None,
        sheet_name: Optional[Union[str, int, list]] = None,
    ):
    '''
    def __init__(self, webviz_settings: WebvizSettings,relpermfile: str, ensembles: list, scalfile: Path = None,) -> None:
    
    
        super().__init__() # super refer to class inhereted from, init from ABC

        # set a member, self first for all
        self.error_message = ""

        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "block_options.css"
        )

        # when reading from file must check that these are the keywords, if not raise ValueError

        try:
            #self.relperm_df = pd.read_csv(path_to_relpermfile) # df = data frame
            self.ens_paths = {
            ens: WebvizSettings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
            }
            if relpermfile is not None:
                self.satfunc = load_csv(ensemble_paths=self.ens_paths, csv_file=relpermfile)
        except PermissionError:
            self.error_message = (
                f"Access to file '{relpermfile}' denied. "
                f"Please check your path for '{relpermfile}' and make sure you have access to it."
            )
            return
        except FileNotFoundError:
            self.error_message = (
                f"The file {relpermfile}' not found."
                "Please check you path"
            )
            return
        except pd.errors.ParserError:
            self.error_message = (
                f"The file '{relpermfile}' is not a valid csv file."
            )
        except pd.errors.EmptyDataError:
            self.error_message = (
                f"The file '{relpermfile}' is an empty file."
            )
        except Exception:
            self.error_message = (
                f"Unknown exception when trying to read '{relpermfile}"
            )
        
        @property
        def layout(self) -> Type[Component]:
            return error(self.error_message)
    '''
    """


class RelativePermeabilityNew(WebvizPluginABC):
    """Visualizes relative permeability and capillary pressure curves for FMU ensembles.

---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`relpermfile`:** Local path to a csvfile in each realization with dumped relperm data.
* **`scalfile`:** Path to a reference file with SCAL recommendationed data. \
    Path to a single file, **not** per realization/ensemble. The path can be absolute or \
    relative to the `webviz` configuration.
* **`sheet_name`:** Which sheet to use for the `scalfile`, only relevant if `scalfile` is an \
    `xlsx` file (recommended to use csv files with `webviz`).

---
The minimum requirement is to define `ensembles`.

If no `relpermfile` is defined, the relative permeability data will be extracted automatically
from the simulation decks of individual realizations using `fmu-ensemble`and `ecl2df` behind the
scenes. Note that this method can be very slow for larger data decks, and is therefore not
recommended unless you have a very simple model/data deck.

`relpermfile` is a path to a file stored per realization (e.g. in \
`share/results/tables/relperm.csv`). `relpermfile` columns:
* One column named `KEYWORD` or `TYPE`: with Flow/Eclipse style keywords (e.g. `SWOF` and `SGOF`).
* One column named `SATNUM` with integer `SATNUM` regions.
* One column **per** saturation (e.g. `SG` and `SW`).
* One column **per** relative permeability curve (e.g. `KRW`, `KROW` and `KRG`)
* One column **per** capillary pressure curve (e.g. `PCOW`).

The `relpermfile` file can e.g. be dumped to disk per realization by a forward model in ERT that
wraps the command `ecl2csv satfunc input_file -o output_file` (requires that you have `ecl2df`
installed). A typical example could be:
`ecl2csv satfunc eclipse/include/props/relperm.inc -o share/results/tables/relperm.csv`.
[Link to ecl2csv satfunc documentation.](https://equinor.github.io/ecl2df/scripts.html#satfunc)


`scalfile` is a path to __a single file of SCAL recommendations__ (for all
realizations/ensembles). The file has to be compatible with
[pyscal's](https://equinor.github.io/pyscal/pyscal.html#pyscal.\
factory.PyscalFactory.load_relperm_df) input format. Including this file adds reference cases
`Pess`, `Base` and `Opt` to the plots. This file is typically a result of a SCAL study.

`sheet_name` defines the sheet to use in the `scalfile`. Only relevant if `scalfile` is an
`xlsx` file (it is recommended to use `csv` and not `xlsx` for `Webviz`).

* [Example of relpermfile](https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/realization-0/iter-0/share/results/tables/relperm.csv).
* [Example of scalfile](https://github.com/equinor/\
webviz-subsurface-testdata/blob/master/reek_history_match/share/scal/scalreek.csv).
"""
    class PlotOptions:
        SATURATIONS = ["SW", "SO", "SG", "SL"]
        RELPERM_FAMILIES = {
            1: ["SWOF", "SGOF", "SLGOF"],
            2: ["SWFN", "SGFN", "SOF3"],
        }
        SCAL_COLORMAP = {
            "Missing": "#ffff00",  # using yellow if the curve could not be found
            "KRW": "#0000aa",
            "KRG": "#ff0000",
            "KROG": "#00aa00",
            "KROW": "#00aa00",
            "PCOW": "#555555",  # Reserving #000000 for reference envelope (scal rec)
            "PCOG": "#555555",
        }

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: list,
        relpermfile: str = None,
        scalfile: Path = None,
        sheet_name: Optional[Union[str, int, list]] = None,
    ):
        # pylint: disable=too-many-statements

        super().__init__()

        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "block_options.css"
        )
        try:
            # self.ens_paths = {
            #     ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            #     for ens in ensembles
            # }
            # if relpermfile is not None:
            #     self.satfunc = load_csv(ensemble_paths=self.ens_paths, csv_file=relpermfile)
            self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
            }
            self.plotly_theme = webviz_settings.theme.plotly_theme
            self.relpermfile = relpermfile
            if self.relpermfile is not None:
                self.satfunc = load_csv(ensemble_paths=self.ens_paths, csv_file=relpermfile)
                self.satfunc = self.satfunc.rename(str.upper, axis="columns").rename(
                    columns={"TYPE": "KEYWORD"}
                )
                if "KEYWORD" not in self.satfunc.columns:
                    raise ValueError(
                        "There has to be a KEYWORD or TYPE column with "
                        "corresponding Eclipse keyword: e.g SWOF, SGOF and etc."
                    )
                valid_columns = (
                    ["ENSEMBLE", "REAL", "KEYWORD", "SATNUM"]
                    + self.PlotOptions.SATURATIONS
                    + [
                        key
                        for key in self.PlotOptions.SCAL_COLORMAP
                        if key != "Missing"
                    ]
                )
                self.satfunc = self.satfunc[
                    [col for col in self.satfunc.columns if col in valid_columns]
                ]
            else:
                self.satfunc = load_satfunc(self.ens_paths)
            
            if any(
            keyword in self.PlotOptions.RELPERM_FAMILIES[1]
            for keyword in self.satfunc["KEYWORD"].unique()
                ):
                self.family = 1
                if any(
                    keyword in self.PlotOptions.RELPERM_FAMILIES[2]
                    for keyword in self.satfunc["KEYWORD"].unique()
                    ):
                    warnings.warn(
                        (
                            "Mix of keyword family 1 and 2, currently only support "
                            "one family at the time. Dropping all data of family 2 "
                            "('SWFN', 'SGFN', 'SGWFN', 'SOF2', 'SOF3', 'SOF32D') "
                            "and continues with family 1 ('SWOF', 'SGOF', 'SLGOF')."
                        ),
                    )
                    self.satfunc = self.satfunc[
                        self.satfunc["KEYWORD"].isin(
                            self.PlotOptions.RELPERM_FAMILIES["fam1"]
                        )
                    ]
                if "SGOF" in self.satfunc["KEYWORD"].unique():
                    if "SLGOF" in self.satfunc["KEYWORD"].unique():
                        warnings.warn(
                            (
                                "Mix of 'SGOF' and 'SLGOF' in ensembles, resulting in non-unique "
                                "horizontal axis ('SG' and 'SL') for 'KRG', 'KROG' and 'PCOG'. "
                                "Dropping all data with 'SLGOF'."
                            ),
                        )
                        self.satfunc = self.satfunc[self.satfunc["KEYWORD"] != "SLGOF"]
                    self.sat_axes_maps = {
                        "SW": ["KRW", "KROW", "PCOW"],
                        "SG": ["KRG", "KROG", "PCOG"],
                    }
                else:
                    self.sat_axes_maps = {
                        "SW": ["KRW", "KROW", "PCOW"],
                        "SL": ["KRG", "KROG", "PCOG"],
                    }
            elif not all(
            keyword in self.PlotOptions.RELPERM_FAMILIES[2]
            for keyword in self.satfunc["KEYWORD"].unique()
            ):
                raise ValueError(
                    "Unrecognized saturation table keyword in data. This should not occur unless "
                    "there has been changes to ecl2df. Update of this plugin might be required."
                )
            else:
                self.family = 2
                self.sat_axes_maps = {
                    "SW": ["KRW", "PCOW"],
                    "SG": ["KRG", "PCOG"],
                    "SO": ["KROW", "KROG"],
                }
            self.scalfile = scalfile
            self.sheet_name = sheet_name
            self.scal = (
                load_scal_recommendation(self.scalfile, self.sheet_name)
                if self.scalfile is not None
                else None
            )
            

        except PermissionError:
            self.error_message = (
                f"Access to file '{relpermfile}' denied. "
                f"Please check your path for '{relpermfile}' and make sure you have access to it."
            )
            return
        except FileNotFoundError:
            self.error_message = (
                f"The file {relpermfile}' not found."
                "Please check you path"
            )
            return
        except pd.errors.ParserError:
            self.error_message = (
                f"The file '{relpermfile}' is not a valid csv file."
            )
        except pd.errors.EmptyDataError:
            self.error_message = (
                f"The file '{relpermfile}' is an empty file."
            )
        except Exception:
            self.error_message = (
                f"Unknown exception when trying to read '{relpermfile}"
            )
        
        self.add_store(PlugInIDs.Stores.Selectors.SATURATION_AXIS,WebvizPluginABC.StorageType.SESSION)
        self.add_store(PlugInIDs.Stores.Selectors.COLOR_BY,WebvizPluginABC.StorageType.SESSION)
        self.add_store(PlugInIDs.Stores.Selectors.ENSAMBLES,WebvizPluginABC.StorageType.SESSION)
        self.add_store(PlugInIDs.Stores.Selectors.CURVES,WebvizPluginABC.StorageType.SESSION)
        self.add_store(PlugInIDs.Stores.Selectors.SATNUM,WebvizPluginABC.StorageType.SESSION)
        self.add_shared_settings_group(Selectors(self.satfunc,self.plotly_theme,self.sat_axes_maps),
                    PlugInIDs.SharedSettings.SELECTORS)

        
        self.add_store(PlugInIDs.Stores.Visualization.LINE_TRACES,WebvizPluginABC.StorageType.SESSION)
        self.add_store(PlugInIDs.Stores.Visualization.Y_AXIS,WebvizPluginABC.StorageType.SESSION)
        self.add_shared_settings_group(Visualization(self.satfunc),PlugInIDs.SharedSettings.VISUALIZATION)
        '''
        self.add_store(PlugInIDs.Stores.SCALRecomendation.SHOW_SCAL,WebvizPluginABC.StorageType.SESSION)
        self.add_shared_settings_group(Scal_recommendation(self.satfunc),PlugInIDs.SharedSettings.SCAL_RECOMMENDATION)
        '''
        self.add_view(TestView(self.satfunc),PlugInIDs.RelCapViewGroup.RELCAP,PlugInIDs.RelCapViewGroup.GROUP_NAME)

        

        
        @property
        def layout(self) -> Type[Component]:
            return error(self.error_message)
        
        