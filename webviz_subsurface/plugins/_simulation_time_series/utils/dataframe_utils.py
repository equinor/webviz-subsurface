import datetime

import numpy as np
import pandas as pd

from webviz_subsurface._utils.dataframe_utils import (
    assert_date_column_is_datetime_object,
    make_date_column_datetime_object,
)
from webviz_subsurface._utils.perf_timer import PerfTimer

# *****************************************
#
# TODO: Verify which function is best!
#
# NOTE: Testing with timer scores create_relative_to_date_df_2 as winner!
#
# *****************************************


def create_relative_to_date_df(
    df: pd.DataFrame, relative_date: datetime.datetime
) -> pd.DataFrame:
    df_copy = df.copy()
    df_copy_2 = df.copy()
    print("****************************************")
    make_relative_to_date_df(df_copy, relative_date)
    make_relative_to_date_df_2(df_copy_2, relative_date)
    create_relative_to_date_df_group_by_real(df, relative_date)
    create_relative_to_date_df_group_by_real_2(df, relative_date)
    create_relative_to_date_df_group_by_real_4(df, relative_date)
    # create_relative_to_date_df_group_by_date(df, relative_date)
    # create_relative_to_date_df_group_by_date_2(df, relative_date)
    return create_relative_to_date_df_group_by_real_3(df, relative_date)


def create_relative_to_date_df_group_by_real_2(
    df: pd.DataFrame, relative_date: datetime.datetime
) -> pd.DataFrame:
    """
    Create dataframe where data for relative_date is subtracted from respective
    vector data.

    I.e. Subtract vector data for set of realizations at give date from vectors
    for all dates present in dataframe.

    `Input:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    `Output:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    NOTE:
    - This function iterates over realization group in input df
    - For-loop makes it possible to get realization not present in _relative_date_df
    - When realization is not present in _relative_date_df, the realization is excluded
    from output df.
    """

    assert_date_column_is_datetime_object(df)

    timer = PerfTimer()

    if not set(["DATE", "REAL"]).issubset(set(df.columns)):
        raise ValueError('Expect column "DATE" and "REAL" in input dataframe!')

    # Columns of correct dtype
    _columns = {name: pd.Series(dtype=df.dtypes[name]) for name in df.columns}
    output_df = pd.DataFrame(_columns)

    _relative_date_df: pd.DataFrame = df.loc[df["DATE"] == relative_date].drop(
        columns=["DATE"]
    )
    if _relative_date_df.empty:
        # Dataframe with columns, but no rows
        return output_df

    vectors = [elm for elm in df.columns if elm not in ("DATE", "REAL")]

    # NOTE: This for-loop makes it possible to get real not represented in _relative_date_df!
    for _real, _df in df.groupby("REAL"):
        # __ = timer.lap_ms()
        _relative_date_data = _relative_date_df.loc[
            _relative_date_df["REAL"] == _real
        ].drop(columns=["REAL"])
        # _relative_date_date_lap = timer.lap_ms()

        # If realization does not exist in _relative_date_df
        if _relative_date_data.empty:
            continue

        _df[vectors] = _df[vectors].sub(_relative_date_data.iloc[0], axis=1)
        # _sub_lap = timer.lap_ms()

        output_df = pd.concat([output_df, _df], ignore_index=True)
        # _concat_lap = timer.lap_ms()

        # print(
        #     f"*********** Real: {_real} ***********\n"
        #     f"Loc function: {_relative_date_date_lap} ms"
        #     f"Sub function: {_sub_lap} ms"
        #     f"Concat function: {_concat_lap} ms"
        # )

    make_date_column_datetime_object(output_df)

    print(f"Calculation Second Groupby REAL took: {timer.elapsed_s():.2f}s")

    return output_df


def create_relative_to_date_df_group_by_real_3(
    df: pd.DataFrame, relative_date: datetime.datetime
) -> pd.DataFrame:
    """
    Create dataframe where data for relative_date is subtracted from respective
    vector data.

    I.e. Subtract vector data for set of realizations at give date from vectors
    for all dates present in dataframe.

    `Input:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    `Output:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    NOTE:
    - This function iterates over realization group in input df
    - For-loop makes it possible to get realization not present in _relative_date_df
    - When realization is not present in _relative_date_df, the realization is excluded
    from output df.
    """

    assert_date_column_is_datetime_object(df)

    timer = PerfTimer()

    if not set(["DATE", "REAL"]).issubset(set(df.columns)):
        raise ValueError('Expect column "DATE" and "REAL" in input dataframe!')

    # Columns of correct dtype
    _columns = {name: pd.Series(dtype=df.dtypes[name]) for name in df.columns}
    output_df = pd.DataFrame(_columns)

    _relative_date_df: pd.DataFrame = (
        df.loc[df["DATE"] == relative_date].drop(columns=["DATE"]).set_index("REAL")
    )
    if _relative_date_df.empty:
        # Dataframe with columns, but no rows
        return output_df

    vectors = [elm for elm in df.columns if elm not in ("DATE", "REAL")]

    # NOTE: This for-loop will neglect realizations in input df not present in _relative_date_data!
    for _realization in _relative_date_df.index:
        _df = df.loc[df["REAL"] == _realization].copy()
        _relative_date_data = _relative_date_df.loc[_realization]
        # _relative_date_date_lap = timer.lap_ms()

        # If realization does not exist in _relative_date_df
        if _relative_date_data.empty:
            continue

        _df[vectors] = _df[vectors].sub(_relative_date_data, axis=1)
        # _sub_lap = timer.lap_ms()

        output_df = pd.concat([output_df, _df], ignore_index=True)
        # _concat_lap = timer.lap_ms()

        # print(
        #     f"*********** Real: {_real} ***********\n"
        #     f"Loc function: {_relative_date_date_lap} ms"
        #     f"Sub function: {_sub_lap} ms"
        #     f"Concat function: {_concat_lap} ms"
        # )

    make_date_column_datetime_object(output_df)

    print(f"Calculation Third Groupby REAL took: {timer.elapsed_s():.2f}s")

    return output_df


def create_relative_to_date_df_group_by_real_4(
    df: pd.DataFrame, relative_date: datetime.datetime
) -> pd.DataFrame:
    """
    Create dataframe where data for relative_date is subtracted from respective
    vector data.

    I.e. Subtract vector data for set of realizations at give date from vectors
    for all dates present in dataframe.

    `Input:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    `Output:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    NOTE:
    - This function iterates over realization group in input df
    - For-loop makes it possible to get realization not present in _relative_date_df
    - When realization is not present in _relative_date_df, the realization is excluded
    from output df.
    """

    assert_date_column_is_datetime_object(df)

    timer = PerfTimer()

    if not set(["DATE", "REAL"]).issubset(set(df.columns)):
        raise ValueError('Expect column "DATE" and "REAL" in input dataframe!')

    # Columns of correct dtype
    _columns = {name: pd.Series(dtype=df.dtypes[name]) for name in df.columns}
    output_df = pd.DataFrame(_columns)

    _relative_date_df: pd.DataFrame = (
        df.loc[df["DATE"] == relative_date].drop(columns=["DATE"]).set_index("REAL")
    )
    if _relative_date_df.empty:
        # Dataframe with columns, but no rows
        return output_df

    vectors = [elm for elm in df.columns if elm not in ("DATE", "REAL")]

    # NOTE: This for-loop calculates with np.ndarray objects!
    output_array = None
    for _real in _relative_date_df.index:
        _date_reals = df.loc[df["REAL"] == _real][["DATE", "REAL"]].values
        _vectors = df.loc[df["REAL"] == _real][vectors].values
        _relative_date_data = _relative_date_df.loc[_real].values

        _relative_vectors = _vectors - _relative_date_data

        _relative_matrix = np.column_stack([_date_reals, _relative_vectors])

        if output_array is None:
            output_array = _relative_matrix
        else:
            output_array = np.append(output_array, _relative_matrix, axis=0)

    output_df = pd.DataFrame(columns=df.columns, data=output_array)
    make_date_column_datetime_object(output_df)

    print(f"Calculation Fourth Groupby REAL took: {timer.elapsed_s():.2f}s")

    return output_df


def create_relative_to_date_df_group_by_real(
    df: pd.DataFrame, relative_date: datetime.datetime
) -> pd.DataFrame:
    """
    Create dataframe where data for relative_date is subtracted from respective
    vector data.

    I.e. Subtract vector data for set of realizations at give date from vectors
    for all dates present in dataframe.

    `Input:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    `Output:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    NOTE:
    - This function iterates over realization group in _relative_date_df
    - For-loop the neglects all realization numbers not present in _relative_date_df
    - If a realization in input df is not present in _relative_date_df, the realization
    is excluded from output df.
    """

    assert_date_column_is_datetime_object(df)

    timer = PerfTimer()

    if not set(["DATE", "REAL"]).issubset(set(df.columns)):
        raise ValueError('Expect column "DATE" and "REAL" in input dataframe!')

    # Columns of correct dtype
    _columns = {name: pd.Series(dtype=df.dtypes[name]) for name in df.columns}
    output_df = pd.DataFrame(_columns)

    _relative_date_df: pd.DataFrame = df.loc[df["DATE"] == relative_date].drop(
        columns=["DATE"]
    )
    if _relative_date_df.empty:
        # Dataframe with columns, but no rows
        return output_df

    vectors = [elm for elm in df.columns if elm not in ("DATE", "REAL")]

    # NOTE: This for-loop will neglect realizations in input df not present in
    # _relative_date_data!
    for _real, _real_df in _relative_date_df.groupby("REAL"):
        _relative_date_data = _real_df[vectors].iloc[0]
        _df = df.loc[df["REAL"] == _real].copy()
        _df[vectors] = _df[vectors].sub(_relative_date_data, axis=1)

        output_df = pd.concat([output_df, _df], ignore_index=True)

    make_date_column_datetime_object(output_df)

    print(f"Calculation First Groupby REAL took: {timer.elapsed_s():.2f}s")

    return output_df


# pylint: disable=too-many-locals
def create_relative_to_date_df_group_by_date(
    df: pd.DataFrame, relative_date: datetime.datetime
) -> pd.DataFrame:
    """
    Create dataframe where data for relative_date is subtracted from respective
    vector data.

    I.e. Subtract vector data for set of realizations at give date from vectors
    for all dates present in dataframe.

    `Input:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    NOTE: THIS IS A PROTOTYPE, WHICH IS NOT OPTIMAL FOR PERFORMANCE

    TODO:
    - OPTIMIZE CODE/ REFACTOR
    - HOW TO HANDLE IF relative_date does not exist in one REAL? .dropna()?
    """

    assert_date_column_is_datetime_object(df)

    timer = PerfTimer()

    if not set(["DATE", "REAL"]).issubset(set(df.columns)):
        raise ValueError('Expect column "DATE" and "REAL" in input dataframe!')

    # Columns of correct dtype
    _columns = {name: pd.Series(dtype=df.dtypes[name]) for name in df.columns}
    output_df = pd.DataFrame(_columns)

    _relative_date_df: pd.DataFrame = (
        df.loc[df["DATE"] == relative_date].drop(columns=["DATE"]).set_index(["REAL"])
    )
    if _relative_date_df.empty:
        # TODO: Return empty dataframe with columns and no rows or input df?
        return output_df

    for i, (__, _df) in enumerate(df.groupby("DATE")):
        # __ = timer.lap_ms()
        # TODO: Simplify code within loop?
        _date = _df["DATE"]
        _date_index = pd.Index(_date)

        _df.drop(columns=["DATE"], inplace=True)
        _df.set_index(["REAL"], inplace=True)
        # _relative_date_date_lap = timer.lap_ms()

        # TODO: What if "REAL" is not matching between _relative_date_df and _df
        res = _df.sub(_relative_date_df)  # .dropna(axis=0, how="any")
        # _sub_lap = timer.lap_ms()
        res.reset_index(inplace=True)
        res.set_index(_date_index, inplace=True)
        res.reset_index(inplace=True)
        # _reset_index_lap = timer.lap_ms()

        output_df = pd.concat([output_df, res], ignore_index=True)
        # _concat_lap = timer.lap_ms()

        # print(
        #     f"*********** Iteration {i} ***********\n"
        #     f"Loc function: {_relative_date_date_lap} ms, "
        #     f"Sub function: {_sub_lap} ms, "
        #     f"Reset index function: {_reset_index_lap} ms, "
        #     f"Concat function: {_concat_lap} ms"
        # )

    # TODO: Drop sorting?
    output_df.sort_values(["REAL", "DATE"], ignore_index=True, inplace=True)

    make_date_column_datetime_object(output_df)

    print(f"Calculation First Groupby DATE took: {timer.elapsed_s():.2f}s")

    return output_df


def create_relative_to_date_df_group_by_date_2(
    df: pd.DataFrame, relative_date: datetime.datetime
) -> pd.DataFrame:
    """
    Create dataframe where data for relative_date is subtracted from respective
    vector data.

    I.e. Subtract vector data for set of realizations at give date from vectors
    for all dates present in dataframe.

    `Input:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    NOTE: THIS IS A PROTOTYPE, WHICH IS NOT OPTIMAL FOR PERFORMANCE

    TODO:
    - OPTIMIZE CODE/ REFACTOR
    - HOW TO HANDLE IF relative_date does not exist in one REAL? .dropna()?
    """

    assert_date_column_is_datetime_object(df)

    timer = PerfTimer()

    if not set(["DATE", "REAL"]).issubset(set(df.columns)):
        raise ValueError('Expect column "DATE" and "REAL" in input dataframe!')

    # Columns of correct dtype
    _columns = {name: pd.Series(dtype=df.dtypes[name]) for name in df.columns}
    output_df = pd.DataFrame(_columns)

    _relative_date_df: pd.DataFrame = (
        df.loc[df["DATE"] == relative_date].drop(columns=["DATE"]).set_index(["REAL"])
    )
    if _relative_date_df.empty:
        # TODO: Return empty dataframe with columns and no rows or input df?
        return output_df

    vectors = [elm for elm in df.columns if elm not in ("DATE", "REAL")]

    for i, (__, _df) in enumerate(df.groupby("DATE")):
        # __ = timer.lap_ms()

        # TODO: What if "REAL" is not matching between _relative_date_df and _df
        _df[vectors] = _df[vectors].sub(_relative_date_df[vectors])
        # _sub_lap = timer.lap_ms()

        output_df = pd.concat([output_df, _df], ignore_index=True)
        # _concat_lap = timer.lap_ms()

        # print(
        #     f"*********** Iteration {i} ***********\n"
        #     f"Sub function: {_sub_lap} ms, "
        #     f"Concat function: {_concat_lap} ms"
        # )

    # TODO: Drop sorting?
    output_df.sort_values(["REAL", "DATE"], ignore_index=True, inplace=True)

    make_date_column_datetime_object(output_df)

    print(f"Calculation Second Groupby DATE took: {timer.elapsed_s():.2f}s")

    return output_df


def make_relative_to_date_df(
    df: pd.DataFrame, relative_date: datetime.datetime
) -> None:
    """
    Make dataframe where data for relative_date is subtracted from respective
    vector data.

    I.e. Subtract vector data for set of realizations at give date from vectors
    for all dates present in dataframe.

    `Input:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    NOTE:
    - This function iterates over realization group in _relative_date_df
    - For-loop the neglects all realization numbers not present in _relative_date_df
    - If a realization in input df is not present in _relative_date_df, the realization
    is excluded from relative to date calculation. I.e. subtraction is not performed
    and realization data remain unaffected in df - not calculating relative to date!
    """

    assert_date_column_is_datetime_object(df)

    timer = PerfTimer()

    if not set(["DATE", "REAL"]).issubset(set(df.columns)):
        raise ValueError('Expect column "DATE" and "REAL" in input dataframe!')

    _relative_date_df: pd.DataFrame = df.loc[df["DATE"] == relative_date].drop(
        columns=["DATE"]
    )
    if _relative_date_df.empty:
        # Dataframe with columns, but no rows
        return

    vectors = [elm for elm in df.columns if elm not in ("DATE", "REAL")]

    # NOTE: This for-loop will not perform subtraction for realizations not present in
    # _relative_date_data
    for _real, _real_df in _relative_date_df.groupby("REAL"):
        _relative_date_data = _real_df[vectors].iloc[0]
        df.loc[df["REAL"] == _real, vectors] = df.loc[df["REAL"] == _real, vectors].sub(
            _relative_date_data, axis=1
        )

    make_date_column_datetime_object(df)

    print(f"Calculation with First Make method took {timer.elapsed_s():.2f}s")


def make_relative_to_date_df_2(
    df: pd.DataFrame, relative_date: datetime.datetime
) -> None:
    """
    Make dataframe where data for relative_date is subtracted from respective
    vector data.

    I.e. Subtract vector data for set of realizations at give date from vectors
    for all dates present in dataframe.

    `Input:`
    * df - `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

    NOTE:
    - This function iterates over realization group in _relative_date_df
    - For-loop the neglects all realization numbers not present in _relative_date_df
    - If a realization in input df is not present in _relative_date_df, the realization
    is excluded from relative to date calculation. I.e. subtraction is not performed
    and realization data remain unaffected in df - not calculating relative to date!
    """

    assert_date_column_is_datetime_object(df)

    timer = PerfTimer()

    if not set(["DATE", "REAL"]).issubset(set(df.columns)):
        raise ValueError('Expect column "DATE" and "REAL" in input dataframe!')

    _relative_date_df: pd.DataFrame = (
        df.loc[df["DATE"] == relative_date].drop(columns=["DATE"]).set_index("REAL")
    )

    if _relative_date_df.empty:
        # Dataframe with columns, but no rows
        return

    vectors = [elm for elm in df.columns if elm not in ("DATE", "REAL")]

    # NOTE: This for-loop will not perform subtraction for realizations not present in
    # _relative_date_data
    for _realization in _relative_date_df.index:
        _relative_date_data = _relative_date_df.loc[_realization]
        df.loc[df["REAL"] == _realization, vectors] = df.loc[
            df["REAL"] == _realization, vectors
        ].sub(_relative_date_data, axis=1)

    make_date_column_datetime_object(df)

    print(f"Calculation with Second Make method took {timer.elapsed_s():.2f}s")
