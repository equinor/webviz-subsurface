import datetime
from typing import Dict

import dateutil.parser  # type: ignore
import numpy as np
import pandas as pd


def make_date_column_datetime_object(df: pd.DataFrame) -> pd.DataFrame:

    # Make a copy since it is likely we will modify the dataframe, and
    # we don't know if it is a view on a larger DF or a copy
    df = df.copy()

    if "DATE" not in df.columns:
        return df

    sampled_date_value = df["DATE"].values[0]

    # Infer datatype (Pandas cannot answer it) based on the first element:
    if isinstance(sampled_date_value, pd.Timestamp):
        df["DATE"] = pd.Series(pd.to_pydatetime(df["DATE"]), dtype="object")

    elif isinstance(sampled_date_value, str):
        # Do not use pd.Series.apply() here, Pandas would try to convert it to
        # datetime64[ns] which is limited at year 2262.
        df["DATE"] = pd.Series(
            [dateutil.parser.parse(datestr) for datestr in df["DATE"]], dtype="object"
        )

    elif isinstance(sampled_date_value, datetime.date):
        df["DATE"] = pd.Series(
            [
                datetime.datetime.combine(dateobj, datetime.datetime.min.time())
                for dateobj in df["DATE"]
            ],
            dtype="object",
        )

    return df


def find_min_max_for_numeric_df_columns(
    df: pd.DataFrame,
) -> Dict[str, dict]:

    ret_dict = {}
    for col_name in df.columns:
        series = df[col_name]
        if pd.api.types.is_numeric_dtype(series):
            # minval = series.min().item()
            # maxval = series.max().item()

            nparr = series.values
            minval = np.nanmin(nparr).item()
            maxval = np.nanmax(nparr).item()

            ret_dict[col_name] = {"min": minval, "max": maxval}

    return ret_dict

    # Using df.describe() seems to be very slow!
    # desc_df = df.describe(percentiles=[], include=[np.number])
    # ret_dict = {}
    # for vec_name in desc_df.columns:
    #     minval = desc_df[vec_name]["min"]
    #     maxval = desc_df[vec_name]["max"]
    #     ret_dict[vec_name] = {"min": minval, "max": maxval}

    # return ret_dict
