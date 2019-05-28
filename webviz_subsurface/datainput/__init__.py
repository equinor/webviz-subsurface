'''### _Subsurface data input_
Contains data processing functions used in the containers.
Some of the scripts are dependent on FMU postprocessing scripts
that will be made open source in the near future.
'''

from ._history_match import extract_mismatch, scratch_ensemble
from ._intersect import load_surface, get_wfence, get_hfence

__all__ = ['scratch_ensemble',
           'extract_mismatch',
           'load_surface',
           'get_wfence',
           'get_hfence']
try:
  import fmu.ensemble
except ImportError:  # fmu.ensemble is an optional dependency, e.g.
  pass             # for a portable webviz instance, it is never used.


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def extract_mismatch(ens_paths, observation_file: Path) -> pd.DataFrame:
  """Convert the fmu-ensemble mismatch dataframe into the the format
  suitable for the interactive history match visualization.
  """

  list_ens = [scratch_ensemble(ensemble_name, path)
              for (ensemble_name, path) in ens_paths]

  ens_data = fmu.ensemble.EnsembleSet("HistoryMatch", list_ens)

  df_mismatch = fmu.ensemble.Observations(str(observation_file))\
                   .mismatch(ens_data)

  df_mismatch['NORMALISED_MISMATCH'] = \
      df_mismatch['L2'] / (df_mismatch['MEASERROR'] ** 2)

  # Create a dataframe containing number of
  # observation points within each observation key:
  df_count = df_mismatch.groupby(['OBSKEY', 'REAL', 'ENSEMBLE'])\
                        .size()\
                        .to_frame('COUNT')\
                        .reset_index()\
                        .drop_duplicates(['OBSKEY'], keep='first')\
                        .drop(columns=['REAL', 'ENSEMBLE'])

  # 1) Sum the normalised misfit (grouped by obskey, misfit sign
  #    realizaton and ensemble.
  # 2) Pivot the dataframe such that instead of two rows wrt. positive and
  #    negative misfit, we get two columns.
  # 3) Replace NaN values with 0 (NaN happens e.g. for the summed negative
  #    misfit if e.g. all misfit values are positive.
  # 4) Drop the column name 0 (webviz don't need summed misfit over all
  #    observation points with zero misfit :p)
  # 5) Merge in the COUNT column.
  # 6) Rename columns such that the columns from fmu.ensemble corresponds
  #    to those used in the webviz history match visualization.
  return df_mismatch.groupby(['OBSKEY', 'SIGN', 'REAL', 'ENSEMBLE'])\
                    .sum()[['NORMALISED_MISMATCH']]\
                    .pivot_table(index=['OBSKEY', 'REAL', 'ENSEMBLE'],
                                 columns='SIGN',
                                 values='NORMALISED_MISMATCH'
                                 )\
                    .reset_index()\
                    .fillna(0)\
                    .drop(columns=[0], errors='ignore')\
                    .merge(df_count, on='OBSKEY', how='left')\
                    .rename(columns={'OBSKEY': 'obs_group_name',
                                     'REAL': 'realization',
                                     'ENSEMBLE': 'ensemble_name',
                                     'COUNT': 'number_data_points',
                                     1: 'total_pos',
                                     -1: 'total_neg'})


__all__ = ['scratch_ensemble', 'extract_mismatch']
