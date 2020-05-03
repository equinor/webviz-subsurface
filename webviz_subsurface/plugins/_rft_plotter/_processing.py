from webviz_config.common_cache import CACHE


def interpolate_depth(df):
    df = (
        df.pivot_table(index=["DEPTH"], columns=["REAL"], values="PRESSURE")
        .interpolate(limit_direction="both")
        .stack("REAL")
    )
    return df.to_frame().rename(columns={0: "PRESSURE"}).reset_index()


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_frame(dframe, column_values):
    df = dframe.copy()
    for column, value in column_values.items():
        if isinstance(value, list):
            df = df.loc[df[column].isin(value)]
        else:
            df = df.loc[df[column] == value]
    return df
