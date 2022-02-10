import datetime

import pandas as pd

from webviz_subsurface._utils.dataframe_utils import (
    assert_date_column_is_datetime_object,
    make_date_column_datetime_object,
)


def create_relative_to_date_df(
    df: pd.DataFrame, relative_date: datetime.datetime
) -> pd.DataFrame:
    """
    Create dataframe where data for relative_date is subtracted from respective
    vector data.

    I.e. Subtract realization data at given relative date from corresponding
    realizations at each individual date for each vector column in dataframe.

    `Assume:`
    Set of realizations are equal for each date in "DATE" column of input dataframe.

    `Input:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    `Output:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    NOTE:
    - This function iterates over realization group in input dataframe
    - For-loop makes it possible to get realization not present in relative_date_df, if
    realization is not present in relative_date_df the realization is excluded output.
    """

    assert_date_column_is_datetime_object(df)

    if not set(["DATE", "REAL"]).issubset(set(df.columns)):
        raise ValueError('Expect column "DATE" and "REAL" in input dataframe!')

    # Columns of correct dtype
    _columns = {name: pd.Series(dtype=df.dtypes[name]) for name in df.columns}
    output_df = pd.DataFrame(_columns)

    relative_date_df: pd.DataFrame = df.loc[df["DATE"] == relative_date].drop(
        columns=["DATE"]
    )
    if relative_date_df.empty:
        # Dataframe with columns, but no rows
        return output_df

    vectors = [elm for elm in df.columns if elm not in ("DATE", "REAL")]

    # NOTE: This for-loop makes it possible to get real not represented in relative_date_df!
    for real, real_df in df.groupby("REAL"):
        relative_date_data = relative_date_df.loc[
            relative_date_df["REAL"] == real
        ].drop(columns=["REAL"])

        # If realization does not exist in relative_date_df
        if relative_date_data.empty:
            continue

        real_df[vectors] = real_df[vectors].sub(relative_date_data.iloc[0], axis=1)
        output_df = pd.concat([output_df, real_df], ignore_index=True)

    make_date_column_datetime_object(output_df)
    return output_df
