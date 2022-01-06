from datetime import date

import pandas as pd

from webviz_subsurface.plugins._simulation_time_series.types import StatisticsOptions
from webviz_subsurface.plugins._simulation_time_series.utils.vector_statistics import (
    create_vectors_statistics_df,
)

# fmt: off
TEST_INPUT_DF = pd.DataFrame(
    columns = ["DATE", "REAL",  "A", "B"],
    data = [
        [date(2000,1,1),  1,      10.0,       50.0    ],
        [date(2000,2,1),  1,      100.0,      500.0   ],
        [date(2000,3,1),  1,      1000.0,     5000.0  ],
        [date(2000,4,1),  1,      10000.0,    50000.0 ],
        [date(2000,5,1),  1,      100000.0,   500000.0],
        [date(2000,1,1),  2,      20.0,       60.0    ],
        [date(2000,2,1),  2,      200.0,      600.0   ],
        [date(2000,3,1),  2,      2000.0,     6000.0  ],
        [date(2000,4,1),  2,      20000.0,    60000.0 ],
        [date(2000,5,1),  2,      200000.0,   600000.0],
        [date(2000,1,1),  4,      30.0,       70.0    ],
        [date(2000,2,1),  4,      300.0,      700.0   ],
        [date(2000,3,1),  4,      3000.0,     7000.0  ],
        [date(2000,4,1),  4,      30000.0,    70000.0 ],
        [date(2000,5,1),  4,      300000.0,   700000.0],
        [date(2000,1,1),  5,      40.0,       80.0    ],
        [date(2000,2,1),  5,      400.0,      800.0   ],
        [date(2000,3,1),  5,      4000.0,     8000.0  ],
        [date(2000,4,1),  5,      40000.0,    80000.0 ],
        [date(2000,5,1),  5,      400000.0,   800000.0]
    ]
)

# pylint: disable=line-too-long
# Columns are:
#           ["DATE", "A"                             "B"                          ]
#           [        MEAN, MIN, MAX, P10, P90, P50,  MEAN, MIN, MAX, P10, P90, P50]
# NOTE: P10 is 90 percentil and P90 is 10 percentile for oil standard
TEST_EXPECTED_DF = pd.DataFrame(
    columns = pd.MultiIndex.from_tuples([
        ("DATE", ""),
        ("A", StatisticsOptions.MEAN),
        ("A", StatisticsOptions.MIN),
        ("A", StatisticsOptions.MAX),
        ("A", StatisticsOptions.P10),
        ("A", StatisticsOptions.P90),
        ("A", StatisticsOptions.P50),
        ("B", StatisticsOptions.MEAN),
        ("B", StatisticsOptions.MIN),
        ("B", StatisticsOptions.MAX),
        ("B", StatisticsOptions.P10),
        ("B", StatisticsOptions.P90),
        ("B", StatisticsOptions.P50),
    ]),
    data = [
        [date(2000,1,1), 25.0,     10.0,     40.0,     37.0,     13.0,     25.0,     65.0,     50.0,     80.0,     77.0,     53.0,     65.0    ],
        [date(2000,2,1), 250.0,    100.0,    400.0,    370.0,    130.0,    250.0,    650.0,    500.0,    800.0,    770.0,    530.0,    650.0   ],
        [date(2000,3,1), 2500.0,   1000.0,   4000.0,   3700.0,   1300.0,   2500.0,   6500.0,   5000.0,   8000.0,   7700.0,   5300.0,   6500.0  ],
        [date(2000,4,1), 25000.0,  10000.0,  40000.0,  37000.0,  13000.0,  25000.0,  65000.0,  50000.0,  80000.0,  77000.0,  53000.0,  65000.0 ],
        [date(2000,5,1), 250000.0, 100000.0, 400000.0, 370000.0, 130000.0, 250000.0, 650000.0, 500000.0, 800000.0, 770000.0, 530000.0, 650000.0],
    ]
)
# fmt: on


def test_create_vectors_statistics_df() -> None:
    statistics_df = create_vectors_statistics_df(TEST_INPUT_DF)

    assert statistics_df.equals(TEST_EXPECTED_DF)
    assert list(statistics_df.columns) == list(TEST_EXPECTED_DF.columns)
