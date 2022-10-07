from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd


class TornadoData:
    REQUIRED_COLUMNS = ["REAL", "SENSNAME", "SENSCASE", "SENSTYPE", "VALUE"]

    def __init__(
        self,
        dframe: pd.DataFrame,
        response_name: Optional[str] = "Response",
        reference: str = "rms_seed",
        cutbyref: bool = False,
        scale: str = "Percentage",
    ) -> None:
        self._reference = reference
        self.response_name = response_name
        self._validate_input(dframe)
        self._scale = scale
        self._reference_average = self._calculate_ref_average(dframe)
        self._tornadotable = self._calculate_tornado_table(dframe)
        if cutbyref:
            self._cut_sensitivities_by_ref()
        self._sort_sensitivities_by_max()
        self._real_df = self._create_real_df(dframe)

    def _validate_input(self, dframe: pd.DataFrame) -> None:
        for col in self.REQUIRED_COLUMNS:
            if col not in dframe:
                raise KeyError(f"Tornado input is missing {col}")

        if list(dframe["SENSCASE"].unique()) == [None]:
            raise KeyError("No sensitivities found in tornado input")

        for sens_name, sens_name_df in dframe.groupby("SENSNAME"):
            if not any(
                (sens_name_df["SENSTYPE"] == st).all() for st in ["scalar", "mc"]
            ):
                raise ValueError(
                    f"Sensitivity {sens_name} is not of type 'mc' or 'scalar"
                )
        if dframe.loc[dframe["SENSNAME"].isin([self._reference])].empty:
            raise ValueError(f"Reference SENSNAME {self._reference} not in input data")

    def _create_real_df(self, dframe: pd.DataFrame) -> pd.DataFrame:
        """Make dataframe with value and case info per realization"""
        realdf = dframe[self.REQUIRED_COLUMNS].rename(
            columns={"SENSNAME": "sensname", "SENSCASE": "senscase"}
        )

        sensitivities = self._tornadotable["sensname"].unique()
        realdf = realdf.loc[realdf["sensname"].isin(sensitivities)]

        for val in self.low_high_realizations_list.values():
            for case in ["high", "low"]:
                casemask = realdf["REAL"].isin(val[f"real_{case}"])
                realdf.loc[casemask, "case"] = case

        mc_mask = realdf["SENSTYPE"] == "mc"
        realdf["casetype"] = np.where(mc_mask, "mc", realdf["case"])
        realdf["sensname_case"] = np.where(
            mc_mask,
            realdf["sensname"],
            realdf[["sensname", "senscase"]].agg("--".join, axis=1),
        )
        return realdf

    @property
    def real_df(self) -> pd.DataFrame:
        return self._real_df

    @property
    def scale(self) -> str:
        return self._scale

    def _calculate_ref_average(self, dframe: pd.DataFrame) -> float:
        # Calculate average response value for reference sensitivity
        return dframe.loc[dframe["SENSNAME"] == self._reference]["VALUE"].mean()

    @property
    def reference_average(self) -> float:
        return self._reference_average

    def _calculate_tornado_table(self, dframe: pd.DataFrame) -> pd.DataFrame:
        avg_per_sensitivity = self._calculate_sensitivity_averages(dframe)
        return pd.DataFrame(self._calculate_tornado_low_high_list(avg_per_sensitivity))

    @property
    def tornadotable(self) -> pd.DataFrame:
        return self._tornadotable

    def _scale_to_ref(self, value: float) -> float:
        value_ref = value - self.reference_average
        if self.scale == "Percentage":
            return (
                (100 * (value_ref / self.reference_average))
                if self.reference_average != 0
                else 0
            )
        return value_ref

    def _calculate_sensitivity_averages(
        self, dframe: pd.DataFrame
    ) -> List[Dict[str, Union[str, list, float]]]:
        avg_per_sensitivity = []

        for sens_name, sens_name_df in dframe.groupby("SENSNAME"):
            # Excluding cases if `ref` is used as `SENSNAME`, and only one realization
            # is present for this `SENSNAME`
            if sens_name == "ref" and len(sens_name_df["REAL"].unique()) == 1:
                continue

            # If `SENSTYPE` is scalar get the mean for each `SENSCASE`
            if (sens_name_df["SENSTYPE"] == "scalar").all():
                for sens_case, sens_case_df in sens_name_df.groupby("SENSCASE"):
                    avg_per_sensitivity.append(
                        {
                            "sensname": sens_name,
                            "senscase": sens_case,
                            "values": sens_case_df["VALUE"].mean(),
                            "values_ref": self._scale_to_ref(
                                sens_case_df["VALUE"].mean()
                            ),
                            "reals": list(map(int, sens_case_df["REAL"])),
                        }
                    )
            # If `SENSTYPE` is monte carlo get p10, p90
            elif (sens_name_df["SENSTYPE"] == "mc").all():

                # Calculate p90(low) and p10(high)
                p90 = sens_name_df["VALUE"].quantile(0.10)
                p10 = sens_name_df["VALUE"].quantile(0.90)

                # Extract list of realizations with values less then reference avg (low)
                low_reals = list(
                    map(
                        int,
                        sens_name_df.loc[
                            sens_name_df["VALUE"] <= self.reference_average
                        ]["REAL"],
                    )
                )

                # Extract list of realizations with values higher then reference avg (high)
                high_reals = list(
                    map(
                        int,
                        sens_name_df.loc[
                            sens_name_df["VALUE"] > self.reference_average
                        ]["REAL"],
                    )
                )

                avg_per_sensitivity.append(
                    {
                        "sensname": sens_name,
                        "senscase": "P90",
                        "values": p90,
                        "values_ref": self._scale_to_ref(p90),
                        "reals": low_reals,
                    }
                )
                avg_per_sensitivity.append(
                    {
                        "sensname": sens_name,
                        "senscase": "P10",
                        "values": p10,
                        "values_ref": self._scale_to_ref(p10),
                        "reals": high_reals,
                    }
                )

        return avg_per_sensitivity

    def _calculate_tornado_low_high_list(
        self, avg_per_sensitivity: List
    ) -> List[Dict[str, Union[str, list, float]]]:
        low_high_per_sensitivity = []
        for sensname, sens_name_df in pd.DataFrame(avg_per_sensitivity).groupby(
            "sensname"
        ):
            low = sens_name_df.copy().loc[sens_name_df["values_ref"].idxmin()]
            high = sens_name_df.copy().loc[sens_name_df["values_ref"].idxmax()]
            if sens_name_df["senscase"].nunique() == 1:
                # Single case sens, implies low == high, but testing just in case:
                if low["values_ref"] != high["values_ref"]:
                    raise ValueError(
                        "For a single sensitivity case, low and high cases should be equal."
                    )
                if low["values_ref"] < 0:
                    # To avoid warnings for changing values of dataframe slices.
                    high = high.copy()
                    high["values_ref"] = 0
                    high["reals"] = []
                    high["senscase"] = None
                    high["values"] = self.reference_average
                else:
                    low = (
                        low.copy()
                    )  # To avoid warnings for changing values of dataframe slices.
                    low["values_ref"] = 0
                    low["reals"] = []
                    low["senscase"] = None
                    low["values"] = self.reference_average

            low_high_per_sensitivity.append(
                {
                    "low": self.calc_low_x(low["values_ref"], high["values_ref"]),
                    "low_base": self.calc_low_base(
                        low["values_ref"], high["values_ref"]
                    ),
                    "low_label": low["senscase"],
                    "low_tooltip": low["values_ref"],
                    "true_low": low["values"],
                    "low_reals": low["reals"],
                    "sensname": sensname,
                    "high": self.calc_high_x(low["values_ref"], high["values_ref"]),
                    "high_base": self.calc_high_base(
                        low["values_ref"], high["values_ref"]
                    ),
                    "high_label": high["senscase"],
                    "high_tooltip": high["values_ref"],
                    "true_high": high["values"],
                    "high_reals": high["reals"],
                }
            )
        return low_high_per_sensitivity

    def _cut_sensitivities_by_ref(self) -> None:
        """Removes sensitivities smaller than reference sensitivity from table"""

        self._tornadotable = self._tornadotable.loc[
            ((self._tornadotable["low"] - self._tornadotable["high"]) != 0)
            | (self._tornadotable["sensname"] == self._reference)
        ]

    def _sort_sensitivities_by_max(self) -> None:
        """Sorts table based on max(abs('low', 'high'))"""
        self._tornadotable["max"] = (
            self._tornadotable[["low", "high"]]
            .apply(lambda x: max(x.min(), x.max(), key=abs), axis=1)  # type: ignore
            .abs()
        )
        self._tornadotable.sort_values("max", ascending=True, inplace=True)
        self._tornadotable.drop(["max"], axis=1, inplace=True)
        self._tornadotable = pd.concat(
            [
                self._tornadotable[self._tornadotable["sensname"] != self._reference],
                self._tornadotable[self._tornadotable["sensname"] == self._reference],
            ]
        )

    @property
    def low_high_realizations_list(self) -> Dict[str, Dict]:
        return {
            sensname: {
                "real_low": sens_name_df["low_reals"].tolist()[0],
                "real_high": sens_name_df["high_reals"].tolist()[0],
            }
            for sensname, sens_name_df in self.tornadotable.groupby("sensname")
        }

    @staticmethod
    def calc_low_base(low: float, high: float) -> float:
        """
        From the low and high value of a parameter,
        calculates the base (starting x value) of the
        bar visualizing low values.
        """
        if low < 0:
            return min(0, high)
        return low

    @staticmethod
    def calc_high_base(low: float, high: float) -> float:
        """
        From the low and high value of a parameter,
        calculates the base (starting x value) of the bar
        visualizing high values.
        """
        if high > 0:
            return max(0, low)
        return high

    @staticmethod
    def calc_high_x(low: float, high: float) -> float:
        """
        From the low and high value of a parameter,
        calculates the x-value (length of bar) of the bar
        visualizing high values.
        """
        if high > 0:
            base = max(0, low)
            return high - base
        return 0.0

    @staticmethod
    def calc_low_x(low: float, high: float) -> float:
        """
        From the low and high value of a parameter,
        calculates the x-value (length of bar) of the bar
        visualizing low values.
        """
        if low < 0:
            base = min(0, high)
            return low - base
        return 0.0
