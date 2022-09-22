########################################
#
#  Copyright (C) 2020-     Equinor ASA
#
########################################


from typing import Any, Callable, Dict, List, Tuple

from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum

from ..._datainput.pvt_data import load_pvt_csv, load_pvt_dataframe
from ._views._pvt import PvtView


class PvtPlot(WebvizPluginABC):
    """Visualizes formation volume factor and viscosity data \
    for oil, gas and water from both **csv**, Eclipse **init** and **include** files.

    !> The plugin supports variations in PVT between ensembles, but not between \
    realizations in the same ensemble.
    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`pvt_relative_file_path`:** Local path to a csv file in each \
        realization with dumped pvt data.
    * **`read_from_init_file`:** A boolean flag stating if data shall be \
        read from an Eclipse INIT file instead of an INCLUDE file. \
        This is only used when **pvt_relative_file_path** is not given.
    * **`drop_ensemble_duplicates`:** A boolean flag stating if ensembles \
        which are holding duplicate data of other ensembles shall be dropped. \
        Defaults to False.

    ---
    The minimum requirement is to define `ensembles`.

    If no `pvt_relative_file_path` is given, the PVT data will be extracted automatically
    from the simulation decks of individual realizations using `fmu_ensemble` and `ecl2df`.
    If the `read_from_init_file` flag is set to True, the extraction procedure in
    `ecl2df` will be replaced by an individual extracting procedure that reads the
    normalized Eclipse INIT file.
    Note that the latter two extraction methods can be very slow for larger data and are therefore
    not recommended unless you have a very simple model/data deck.
    If the `drop_ensemble_duplicates` flag is set to True, any ensembles which are holding
    duplicate data of other ensembles will be dropped.

    `pvt_relative_file_path` is a path to a file stored per realization (e.g. in \
    `share/results/tables/pvt.csv`). `pvt_relative_file_path` columns:
    * One column named `KEYWORD` or `TYPE`: with Flow/Eclipse style keywords
        (e.g. `PVTO` and `PVDG`).
    * One column named `PVTNUM` with integer `PVTNUM` regions.
    * One column named `RATIO` or `R` with the gas-oil-ratio as the primary variate.
    * One column named `PRESSURE` with the fluids pressure as the secondary variate.
    * One column named `VOLUMEFACTOR` as the first covariate.
    * One column named `VISCOSITY` as the second covariate.

    The file can e.g. be dumped to disc per realization by a forward model in ERT using
    `ecl2df`.
    """

    class Ids(StrEnum):
        INDICATORS = "pvt-indicators"

    PHASES = ["OIL", "GAS", "WATER"]

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        pvt_relative_file_path: str = None,
        read_from_init_file: bool = False,
        drop_ensemble_duplicates: bool = False,
    ) -> None:
        super().__init__(stretch=True)

        self.ensemble_paths = {
            ensemble: webviz_settings.shared_settings["scratch_ensembles"][ensemble]
            for ensemble in ensembles
        }

        self.plotly_theme = webviz_settings.theme.plotly_theme

        self.pvt_relative_file_path = pvt_relative_file_path

        self.read_from_init_file = read_from_init_file

        self.drop_ensemble_duplicates = drop_ensemble_duplicates

        if self.pvt_relative_file_path is None:
            self.pvt_df = load_pvt_dataframe(
                self.ensemble_paths,
                use_init_file=read_from_init_file,
                drop_ensemble_duplicates=drop_ensemble_duplicates,
            )
        else:
            # Load data from all ensembles into a pandas DataFrame
            self.pvt_df = load_pvt_csv(
                ensemble_paths=self.ensemble_paths,
                csv_file=self.pvt_relative_file_path,
                drop_ensemble_duplicates=drop_ensemble_duplicates,
            )

            self.pvt_df = self.pvt_df.rename(str.upper, axis="columns").rename(
                columns={"TYPE": "KEYWORD", "RS": "RATIO", "R": "RATIO", "GOR": "RATIO"}
            )

        # Ensure that the identifier string "KEYWORD" is contained in the header columns
        if "KEYWORD" not in self.pvt_df.columns:
            raise ValueError(
                (
                    "There has to be a KEYWORD or TYPE column with corresponding Eclipse keyword."
                    "When not providing a csv file, make sure ecl2df is installed."
                )
            )

        self.phases_additional_info: List[str] = []
        if self.pvt_df["KEYWORD"].str.contains("PVTO").any():
            self.phases_additional_info.append("PVTO")
        elif self.pvt_df["KEYWORD"].str.contains("PVDO").any():
            self.phases_additional_info.append("PVDO")
        elif self.pvt_df["KEYWORD"].str.contains("PVCDO").any():
            self.phases_additional_info.append("PVCDO")
        if self.pvt_df["KEYWORD"].str.contains("PVTG").any():
            self.phases_additional_info.append("PVTG")
        elif self.pvt_df["KEYWORD"].str.contains("PVDG").any():
            self.phases_additional_info.append("PVDG")
        if self.pvt_df["KEYWORD"].str.contains("PVTW").any():
            self.phases_additional_info.append("PVTW")

        self.add_view(
            PvtView(self.pvt_df, webviz_settings),
            PvtPlot.Ids.INDICATORS,
        )

    def add_webvizstore(
        self,
    ) -> List[Tuple[Callable, List[Dict[str, Any]]]]:
        return (
            [
                (
                    load_pvt_dataframe,
                    [
                        {
                            "ensemble_paths": self.ensemble_paths,
                            "use_init_file": self.read_from_init_file,
                            "drop_ensemble_duplicates": self.drop_ensemble_duplicates,
                        }
                    ],
                )
            ]
            if self.pvt_relative_file_path is None
            else [
                (
                    load_pvt_csv,
                    [
                        {
                            "ensemble_paths": self.ensemble_paths,
                            "csv_file": self.pvt_relative_file_path,
                            "drop_ensemble_duplicates": self.drop_ensemble_duplicates,
                        }
                    ],
                )
            ]
        )
