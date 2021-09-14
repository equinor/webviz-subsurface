import pytest

from webviz_subsurface._utils import simulation_timeseries


@pytest.mark.parametrize(
    "date,vector,interval,as_date,res",
    [
        # Testing AVG_ vectors
        ("2000-01-01", "AVG_FOPR", "monthly", False, "2000-01"),
        ("2003-05-12", "AVG_WOPR:OP_1", "monthly", False, "2003-05"),
        ("2002-05-12", "AVG_WOPR:OP_1", "yearly", False, "2002"),
        ("2002-05-12", "AVG_WOPR:OP_1", "yearly", True, "2002-01-01"),
        ("2002-05-12", "AVG_WOPR:OP_1", "daily", False, "2002-05-12"),
        ("2002-05-12", "AVG_WOPR:OP_1", "daily", True, "2002-05-12"),
        (None, "AVG_WOPR:OP_1", "daily", True, None),
        # Testing INTVL_ vectors
        ("2000-01-01", "INTVL_FOPR", "monthly", False, "2000-01"),
        ("2003-05-12", "INTVL_WGPT:OP_1", "monthly", False, "2003-05"),
        ("2002-05-12", "INTVL_WGPT:OP_1", "yearly", False, "2002"),
        ("2002-05-12", "INTVL_WGPT:OP_1", "yearly", True, "2002-01-01"),
        ("2002-05-12", "INTVL_WGPT:OP_1", "daily", False, "2002-05-12"),
        ("2002-05-12", "INTVL_WGPT:OP_1", "daily", True, "2002-05-12"),
        (None, "INTVL_WGPT:OP_1", "daily", True, None),
        # Testing vectors that are not AVG_ or INTVL_. Dates should return as is.
        ("2000-01-01", "FOPR", "monthly", False, "2000-01-01"),
        ("2003-05-12", "FGPT", "monthly", False, "2003-05-12"),
        ("2002-05-12", "WGPT:OP_1", "yearly", False, "2002-05-12"),
        ("2002-05-12", "WOPR:OP_1", "yearly", True, "2002-05-12"),
        ("2002-05-12", "TIMESTEP", "daily", False, "2002-05-12"),
        ("2002-05-12", "NSUMPROB", "daily", True, "2002-05-12"),
        (None, "WWCT:OP_2", "daily", True, None),
    ],
)
def test_date_to_interval_conversion(
    date: str, vector: str, interval: str, as_date: bool, res: str
) -> None:
    if res is None:
        assert (
            simulation_timeseries.date_to_interval_conversion(
                date=date, vector=vector, interval=interval, as_date=as_date
            )
            is None
        )
    else:
        assert (
            simulation_timeseries.date_to_interval_conversion(
                date=date, vector=vector, interval=interval, as_date=as_date
            )
            == res
        )
