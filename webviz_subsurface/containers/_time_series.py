from webviz_subsurface.datainput import load_ensemble_set, get_time_series_data, \
    get_time_series_statistics, get_time_series_fielgains


class TimeSeries(WebvizContainer):

    def __init__(self, app, container_settings):
        self.uid = f'{uuid4()}'

    