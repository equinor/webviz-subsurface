import datetime

import pandas as pd


def assert_date_column_is_datetime_object(df: pd.DataFrame) -> None:
    """Check if date column is on datetime.datetime format

    Raise ValueError if date column is missing, is empty or
    not on datetime.datetime format

    `Assume:`
    * Column named "DATE" exist
    * Each row element of "DATE" column is of same type. Mehtod utilize first
    element of "DATE" column as sample value to detect data type.

    `NOTE:`
    - When no rows - dtype of column is not checked, just early return!
    - Type check is performed using type() and not isinstance(), as
    isinstance() gives true on subclass. Thereby instance of pd.Timestamp
    return True - i.e. x: pd.Timestamp -> isinstance(x, datetime.datetime)
    is True.
    """
    if "DATE" not in df.columns:
        raise ValueError('df does not contain column "DATE"')

    # Empty rows (no dtype check of "DATE"-column)
    if df.shape[0] <= 0:
        return None

    # Get type from first element - use iloc to access by position rather than index label
    sampled_date_value = df["DATE"].iloc[0]

    # Use type() and not isinstance() as isinstance() gives true on subclass
    # pylint: disable = unidiomatic-typecheck
    if type(sampled_date_value) != datetime.datetime:
        raise ValueError(
            '"DATE"-column in dataframe is not on datetime.datetime format!'
        )

    return None


def make_date_column_datetime_object(df: pd.DataFrame) -> None:
    """Convert date column to datetime.datetime format

    Methods only handles "DATE" column of datetime.datetime or pd.Timestamp
    format. With date format datetime.datetime nothing is performed. If
    date column is of format pd.Timestamp the dates are converted. Otherwise
    ValueError is raised.

    `Assume:`
    * Column named "DATE" exist
    * "DATE" column is of type datetime.datetime or pd.Timestamp
    * Each row element of "DATE" column is of same type. Mehtod utilize first
    element of "DATE" column as sample value to detect data type.

    `NOTE:`
    - When no rows - dtype of column is not checked and converted, just early return!
    - Type check is performed using type() and not isinstance(), as
    isinstance() gives true on subclass. Thereby instance of pd.Timestamp
    return True - i.e. x: pd.Timestamp -> isinstance(x, datetime.datetime) is True
    """
    if "DATE" not in df.columns:
        raise ValueError('df does not contain column "DATE"')

    # Empty rows (no dtype check/conversion of "DATE"-column)
    if df.shape[0] <= 0:
        return None

    # Get type from first element - use iloc to access by position rather than index label
    sampled_date_value = df["DATE"].iloc[0]

    # Use type() and not isinstance() as isinstance() gives true on subclass
    # pylint: disable = unidiomatic-typecheck
    if type(sampled_date_value) == datetime.datetime:
        return None

    # Use type() and not isinstance() as isinstance() gives true on subclass
    # pylint: disable = unidiomatic-typecheck
    if type(sampled_date_value) == pd.Timestamp:
        df["DATE"] = pd.Series(
            df["DATE"].dt.to_pydatetime(), dtype=object, index=df.index
        )
        return None

    raise ValueError(
        f'Column "DATE" of type {type(sampled_date_value)} is not handled!'
    )
