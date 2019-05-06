import pandas as pd


class Volumetrics:
    '''### Volumetrics

This container visualizes RMS in-place volumetrics results

* `ensembles`: Which ensembles in `container_settings` to visualize.
* `volfile`:  Local realization path to the RMS volumetrics file
* `title`: Optional title for the container.
'''

    def __init__(self, app, container_settings, ensembles: list, volfile: str,
                 title: str = 'Volumetrics'):

        self.title = title
        self.ensemble_names = ensembles
        self.ensemble_paths = tuple(
            (ens,
             container_settings['scratch_ensembles'][ens])
            for ens in ensembles)

        self.volume_dfs = pd.concat(
            [pd.read_csv(ensemble_path + volfile)
             for ensemble_path in self.ensemble_paths])

        print(self.volume_dfs)
