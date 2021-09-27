from pathlib import Path
from typing import List

import pandas as pd
import pytest

import webviz_subsurface._datainput.from_timeseries_cumulatives as from_cum


def get_data_df(testdata_folder: Path) -> pd.DataFrame:

    data_df = pd.read_csv(
        testdata_folder / "reek_test_data" / "aggregated_data" / "unsmry--monthly.csv"
    )
    data_df.DATE = data_df.DATE.astype(str)
    return data_df


def test_calc_from_cumulatives(testdata_folder: Path) -> None:
    # Includes monthly data, 10 reals x 4 ensembles, 3 years and 1 month (2000-01-01 to 2003-02-01)
    data_df = get_data_df(testdata_folder)

    ## Test single column key, FOPT as average rate avg_fopr, monthly
    calc_df = from_cum.calc_from_cumulatives(
        data=data_df,
        column_keys="FOPT",
        time_index="monthly",
        time_index_input="monthly",
        as_rate=True,
    )

    # Test real 0, iter-2
    real_data = data_df[(data_df["REAL"] == 0) & (data_df["ENSEMBLE"] == "iter-2")]
    real_calc = calc_df[(calc_df["REAL"] == 0) & (calc_df["ENSEMBLE"] == "iter-2")]

    assert real_calc[real_calc.DATE == "2000-01-01"]["AVG_FOPR"].values == (
        (
            real_data[real_data.DATE == "2000-02-01"]["FOPT"].values
            - real_data[real_data.DATE == "2000-01-01"]["FOPT"].values
        )
        / 31
    )

    assert real_calc[real_calc.DATE == "2002-05-01"]["AVG_FOPR"].values == (
        (
            real_data[real_data.DATE == "2002-06-01"]["FOPT"].values
            - real_data[real_data.DATE == "2002-05-01"]["FOPT"].values
        )
        / 31
    )

    ## Test multiple column keys, WOPT:OP_1 as average rate avg_fopr, monthly
    calc_df = from_cum.calc_from_cumulatives(
        data=data_df,
        column_keys=["WOPT:OP_1", "GOPT:OP"],
        time_index="yearly",
        time_index_input="monthly",
        as_rate=True,
    )
    # Test real 4, iter-0
    real_data = data_df[(data_df["REAL"] == 4) & (data_df["ENSEMBLE"] == "iter-0")]
    real_calc = calc_df[(calc_df["REAL"] == 4) & (calc_df["ENSEMBLE"] == "iter-0")]

    assert real_calc[real_calc.DATE == "2000-01-01"]["AVG_WOPR:OP_1"].values == (
        (
            real_data[real_data.DATE == "2001-01-01"]["WOPT:OP_1"].values
            - real_data[real_data.DATE == "2000-01-01"]["WOPT:OP_1"].values
        )
        / 366
    )

    assert real_calc[real_calc.DATE == "2002-01-01"]["AVG_GOPR:OP"].values == (
        (
            real_data[real_data.DATE == "2003-01-01"]["GOPT:OP"].values
            - real_data[real_data.DATE == "2002-01-01"]["GOPT:OP"].values
        )
        / 365
    )

    assert real_calc[real_calc.DATE == "2002-01-01"]["AVG_WOPR:OP_1"].values == (
        (
            real_data[real_data.DATE == "2003-01-01"]["WOPT:OP_1"].values
            - real_data[real_data.DATE == "2002-01-01"]["WOPT:OP_1"].values
        )
        / 365
    )

    assert real_calc[real_calc.DATE == "2001-01-01"]["AVG_GOPR:OP"].values == (
        (
            real_data[real_data.DATE == "2002-01-01"]["GOPT:OP"].values
            - real_data[real_data.DATE == "2001-01-01"]["GOPT:OP"].values
        )
        / 365
    )

    ## Test multiple column keys, WOPR_OP as average rate avg_fopr, monthly
    calc_df = from_cum.calc_from_cumulatives(
        data=data_df,
        column_keys=["WGPT:OP_2", "GWPT:OP"],
        time_index="monthly",
        time_index_input="monthly",
        as_rate=False,
    )
    # Test real 9, iter-0
    real_data = data_df[(data_df["REAL"] == 9) & (data_df["ENSEMBLE"] == "iter-0")]
    real_calc = calc_df[(calc_df["REAL"] == 9) & (calc_df["ENSEMBLE"] == "iter-0")]

    assert real_calc[real_calc.DATE == "2000-01-01"]["INTVL_WGPT:OP_2"].values == (
        real_data[real_data.DATE == "2000-01-01"]["WGPT:OP_2"].values
        - real_data[real_data.DATE == "2000-02-01"]["WGPT:OP_2"].values
    )

    assert real_calc[real_calc.DATE == "2002-05-01"]["INTVL_GWPT:OP"].values == (
        real_data[real_data.DATE == "2002-06-01"]["GWPT:OP"].values
        - real_data[real_data.DATE == "2002-05-01"]["GWPT:OP"].values
    )

    assert real_calc[real_calc.DATE == "2000-12-01"]["INTVL_WGPT:OP_2"].values == (
        real_data[real_data.DATE == "2001-01-01"]["WGPT:OP_2"].values
        - real_data[real_data.DATE == "2000-12-01"]["WGPT:OP_2"].values
    )

    assert real_calc[real_calc.DATE == "2002-02-01"]["INTVL_GWPT:OP"].values == (
        real_data[real_data.DATE == "2002-03-01"]["GWPT:OP"].values
        - real_data[real_data.DATE == "2002-02-01"]["GWPT:OP"].values
    )

    # Resample the data to yearly datapoints:
    data_df = data_df[
        data_df["DATE"].isin(["2000-01-01", "2001-01-01", "2002-01-01", "2003-01-01"])
    ]
    calc_df = from_cum.calc_from_cumulatives(
        data=data_df,
        column_keys=["WGPT:OP_2", "GWPT:OP"],
        time_index="yearly",
        time_index_input="yearly",
        as_rate=False,
    )
    # Test real 9, iter-0
    real_data = data_df[(data_df["REAL"] == 9) & (data_df["ENSEMBLE"] == "iter-0")]
    real_calc = calc_df[(calc_df["REAL"] == 9) & (calc_df["ENSEMBLE"] == "iter-0")]

    assert real_calc[real_calc.DATE == "2000-01-01"]["INTVL_WGPT:OP_2"].values == (
        real_data[real_data.DATE == "2001-01-01"]["WGPT:OP_2"].values
        - real_data[real_data.DATE == "2000-01-01"]["WGPT:OP_2"].values
    )

    assert real_calc[real_calc.DATE == "2002-01-01"]["INTVL_GWPT:OP"].values == (
        real_data[real_data.DATE == "2003-01-01"]["GWPT:OP"].values
        - real_data[real_data.DATE == "2002-01-01"]["GWPT:OP"].values
    )


@pytest.mark.parametrize(
    "column_keys,time_index,time_index_input,as_rate",
    [
        (["WGPT:OP_2", "GWPT:OP"], "monthly", "yearly", False),
        (["WGPT:OP_2", "GWPT:OP"], "daily", "monthly", True),
        (["WGPT:OP_2", "GWPT:OP"], "daily", "yearly", True),
    ],
)
def test_calc_from_cumulatives_errors(
    column_keys: List[str],
    time_index: str,
    time_index_input: str,
    as_rate: bool,
    testdata_folder: Path,
) -> None:
    data_df = get_data_df(testdata_folder)
    with pytest.raises(ValueError):
        # Is this variable necessary?
        # pylint: disable=unused-variable
        calc_df = from_cum.calc_from_cumulatives(
            data=data_df,
            column_keys=column_keys,
            time_index=time_index,
            time_index_input=time_index_input,
            as_rate=as_rate,
        )
