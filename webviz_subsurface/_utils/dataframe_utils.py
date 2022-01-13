import datetime

import pandas as pd


def assert_date_column_is_datetime_object(df: pd.DataFrame) -> None:
    """Check if date column is on datetime.datetime format

    Raise ValueError if date column is missing, is empty or
    not on datetime.datetime format

    `Assume:`
    * Each row element of "DATE" column is of same type
    * Same data format in each row of in "DATE"-column. Mehtod utilize first
    element of "DATE" column as sample value to detect data type.

    `NOTE:`
    - Type check is performed using type() and not isinstance(), as
    isinstance() gives true on subclass. Thereby instance of pd.Timestamp
    return True - i.e. x: pd.Timestamp -> isinstance(x, datetime.datetime)
    is True.
    """
    if "DATE" not in df.columns:
        raise ValueError('df does not contain column "DATE"')

    # Empty rows
    if df.shape[0] <= 0:
        raise ValueError(
            "DataFrame does not contain rows of data, cannot ensure correct "
            'type in "DATE" column!'
        )

    # Get type from first element
    sampled_date_value = df["DATE"][0]

    # Use type() and not isinstance() as isinstance() gives true on subclass
    # pylint: disable = unidiomatic-typecheck
    if type(sampled_date_value) != datetime.datetime:
        raise ValueError(
            '"DATE"-column in dataframe is not on datetime.datetime format!'
        )


def make_date_column_datetime_object(df: pd.DataFrame) -> None:
    """Convert date column to datetime.datetime format

    Methods only handles "DATE" column of datetime.datetime or pd.Timestamp
    format. With date format datetime.datetime nothing is performed. If
    date column is of format pd.Timestamp the dates are converted. Otherwise
    ValueError is raised.

    `Assume:`
    * Column named "DATE" exist
    * "DATE" column is of type datetime.datetime or pd.Timestamp
    * Row element of "DATE" column is of same type

    `NOTE:`
    - Type check is performed using type() and not isinstance(), as
    isinstance() gives true on subclass. Thereby instance of pd.Timestamp
    return True - i.e. x: pd.Timestamp -> isinstance(x, datetime.datetime) is True
    """
    if "DATE" not in df.columns:
        raise ValueError('df does not contain column "DATE"')

    # Empty rows
    if df.shape[0] <= 0:
        return df

    # Get type from first element
    sampled_date_value = df["DATE"][0]

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
