import warnings
from pathlib import Path
from typing import Dict, List

import pandas as pd
from fmu.tools.fipmapper import fipmapper


class VolumeValidatorAndCombinator:
    """
    Class to validate volumetric dataframes based on their type (static/dynamic),
    and to ensure correct format of combined volumetric dataframe before initialization
    of an InplaceVolumesModel instance. A best guess of each source's volume are made based
    on available columns. Only common columns between the different volumetric sources are kept.

    If the input contains both dynamic and static sources and a fipfile with FIPNUM to
    REGION∕ZONE mapping information is provided, the FipMapper from fmu.tools are utilized to
    create sets that are comparable in volumes. The volumes in the reulting dataframe will be
    combined per set. Only region selectors FIPNUM/REGION∕ZONE which are unique whithin each set
    are kept in the resulting dataframe, if none meets the criteria SET is used.

    Static dataframes must follow a strict format to fit the data processing steps of the
    InplaceVolumesModel instance. If custom columns found the source is set as dynamic to
    avoid this processing.
    Dynamic dataframes must contain a FIPNUM column but custom columns are allowed.
    """

    ENSEMBLE_COLUMNS = ["ENSEMBLE", "REAL", "SOURCE"]
    VALID_STATIC_SELECTORS = ["ZONE", "REGION", "FACIES", "LICENSE"]
    VALID_STATIC_RESPONSES = [
        "BULK",
        "NET",
        "PORV",
        "HCPV",
        "GIIP",
        "STOIIP",
        "ASSOCIATEDOIL",
        "ASSOCIATEDGAS",
    ]
    FLUID_TYPES = ["TOTAL", "GAS", "OIL"]

    def __init__(self, volumes_table: pd.DataFrame, fipfile: Path = None):

        self.volume_sources: Dict[str, List[str]] = {
            "static": [],
            "dynamic": [],
            "unknown": [],
        }
        self.disjoint_set_df = (
            fipmapper.FipMapper(yamlfile=fipfile).disjoint_sets() if fipfile else None
        )

        self.dframe = self.validate_and_combine_sources(
            self.drop_rows_with_totals_from_selectors(volumes_table)
        )
        self.volume_type = self.set_volumetric_type()

        if self.volume_type == "mixed":
            self.drop_total_columns()

    @property
    def possible_static_columns(self) -> list:
        possible_static_columns = self.VALID_STATIC_SELECTORS + self.ENSEMBLE_COLUMNS
        for fluid in self.FLUID_TYPES:
            possible_static_columns.extend(
                [f"{col}_{fluid}" for col in self.VALID_STATIC_RESPONSES]
            )
        return possible_static_columns

    def pore_to_porv_mapping(self, dframe: pd.DataFrame) -> pd.DataFrame:
        """
        Check if any columns startswith "PORE", if found rename to standard "PORV".
        Needs to be done on ensemble level to avoid issue with duplicate columns.
        """
        if any(col.startswith("PORE_") for col in dframe):
            dfs = []
            for _, df in dframe.groupby("ENSEMBLE"):
                dfs.append(
                    df.dropna(axis=1, how="all").rename(
                        columns={
                            f"PORE_{fluid}": f"PORV_{fluid}"
                            for fluid in self.FLUID_TYPES
                        },
                        errors="ignore",
                    )
                )
            dframe = pd.concat(dfs)
        return dframe

    def validate_and_combine_sources(self, volumes_table: pd.DataFrame) -> pd.DataFrame:
        """
        Validate columns for each volumetric source and combine them. Only common columns
        are kept. If a fipfile is provided volumes are summed per disjoint_set.
        """
        dfs = []
        all_columns = set()
        for source, voldf in volumes_table.groupby("SOURCE"):
            voldf = voldf.dropna(axis=1, how="all")
            voldf = self.pore_to_porv_mapping(voldf)
            volume_type = self.find_volume_type(voldf.columns, source)
            self.volume_sources[volume_type].append(source)
            all_columns.update(voldf.columns)
            dfs.append(voldf)

        dframe = (
            pd.concat(dfs, join="inner", ignore_index=True)
            if self.disjoint_set_df is None
            else self.create_set_dframe(volume_dfs=dfs)
        )

        missing_columns = [col for col in all_columns if col not in dframe]
        if missing_columns:
            warnings.warn(
                f"Skipping volumetric columns: {missing_columns} as they are not present in all "
                "volumetric sources"
            )
        return dframe

    def set_volumetric_type(self) -> str:
        """Return volumetric type based on available volume sources"""
        if self.volume_sources["static"] and (
            self.volume_sources["dynamic"] or self.volume_sources["unknown"]
        ):
            if self.volume_sources["dynamic"] and self.disjoint_set_df is None:
                raise ValueError(
                    "A fipfile must be provided to map FIPNUMS to REGION/ZONE when both static "
                    "and dynamic volume sources are given as input. "
                    f"Static sources: {self.volume_sources['static']} "
                    f"Dynamic sources: {self.volume_sources['dynamic']}"
                )
            return "mixed"
        return "static" if self.volume_sources["static"] else "dynamic"

    def find_volume_type(self, columns: list, source: str) -> str:
        """Return volume type (stativ/dynamic) based on columns and validate"""
        static_selectors_present = any(
            col in self.VALID_STATIC_SELECTORS for col in columns
        )
        non_static_columns = [
            col for col in columns if col not in self.possible_static_columns
        ]
        # Guess volume type based on columns
        if "FIPNUM" in columns:
            return "dynamic"

        if not non_static_columns:
            if not static_selectors_present:
                raise ValueError(
                    f"Static volume source {source} provided with no valid selectors. "
                    f"One of {self.VALID_STATIC_SELECTORS} must be provided."
                )
            return "static"

        if static_selectors_present:
            warnings.warn(
                f"The volumetric source {source} is considered a dynamic source due "
                f"to the presence of columns: {non_static_columns}. "
                "If this is a static source remove or rename these columns to "
                "trigger correct plugin mode. "
                f"Valid static columns are: {self.possible_static_columns}"
            )
            return "unknown"

        raise ValueError(
            f"Volume source {source} provided with no valid selectors. "
            f"One of {self.VALID_STATIC_SELECTORS + ['FIPNUM']} must be provided."
        )

    def create_set_dframe(self, volume_dfs: List[pd.DataFrame]) -> pd.DataFrame:
        """Sum Eclipse and RMS volumetrics over the common disjoints sets."""
        region_selectors = self.find_region_selectors()
        set_data_list = []
        for set_idx, df in self.disjoint_set_df.groupby(["SET"]):
            for voldf in volume_dfs:
                source = voldf["SOURCE"].unique()[0]
                if "FIPNUM" in voldf.columns:
                    filtered_df = voldf[voldf["FIPNUM"].isin(df["FIPNUM"].unique())]
                elif "ZONE" in voldf.columns and "REGION" in voldf.columns:
                    filtered_df = voldf[
                        (voldf["REGION"].isin(df["REGION"].unique()))
                        & (voldf["ZONE"].isin(df["ZONE"].unique()))
                    ]
                else:
                    raise ValueError(
                        f"Fipfile is provided but volumetric source {source} is missing "
                        "ZONE/REGION or FIPNUM definition."
                    )
                set_df = (
                    filtered_df.groupby(["ENSEMBLE", "REAL"])
                    .sum()
                    .reset_index()
                    .drop(labels=["FIPNUM", "REGION", "ZONE"], errors="ignore")
                )
                for col in region_selectors:
                    set_df[col] = df[col].iloc[0] if col != "SET" else set_idx
                set_df["SOURCE"] = source
                set_data_list.append(set_df)

        dframe = pd.concat(set_data_list, join="inner", ignore_index=True)
        if "FIPNUM" in dframe:
            dframe = dframe.sort_values(by=["FIPNUM"])
        return dframe

    def find_region_selectors(self) -> list:
        """Return region selectors that has a unique value
        per set. If none is found SET is used"""
        df = self.disjoint_set_df.groupby(["SET"]).nunique()
        regcols = ["FIPNUM", "REGION", "ZONE"]
        if any((df[x] == 1).all() for x in regcols):
            return [x for x in regcols if (df[x] == 1).all()]
        return ["SET"]

    def drop_total_columns(self) -> None:
        """Drop columns with "TOTAL" if both static and dynamic volumes in input"""
        total_columns = [col for col in self.dframe if col.endswith("_TOTAL")]
        if total_columns:
            warnings.warn(
                f"Dropping columns {total_columns} to avoid misleading comparison between "
                "static and dynamic columns with TOTAL."
            )
            self.dframe.drop(columns=total_columns, inplace=True)

    @staticmethod
    def drop_rows_with_totals_from_selectors(dframe: pd.DataFrame) -> pd.DataFrame:
        """Drop rows containing total volumes ("Totals") if present"""
        selectors = [col for col in ["ZONE", "REGION", "FACIES"] if col in dframe]
        for sel in selectors:
            dframe = dframe.loc[dframe[sel] != "Totals"]
        return dframe
