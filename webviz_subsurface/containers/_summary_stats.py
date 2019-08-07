import itertools
from uuid import uuid4
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_plotly.graph_objs import FanChart
from webviz_config.common_cache import cache
from webviz_config.containers import WebvizContainer
from plotly.colors import DEFAULT_PLOTLY_COLORS
from ..datainput import get_summary_data, get_summary_stats


class SummaryStats(WebvizContainer):

    """Summary statistics

    Args:
        ensembles: list of ensemble paths. Length >= 1
        column_keys: list of pre defined vectors to visualize. Default is none
        sampling: Optional. Either 'monthly' or 'yearly'. Default is 'monthly'.
        title: Optional title for the container.
        history_uncertainty: boolean value if history vector is subjected to
            uncertainty.
    Return:
        dcc.Graph() of either statistics plot or realization plot.
    Annotations:
        Function argument-litst are passed as tuple as they are hashed in
        webviz-store --portable option (list-type is not hashable).
        Pandas within fmu.ensemlbe expects list. Therefore argument-tuples are
        converted back into lists within get_smry_data and get_smry_stats
        functions.
    """

    def __init__(
            self,
            app,
            container_settings,
            ensembles,
            column_keys=None,
            sampling: str = 'monthly',
            history_uncertainty: bool = False):

        self.uid = f'{uuid4()}'
        self.dropwdown_vector_id = f'dropdown-vector-{self.uid}'
        self.column_keys = tuple(column_keys) if isinstance(
            column_keys, (list, tuple)) else None
        self.sampling = sampling
        self.radio_plot_type_id = f'radio-plot-type-{self.uid}'
        self.show_history_uncertainty_id = \
            f'show-history-uncertainty-{self.uid}'
        self.chart_id = f'chart-id-{self.uid}'
        self.ensemble_paths = tuple(
            (ensemble,
             container_settings['scratch_ensembles'][ensemble])
            for ensemble in ensembles)
        self.history_uncertainty = history_uncertainty
        self.vector_columns = sorted(
            list(
                get_summary_data(
                    ensemble_paths=self.ensemble_paths,
                    sampling=self.sampling,
                    column_keys=self.column_keys) .drop(
                        columns=[
                            'DATE',
                            'REAL',
                            'ENSEMBLE']).columns))
        self.smry_history_columns = tuple(
            [vctr + 'H' for vctr in self.vector_columns
             if vctr + 'H' in self.vector_columns])
        self.smry_vector_columns = tuple(
            [vctr for vctr in self.vector_columns
             if vctr not in self.smry_history_columns])
        self.set_callbacks(app)

    @property
    def layout(self):
        return html.Div([
            html.P('Summary Vector:', style={'font-weight': 'bold'}),
            dcc.Dropdown(id=self.dropwdown_vector_id,
                         clearable=False,
                         options=[{'label': i, 'value': i}
                                  for i in self.smry_vector_columns],
                         value=self.smry_vector_columns[0]),
            html.P('Plot type:', style={'font-weight': 'bold'}),
            dcc.RadioItems(id=self.radio_plot_type_id,
                           options=[{'label': i, 'value': i}
                                    for i in ['Realizations', 'Statistics']],
                           value='Realizations'),
            dcc.Checklist(
                id=self.show_history_uncertainty_id,
                options=[{'label': 'Show history', 'value': 'SHOW_H'}],
                value=[],
            ),
            html.Div(id=self.chart_id)
        ])

    def set_callbacks(self, app):
        @app.callback(Output(self.chart_id, 'children'),
                      [Input(self.dropwdown_vector_id, 'value'),
                       Input(self.radio_plot_type_id, 'value'),
                       Input(self.show_history_uncertainty_id, 'value')])
        def update_plot(
                vector,
                summary_plot_type,
                show_history_uncertainty_id):
            if summary_plot_type == 'Realizations':
                return render_realization_plot(
                    ensemble_paths=self.ensemble_paths,
                    column_keys=self.column_keys,
                    sampling=self.sampling,
                    smry_history_columns=self.smry_history_columns,
                    history_uncertainty=self.history_uncertainty,
                    vector=vector,
                    show_history_uncertainty=show_history_uncertainty_id)
            if summary_plot_type == 'Statistics':
                return render_stat_plot(
                    ensemble_paths=self.ensemble_paths,
                    column_keys=self.column_keys,
                    sampling=self.sampling,
                    vector=vector)

    def add_webvizstore(self):
        return [(get_summary_data,
                 [{'ensemble_paths': self.ensemble_paths,
                   'column_keys': self.column_keys,
                   'sampling': self.sampling, }]),
                (get_summary_stats,
                 [{'ensemble_paths': self.ensemble_paths,
                   'column_keys': self.column_keys,
                   'sampling': self.sampling}])]


def trace_group(ens_smry_data, ens, vector, color):

    ens_traces = []

    # 1st and only trace of the legendgroup to show up in legend
    ens_traces.append({
        'x': ens_smry_data[ens_smry_data['REAL']
                           == ens_smry_data.REAL.unique()[0]]['DATE'],
        'y': ens_smry_data[ens_smry_data['REAL']
                           == ens_smry_data.REAL.unique()[0]][vector],
        'legendgroup': ens,
        'name': ens,
        'type': 'markers',
        'marker': {
            'color': color
        },
        'showlegend': True
    })

    for real in ens_smry_data.REAL.unique()[1:]:

        ens_traces.append({
            'x': ens_smry_data[ens_smry_data['REAL'] == real]['DATE'],
            'y': ens_smry_data[ens_smry_data['REAL'] == real][vector],
            'legendgroup': ens,
            'name': ens,
            'type': 'line',
            'marker': {
                'color': color
            },
            'showlegend': False
        })

    return ens_traces


def single_trace(ens_smry_data, ens, vector, color):

    return {
        'x': ens_smry_data[ens_smry_data['REAL']
                           == ens_smry_data.REAL.unique()[0]]['DATE'],
        'y': ens_smry_data[ens_smry_data['REAL']
                           == ens_smry_data.REAL.unique()[0]][vector],
        'legendgroup': ens,
        'name': ens,
        'type': 'markers',
        'marker': {
            'color': color
        },
        'showlegend': True
    }


@cache.memoize(timeout=cache.TIMEOUT)
def render_realization_plot(ensemble_paths: tuple, sampling: str,
                            column_keys: tuple, vector: str,
                            smry_history_columns: tuple,
                            history_uncertainty: bool,
                            show_history_uncertainty: str):
    """ Creates scatter-plot-traces for choosen vector. One trace per
    realization will be created. If history-data are not subjeted to
    uncertainty only one traces per ensemble will be created for history_data.
    If there is no history-vector in for the given vector, no trace will be
    created. """

    cycle_list = itertools.cycle(DEFAULT_PLOTLY_COLORS)
    history_vector = (vector + 'H')

    if history_vector in smry_history_columns:
        smry_data = get_summary_data(
            ensemble_paths=ensemble_paths,
            column_keys=column_keys,
            sampling=sampling)[
                ['REAL', 'DATE', 'ENSEMBLE', vector, history_vector]]
    else:
        smry_data = get_summary_data(
            ensemble_paths=ensemble_paths,
            column_keys=column_keys,
            sampling=sampling)[
                ['REAL', 'DATE', 'ENSEMBLE', vector]]

    smry_data.dropna(subset=[vector])

    plot_traces = []

    for ens in smry_data.ENSEMBLE.unique():

        plot_traces += trace_group(
            ens_smry_data=smry_data[smry_data['ENSEMBLE'] == ens],
            ens=ens,
            vector=vector,
            color=next(cycle_list))

        if (history_vector in smry_history_columns
                and 'SHOW_H' in show_history_uncertainty
                and history_uncertainty):

            plot_traces += trace_group(
                ens_smry_data=smry_data[smry_data['ENSEMBLE'] == ens],
                ens=ens,
                vector=history_vector,
                color='black')

        if (history_vector in smry_history_columns
                and 'SHOW_H' in show_history_uncertainty
                and not history_uncertainty):

            plot_traces += single_trace(
                ens_smry_data=smry_data[smry_data['ENSEMBLE'] == ens],
                ens=ens,
                vector=history_vector,
                color='black')

    layout = {
        'hovermode': 'closest',
        'barmode': 'overlay',
        'bargap': 0.05,
        'xaxis': {'title': 'Date', 'family': 'Equinor'},
        'yaxis': {'title': vector, 'family': 'Equinor'},
        'font': {'family': 'Equinor'},
        'hoverlabel': {'font': {'family': 'Equinor'}},
    }

    return dcc.Graph(figure={'data': plot_traces, 'layout': layout},
                     config={
                         'displaylogo': False,
                         'modeBarButtonsToRemove': ['sendDataToCloud']})


@cache.memoize(timeout=cache.TIMEOUT)
def render_stat_plot(ensemble_paths: tuple, sampling: str, column_keys: tuple,
                     vector: str):
    """Loops over ensemlbe_paths and creates one summary_statistics-plot per
    ensemble."""

    smry_stats = get_summary_stats(
        ensemble_paths=ensemble_paths,
        column_keys=column_keys,
        sampling=sampling)

    fan_chart_divs = []
    for ens in smry_stats.ENSEMBLE.unique():
        vector_stats = smry_stats[
            smry_stats['ENSEMBLE'] == ens][
                vector].unstack().transpose()
        vector_stats['name'] = vector
        vector_stats.rename(index=str, inplace=True,
                            columns={"minimum": "min", "maximum": "max"})
        fan_chart_divs.append(html.H5(ens))
        fan_chart_divs.append(
            html.Div(
                dcc.Graph(
                    id='graph-{}'.format(ens),
                    figure=FanChart(vector_stats.iterrows()),
                    config={
                        'displaylogo': False,
                        'modeBarButtonsToRemove': ['sendDataToCloud']
                    }
                )
            )
        )

    return fan_chart_divs
