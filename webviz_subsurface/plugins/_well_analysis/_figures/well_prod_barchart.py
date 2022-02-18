from typing import Any, Dict, List

import pandas as pd

from .._ensemble_data import EnsembleData


class WellProdBarChart:
    def __init__(
        self,
        ensembles: str,
        data_models: Dict[str, EnsembleData],
        sumvec: str,
        filter_out_startswith: str,
    ) -> None:

        self._traces: List[Dict[str, Any]] = []
        self._layout = {"title": "Some title", "barmode": "overlay"}

        for ensemble in ensembles:
            data_model = data_models[ensemble]
            sumvecs = [
                f"{sumvec}:{well}"
                for well in data_model.wells
                if not well.startswith(filter_out_startswith)
            ]
            df = data_models[ensemble].summary_data
            df = df[df["DATE"] == df["DATE"].max()]
            df_long = pd.melt(
                df, value_vars=sumvecs, var_name="WELL", value_name=sumvec
            )
            df_long["WELL"] = df_long.agg(
                lambda x: f"{x['WELL'].split(':')[1]}", axis=1
            )

            df_mean = df_long.groupby("WELL").mean().reset_index()
            df_mean = df_mean[df_mean[sumvec] > 0]

            self._traces.append(
                {
                    "x": df_mean["WELL"],
                    "y": df_mean[sumvec],
                    # "text": df_mean["TEXT"],
                    "orientation": "v",
                    "type": "bar",
                    "name": ensemble,
                    # "marker": {"color": color},
                    # "textposition": textposition,
                }
            )

    @property
    def traces(self) -> List[Dict[str, Any]]:
        return self._traces

    @property
    def layout(self) -> Dict[str, Any]:
        return self._layout

        # df = self.smry.copy()
        # df_hist = util.convert_to_longform(
        #     df[df.DATE == hist_date], stubnames=[vec], keep_columns=["REAL"]
        # )
        # df_pred = util.convert_to_longform(
        #     df[df.DATE == df.DATE.max()], stubnames=[vec], keep_columns=["REAL"]
        # )
        # keep_wells = [
        #     well
        #     for well in df_hist["GROUP"].unique()
        #     if not well.startswith(filter_out)
        # ]

        # df_hist = df_hist[df_hist["GROUP"].isin(keep_wells)]
        # df_pred = df_pred[df_pred["GROUP"].isin(keep_wells)]
        # df_hist = df_hist[df_hist[vec] > 0]
        # df_pred = df_pred[df_pred[vec] > 0]

        # fig = go.Figure()
        # title = title if title is not None else vec
        # fig.update_layout(title=title, barmode="overlay")

        # fig.add_trace(
        #     get_barchart_trace(
        #         df_pred, vec, "Prediction", "outside", "#ff7f0e", show_recfac=False
        #     )
        # )
        # fig.add_trace(
        #     get_barchart_trace(
        #         df_hist, vec, "History", "inside", "#1f77b4", show_recfac=False
        #     )
        # )

        # fig.show()


# def get_barchart_trace(
#     df, vec, name, textposition, color, errorbars=False, show_recfac=False
# ):
#     df_mean = df.groupby("GROUP").mean().reset_index()
#     if show_recfac:
#         df_mean["TEXT"] = df_mean.agg(
#             lambda x: f"{human_format(x[vec])}  {x['RF']:.1f}%", axis=1
#         )
#     else:
#         df_mean["TEXT"] = df_mean.agg(lambda x: f"{human_format(x[vec])}", axis=1)
#     trace = {
#         "x": df_mean["GROUP"],
#         "y": df_mean[vec],
#         "text": df_mean["TEXT"],
#         "orientation": "v",
#         "type": "bar",
#         "name": name,
#         "marker": {"color": color},
#         "textposition": textposition,
#     }

#     if errorbars:
#         df_p10 = df.groupby("GROUP").quantile(0.1).reset_index()
#         df_p10 = df_p10.merge(df_mean, on="GROUP")
#         df_p10[vec] = df_p10[f"{vec}_y"] - df_p10[f"{vec}_x"]

#         df_p90 = df.groupby("GROUP").quantile(0.1).reset_index()
#         df_p90 = df_p90.merge(df_mean, on="GROUP")
#         df_p90[vec] = df_p90[f"{vec}_y"] - df_p90[f"{vec}_x"]

#         trace.update(
#             {
#                 "error_y": {
#                     "array": df_p10[vec],
#                     "arrayminus": df_p90[vec],
#                     "thickness": 0.5,
#                 }
#             }
#         )

#     return trace
