# Plugin package webviz_subsurface

?> :bookmark: This documentation is valid for version `0.1.3` of `webviz_subsurface`. 

   
These are plugins relevant within subsurface workflows. Most of them
rely on the setting `scratch_ensembles` within
`shared_settings`. This setting connects ensemble names (user defined)
with the paths to where the ensembles are stored, either absolute or
relative to the location of the configuration file.
I.e. you could have
```yaml
title: Reek Webviz Demonstration
shared_settings:
  scratch_ensembles:
    iter-0: /scratch/my_ensemble/realization-*/iter-0
    iter-1: /scratch/my_ensemble/realization-*/iter-1
pages:
  - title: Front page
    content:
      - plugin: ReservoirSimulationTimeSeries
        ensembles:
          - iter-0
          - iter-1
```

 

---



<div class="plugin-doc">

#### DiskUsage

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualize disk usage in a FMU project. It adds a dashboard showing disk usage per user.


 

<!-- tab:Arguments -->

   

* **`scratch_dir`:** Path to the scratch directory to show disk usage for.
* **`date`:** Date as string of form YYYY-MM-DD to request an explisit date. Default is to
to use the most recent file avaialable, limited to the last week.



```yaml
    - DiskUsage:
        scratch_dir:  # Required, type str (corresponding to a path).
        date: null # Optional, type Union[_ForwardRef('str'), NoneType].
```

   

<!-- tab:Data input -->


?> The `scratch_dir` directory must have a hidden folder `.disk_usage` containing daily
csv files called `disk_usage_user_YYYY-MM-DD.csv`, where YYYY-MM-DD is the date.
The plugin will search backwards from the current date, and throw an error if no file was found
from the last week.

The csv file must have the columns `userid` and `usageKB` (where KB means
[kibibytes](https://en.wikipedia.org/wiki/Kibibyte)). All other columns are ignored.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### HistoryMatch

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes the quality of the history match.


 

<!-- tab:Arguments -->

   

* **`ensembles`:** List of the ensembles in `shared_settings` to visualize.
* **`observation_file`:** Path to the observation `.yaml` file (absolute or relative to config file).



```yaml
    - HistoryMatch:
        ensembles:  # Required, type list.
        observation_file:  # Required, type str (corresponding to a path).
```

   

<!-- tab:Data input -->

Parameter values are extracted automatically from the `parameters.txt` files
of the individual realizations of your given `ensembles`, using the `fmu-ensemble` library.

?> The `observation_file` is a common (optional) file for all ensembles, which currently has to be made manually. [An example of the format can be found here](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/share/observations/observations.yml).

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### HorizonUncertaintyViewer

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes depth uncertainty for surfaces in map view and cross section view.

The cross section is defined by wellfiles and surfacefiles or a polyline.
Polylines are drawn interactivly in map view.

!> The plugin reads information from a COHIBA model file.

* **`basedir`:** Path to folder with model_file.xml.
   Make sure that the folder has the same format as a COHIBA folder.
* **`planned_wells_dir`:** Path to folder with planned well files.
   Make sure that all planned wells have format 'ROXAR RMS well'.

 

<!-- tab:Arguments -->



```yaml
    - HorizonUncertaintyViewer:
        basedir: null # Optional, type str (corresponding to a path).
        planned_wells_dir: null # Optional, type str (corresponding to a path).
```

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### InplaceVolumes

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes inplace volumetric results from
FMU ensembles.

Input can be given either as aggregated `csv` files or as ensemble name(s)
defined in `shared_settings` (with volumetric `csv` files stored per realization).


 

<!-- tab:Arguments -->

   

**Using aggregated data**
* **`csvfile`:** Aggregated csvfile with `REAL`, `ENSEMBLE` and `SOURCE` columns (absolute path or relative to config file).

**Using data stored per realization**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`volfiles`:**  Key/value pair of csv files E.g. `{geogrid: geogrid--oil.csv}`.
Only relevant if `ensembles` is defined. The key (e.g. `geogrid`) will be used as `SOURCE`.
* **`volfolder`:** Local folder for the `volfiles`.

**Common settings for both input options**
* **`response`:** Optional volume response to visualize initially.



```yaml
    - InplaceVolumes:
        csvfile: null # Optional, type str (corresponding to a path).
        ensembles: null # Optional, type list.
        volfiles: null # Optional, type dict.
        volfolder: "share/results/volumes" # Optional, type str.
        response: "STOIIP_OIL" # Optional, type str.
```

   

<!-- tab:Data input -->


?> The input files must follow FMU standards.

* [Example of an aggregated file for `csvfiles`](https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/volumes.csv).

* [Example of a file per realization that can be used with `ensembles` and `volfiles`](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/volumes/geogrid--oil.csv).

**The following columns will be used as available filters, if present:**

* `ZONE`
* `REGION`
* `FACIES`
* `LICENSE`
* `SOURCE` (relevant if calculations are done for multiple grids)


**Remaining columns are seen as volumetric responses.**

All names are allowed (except those mentioned above, in addition to `REAL` and `ENSEMBLE`), but the following responses are given more descriptive names automatically:

* `BULK_OIL`: Bulk Volume (Oil)
* `NET_OIL`: Net Volume (Oil)
* `PORE_OIL`: Pore Volume (Oil)
* `HCPV_OIL`: Hydro Carbon Pore Volume (Oil)
* `STOIIP_OIL`: Stock Tank Oil Initially In Place
* `BULK_GAS`: Bulk Volume (Gas)
* `NET_GAS`: Net Volume (Gas)
* `PORV_GAS`: Pore Volume (Gas)
* `HCPV_GAS`: Hydro Carbon Pore Volume (Gas)
* `GIIP_GAS`: Gas Initially In Place
* `RECOVERABLE_OIL`: Recoverable Volume (Oil)
* `RECOVERABLE_GAS`: Recoverable Volume (Gas)

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### InplaceVolumesOneByOne

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes inplace volumetrics related to a FMU ensemble with a design matrix.

Input can be given either as an aggregated `csv` file for volumes and sensitivity information,
or as ensemble name(s) defined in `shared_settings` and volumetric `csv` files
stored per realization.


 

<!-- tab:Arguments -->

   

* **`csvfile_vol`:** Aggregated csvfile for volumes with `REAL`, `ENSEMBLE` and `SOURCE` columns.
* **`csvfile_parameters`:** Aggregated csvfile of parameters for sensitivity information with   `REAL`, `ENSEMBLE`, `SENSNAME` and `SENSCASE` columns.
* **`ensembles`:** Which ensembles in `shared_settings` to visualize (not to be used with   `csvfile_vol` and `csvfile_parameters`).
* **`volfiles`:**  Key/value pair of csv files when using `ensembles`.   E.g. `{geogrid: geogrid--oil.csv}`.
* **`volfolder`:** Optional local folder for the `volfiles`.
* **`response`:** Optional volume response to visualize initially.



```yaml
    - InplaceVolumesOneByOne:
        csvfile_vol: null # Optional, type str (corresponding to a path).
        csvfile_parameters: null # Optional, type str (corresponding to a path).
        ensembles: null # Optional, type list.
        volfiles: null # Optional, type dict.
        volfolder: "share/results/volumes" # Optional, type str.
        response: "STOIIP_OIL" # Optional, type str.
```

   

<!-- tab:Data input -->

?> The input files must follow FMU standards.


**Volumetric input**

* [Example of an aggregated file for `csvfile_vol`](https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/volumes.csv).

* [Example of a file per realization that can be used with `ensembles` and `volfiles`](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/volumes/geogrid--oil.csv).

The following columns will be used as available filters, if present:

* `ZONE`
* `REGION`
* `FACIES`
* `LICENSE`
* `SOURCE` (relevant if calculations are done for multiple grids)


Remaining columns are seen as volumetric responses.

All names are allowed (except those mentioned above, in addition to `REAL` and `ENSEMBLE`), but the following responses are given more descriptive names automatically:

* `BULK_OIL`: Bulk Volume (Oil)
* `NET_OIL`: Net Volume (Oil)
* `PORE_OIL`: Pore Volume (Oil)
* `HCPV_OIL`: Hydro Carbon Pore Volume (Oil)
* `STOIIP_OIL`: Stock Tank Oil Initially In Place
* `BULK_GAS`: Bulk Volume (Gas)
* `NET_GAS`: Net Volume (Gas)
* `PORV_GAS`: Pore Volume (Gas)
* `HCPV_GAS`: Hydro Carbon Pore Volume (Gas)
* `GIIP_GAS`: Gas Initially In Place
* `RECOVERABLE_OIL`: Recoverable Volume (Oil)
* `RECOVERABLE_GAS`: Recoverable Volume (Gas)

**Sensitivity input**

The sensitivity information is extracted automatically if `ensembles` is given as input,
as long as `SENSCASE` and `SENSNAME` is found in `parameters.txt`.

An example of an aggregated file to use with `csvfile_parameters`
[can be found here](https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/parameters.csv)

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### MorrisPlot

<!-- tabs:start -->
   

<!-- tab:Description -->

Renders a visualization of the Morris sampling method.
The Morris method can be used to screen parameters for how they
influence model response, both individually and through interaction
effect with other parameters.


 

<!-- tab:Arguments -->

   

* **`csv_file`:** Input data on csv format.



```yaml
    - MorrisPlot:
        csv_file:  # Required, type str (corresponding to a path).
```

   

<!-- tab:Data input -->


[Example of input file](https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/morris.csv).

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### ParameterCorrelation

<!-- tabs:start -->
   

<!-- tab:Description -->

Shows parameter correlations using a correlation matrix,
and scatter plot for any given pair of parameters.


 

<!-- tab:Arguments -->

   

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`drop_constants`:** Drop constant parameters.



```yaml
    - ParameterCorrelation:
        ensembles:  # Required, type list.
        drop_constants: true # Optional, type bool.
```

   

<!-- tab:Data input -->

Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations of your defined `ensembles`, using the `fmu-ensemble` library.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### ParameterDistribution

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes parameter distributions for FMU ensembles.

Parameters are visualized either as histograms, showing parameter ranges
and distributions for each ensemble.

Input can be given either as an aggregated `csv` file with parameter information,
or as ensemble name(s) defined in `shared_settings`.


 

<!-- tab:Arguments -->

   

**Using aggregated data**
* **`csvfile`:** Aggregated `csv` file with `REAL`, `ENSEMBLE` and parameter columns.  (absolute path or relative to config file).

**Reading data from ensembles**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.



```yaml
    - ParameterDistribution:
        csvfile: null # Optional, type str (corresponding to a path).
        ensembles: null # Optional, type list.
```

   

<!-- tab:Data input -->

Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations if you have defined `ensembles`, using the `fmu-ensemble` library.

When using an aggregated `csvfile`, you need to have the columns `REAL`, `ENSEMBLE`
and the parameter columns.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### ParameterParallelCoordinates

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes parameters used in FMU ensembles side-by-side. Also supports response coloring.

Useful to investigate:
* Initial parameter distributions, and convergence of parameters over multiple iterations.
* Trends in relations between parameters and responses.

!> At least two parameters have to be selected to make the plot work.


 

<!-- tab:Arguments -->

   
**Three main options for input data: Aggregated, file per realization and read from UNSMRY.**

**Using aggregated data**
* **`parameter_csv`:** Aggregated csvfile for input parameters with `REAL` and `ENSEMBLE` columns (absolute path or relative to config file).
* **`response_csv`:** Aggregated csvfile for response parameters with `REAL` and `ENSEMBLE` columns (absolute path or relative to config file).


**Using a response file per realization**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`response_file`:** Local (per realization) csv file for response parameters (Cannot be                     combined with `response_csv` and `parameter_csv`).
* Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations of your defined `ensembles`, using the `fmu-ensemble` library.

**Using simulation time series data directly from `UNSMRY` files as responses**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize. The lack of `response_file`                 implies that the input data should be time series data from simulation `.UNSMRY`                 files, read using `fmu-ensemble`.
* **`column_keys`:** (Optional) slist of simulation vectors to include as responses when reading                 from UNSMRY-files in the defined ensembles (default is all vectors). * can be                 used as wild card.
* **`sampling`:** (Optional) sampling frequency when reading simulation data directly from                `.UNSMRY`-files (default is monthly).
* Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations of your defined `ensembles`, using the `fmu-ensemble` library.

?> The `UNSMRY` input method implies that the "DATE" vector will be used as a filter    of type `single` (as defined below under `response_filters`).

**Using the plugin without responses**
It is possible to use the plugin with only parameter data, in that case set the option `no_responses` to True, and give either `ensembles` or `parameter_csv` as input as described above. Response coloring and filtering will then not be available.

**Common settings for responses**
All of these are optional, some have defaults seen in the code snippet below.

* **`response_filters`:** Optional dictionary of responses (columns in csv file or simulation                        vectors) that can be used as row filtering before aggregation.                        Valid options:
    * `single`: Dropdown with single selection.
    * `multi`: Dropdown with multiple selection.
    * `range`: Slider with range selection.
* **`response_ignore`:** List of response (columns in csv or simulation vectors) to ignore                       (cannot use with response_include).
* **`response_include`:** List of response (columns in csv or simulation vectors) to include                        (cannot use with response_ignore).
* **`aggregation`:** How to aggregate responses per realization. Either `sum` or `mean`.

Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations of your defined `ensembles`, using the `fmu-ensemble` library.



```yaml
    - ParameterParallelCoordinates:
        ensembles: null # Optional, type list.
        parameter_csv: null # Optional, type str (corresponding to a path).
        response_csv: null # Optional, type str (corresponding to a path).
        response_file: null # Optional, type str.
        response_filters: null # Optional, type dict.
        response_ignore: null # Optional, type list.
        response_include: null # Optional, type list.
        parameter_ignore: null # Optional, type list.
        column_keys: null # Optional, type list.
        sampling: "monthly" # Optional, type str.
        aggregation: "sum" # Optional, type str.
        no_responses: false # Optional.
```

   

<!-- tab:Data input -->


?> Non-numerical (string-based) input parameters and responses are removed.

?> The responses will be aggregated per realization; meaning that if your filters do not reduce the response to a single value per realization in your data, the values will be aggregated accoording to your defined `aggregation`. If e.g. the response is a form of volume, and the filters are regions (or other subdivisions of the total volume), then `sum` would be a natural aggregation. If on the other hand the response is the pressures in the same volume, aggregation as `mean` over the subdivisions of the same volume would make more sense (though the pressures in this case would not be volume weighted means, and the aggregation would therefore likely be imprecise).

!> It is **strongly recommended** to keep the data frequency to a regular frequency (like `monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` (controlled by the `sampling` key). This is because the statistics are calculated per DATE over all realizations in an ensemble, and the available dates should therefore not differ between individual realizations of an ensemble.

**Using aggregated data**

The `parameter_csv` file must have columns `REAL`, `ENSEMBLE` and the parameter columns.

The `response_csv` file must have columns `REAL`, `ENSEMBLE` and the response columns (and the columns to use as `response_filters`, if that option is used).


**Using a response file per realization**

Parameters are extracted automatically from the `parameters.txt` files in the individual
realizations, using the `fmu-ensemble` library.

The `response_file` must have the response columns (and the columns to use as `response_filters`, if that option is used).


**Using simulation time series data directly from `UNSMRY` files as responses**

Parameters are extracted automatically from the `parameters.txt` files in the individual
realizations, using the `fmu-ensemble` library.

Responses are extracted automatically from the `UNSMRY` files in the individual realizations,
using the `fmu-ensemble` library.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the individual realizations. You should therefore not have more than one `UNSMRY` file in this folder, to avoid risk of not extracting the right data.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### ParameterResponseCorrelation

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes correlations between numerical input parameters and responses.


 

<!-- tab:Arguments -->

   
**Three main options for input data: Aggregated, file per realization and read from UNSMRY.**

**Using aggregated data**
* **`parameter_csv`:** Aggregated csvfile for input parameters with `REAL` and `ENSEMBLE` columns (absolute path or relative to config file).
* **`response_csv`:** Aggregated csvfile for response parameters with `REAL` and `ENSEMBLE` columns (absolute path or relative to config file).


**Using a response file per realization**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`response_file`:** Local (per realization) csv file for response parameters (Cannot be                     combined with `response_csv` and `parameter_csv`).


**Using simulation time series data directly from `UNSMRY` files as responses**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize. The lack of `response_file`                 implies that the input data should be time series data from simulation `.UNSMRY`                 files, read using `fmu-ensemble`.
* **`column_keys`:** (Optional) slist of simulation vectors to include as responses when reading                 from UNSMRY-files in the defined ensembles (default is all vectors). * can be                 used as wild card.
* **`sampling`:** (Optional) sampling frequency when reading simulation data directly from                `.UNSMRY`-files (default is monthly).

?> The `UNSMRY` input method implies that the "DATE" vector will be used as a filter    of type `single` (as defined below under `response_filters`).


**Common settings for all input options**

All of these are optional, some have defaults seen in the code snippet below.

* **`response_filters`:** Optional dictionary of responses (columns in csv file or simulation                        vectors) that can be used as row filtering before aggregation.                        Valid options:
    * `single`: Dropdown with single selection.
    * `multi`: Dropdown with multiple selection.
    * `range`: Slider with range selection.
* **`response_ignore`:** List of response (columns in csv or simulation vectors) to ignore                       (cannot use with response_include).
* **`response_include`:** List of response (columns in csv or simulation vectors) to include                        (cannot use with response_ignore).
* **`aggregation`:** How to aggregate responses per realization. Either `sum` or `mean`.
* **`corr_method`:** Correlation method. Either `pearson` or `spearman`.



```yaml
    - ParameterResponseCorrelation:
        parameter_csv: null # Optional, type str (corresponding to a path).
        response_csv: null # Optional, type str (corresponding to a path).
        ensembles: null # Optional, type list.
        response_file: null # Optional, type str.
        response_filters: null # Optional, type dict.
        response_ignore: null # Optional, type list.
        response_include: null # Optional, type list.
        column_keys: null # Optional, type list.
        sampling: "monthly" # Optional, type str.
        aggregation: "sum" # Optional, type str.
        corr_method: "pearson" # Optional, type str.
```

   

<!-- tab:Data input -->


?> Non-numerical (string-based) input parameters and responses are removed.

?> The responses will be aggregated per realization; meaning that if your filters do not reduce the response to a single value per realization in your data, the values will be aggregated accoording to your defined `aggregation`. If e.g. the response is a form of volume, and the filters are regions (or other subdivisions of the total volume), then `sum` would be a natural aggregation. If on the other hand the response is the pressures in the same volume, aggregation as `mean` over the subdivisions of the same volume would make more sense (though the pressures in this case would not be volume weighted means, and the aggregation would therefore likely be imprecise).

!> It is **strongly recommended** to keep the data frequency to a regular frequency (like `monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` (controlled by the `sampling` key). This is because the statistics are calculated per DATE over all realizations in an ensemble, and the available dates should therefore not differ between individual realizations of an ensemble.

**Using aggregated data**

The `parameter_csv` file must have columns `REAL`, `ENSEMBLE` and the parameter columns.

The `response_csv` file must have columns `REAL`, `ENSEMBLE` and the response columns (and the columns to use as `response_filters`, if that option is used).


**Using a response file per realization**

Parameters are extracted automatically from the `parameters.txt` files in the individual
realizations, using the `fmu-ensemble` library.

The `response_file` must have the response columns (and the columns to use as `response_filters`, if that option is used).


**Using simulation time series data directly from `UNSMRY` files as responses**

Parameters are extracted automatically from the `parameters.txt` files in the individual
realizations, using the `fmu-ensemble` library.

Responses are extracted automatically from the `UNSMRY` files in the individual realizations,
using the `fmu-ensemble` library.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the individual realizations. You should therefore not have more than one `UNSMRY` file in this folder, to avoid risk of not extracting the right data.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### PvtPlot

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes formation volume factor and viscosity data     for oil, gas and water from both **csv**, Eclipse **init** and **include** files.

!> The plugin supports variations in PVT between ensembles, but not between     realizations in the same ensemble.

 

<!-- tab:Arguments -->

   

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`pvt_relative_file_path`:** Local path to a csv file in each         realization with dumped pvt data.
* **`read_from_init_file`:** A boolean flag stating if data shall be         read from an Eclipse INIT file instead of an INCLUDE file.         This is only used when **pvt_relative_file_path** is not given.
* **`drop_ensemble_duplicates`:** A boolean flag stating if ensembles         which are holding duplicate data of other ensembles shall be dropped.         Defaults to False.



```yaml
    - PvtPlot:
        ensembles:  # Required, type List[str].
        pvt_relative_file_path: null # Optional, type str.
        read_from_init_file: false # Optional, type bool.
        drop_ensemble_duplicates: false # Optional, type bool.
```

   

<!-- tab:Data input -->

The minimum requirement is to define `ensembles`.

If no `pvt_relative_file_path` is given, the PVT data will be extracted automatically
from the simulation decks of individual realizations using `fmu_ensemble` and `ecl2df`.
If the `read_from_init_file` flag is set to True, the extraction procedure in
`ecl2df` will be replaced by an individual extracting procedure that reads the
normalized Eclipse INIT file.
Note that the latter two extraction methods can be very slow for larger data and are therefore
not recommended unless you have a very simple model/data deck.
If the `drop_ensemble_duplicates` flag is set to True, any ensembles which are holding
duplicate data of other ensembles will be dropped.

`pvt_relative_file_path` is a path to a file stored per realization (e.g. in     `share/results/tables/pvt.csv`). `pvt_relative_file_path` columns:
* One column named `KEYWORD` or `TYPE`: with Flow/Eclipse style keywords
    (e.g. `PVTO` and `PVDG`).
* One column named `PVTNUM` with integer `PVTNUM` regions.
* One column named `GOR` or `RS` with the gas-oil-ratio as the primary variate.
* One column named `PRESSURE` with the fluids pressure as the secondary variate.
* One column named `VOLUMEFACTOR` as the first covariate.
* One column named `VISCOSITY` as the second covariate.

The file can e.g. be dumped to disc per realization by a forward model in ERT using
`ecl2df`.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### RelativePermeability

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes relative permeability and capillary pressure curves for FMU ensembles.


 

<!-- tab:Arguments -->

   

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`relpermfile`:** Local path to a csvfile in each realization with dumped relperm data.
* **`scalfile`:** Path to a reference file with SCAL recommendationed data.     Path to a single file, **not** per realization/ensemble. The path can be absolute or     relative to the `webviz` configuration.
* **`sheet_name`:** Which sheet to use for the `scalfile`, only relevant if `scalfile` is an     `xlsx` file (recommended to use csv files with `webviz`).



```yaml
    - RelativePermeability:
        ensembles:  # Required, type list.
        relpermfile: null # Optional, type str.
        scalfile: null # Optional, type str (corresponding to a path).
        sheet_name: null # Optional, type Union[str, int, list, NoneType].
```

   

<!-- tab:Data input -->

The minimum requirement is to define `ensembles`.

If no `relpermfile` is defined, the relative permeability data will be extracted automatically
from the simulation decks of individual realizations using `fmu-ensemble`and `ecl2df` behind the
scenes. Note that this method can be very slow for larger data decks, and is therefore not
recommended unless you have a very simple model/data deck.

`relpermfile` is a path to a file stored per realization (e.g. in `share/results/tables/relperm.csv`). `relpermfile` columns:
* One column named `KEYWORD` or `TYPE`: with Flow/Eclipse style keywords (e.g. `SWOF` and `SGOF`).
* One column named `SATNUM` with integer `SATNUM` regions.
* One column **per** saturation (e.g. `SG` and `SW`).
* One column **per** relative permeability curve (e.g. `KRW`, `KROW` and `KRG`)
* One column **per** capillary pressure curve (e.g. `PCOW`).

The `relpermfile` file can e.g. be dumped to disk per realization by a forward model in ERT that
wraps the command `ecl2csv satfunc input_file -o output_file` (requires that you have `ecl2df`
installed). A typical example could be:
`ecl2csv satfunc eclipse/include/props/relperm.inc -o share/results/tables/relperm.csv`.
[Link to ecl2csv satfunc documentation.](https://equinor.github.io/ecl2df/scripts.html#satfunc)


`scalfile` is a path to __a single file of SCAL recommendations__ (for all
realizations/ensembles). The file has to be compatible with
[pyscal's](https://equinor.github.io/pyscal/pyscal.html#pyscal.factory.PyscalFactory.load_relperm_df) input format. Including this file adds reference cases
`Pess`, `Base` and `Opt` to the plots. This file is typically a result of a SCAL study.

`sheet_name` defines the sheet to use in the `scalfile`. Only relevant if `scalfile` is an
`xlsx` file (it is recommended to use `csv` and not `xlsx` for `Webviz`).

* [Example of relpermfile](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/tables/relperm.csv).
* [Example of scalfile](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/share/scal/scalreek.csv).

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### ReservoirSimulationTimeSeries

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes reservoir simulation time series data for FMU ensembles.

**Features**
* Visualization of realization time series as line charts.
* Visualization of ensemble time series statistics as fan charts.
* Visualization of single date ensemble statistics as histograms.
* Calculation and visualization of delta ensembles.
* Calculation and visualization of average rates and cumulatives over a specified time interval.
* Download of visualized data to csv files (except histogram data).


 

<!-- tab:Arguments -->

   
**Two main options for input data: Aggregated and read from UNSMRY.**

**Using aggregated data**
* **`csvfile`:** Aggregated csv file with `REAL`, `ENSEMBLE`,     `DATE` and vector columns.

**Using simulation time series data directly from `UNSMRY` files**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`column_keys`:** List of vectors to extract. If not given, all vectors     from the simulations will be extracted. Wild card asterisk `*` can be used.
* **`sampling`:** Time separation between extracted values. Can be e.g. `monthly` (default) or     `yearly`.

**Common optional settings for both input options**
* **`obsfile`**: File with observations to plot together with the relevant time series. (absolute path or relative to config file).
* **`options`:** Options to initialize plots with:
    * `vector1` : First vector to display
    * `vector2` : Second vector to display
    * `vector3` : Third vector to display
    * `visualization` : `realizations`, `statistics` or `statistics_hist`
    * `date` : Date to show in histograms
* **`line_shape_fallback`:** Fallback interpolation method between points. Vectors identified as     rates or phase ratios are always backfilled, vectors identified as cumulative (totals) are     always linearly interpolated. The rest use the fallback.
    Supported options:
    * `linear` (default)
    * `backfilled`
    * `hv`, `vh`, `hvh`, `vhv` and `spline` (regular Plotly options).



```yaml
    - ReservoirSimulationTimeSeries:
        csvfile: null # Optional, type str (corresponding to a path).
        ensembles: null # Optional, type list.
        obsfile: null # Optional, type str (corresponding to a path).
        column_keys: null # Optional, type list.
        sampling: "monthly" # Optional, type str.
        options: null # Optional, type dict.
        line_shape_fallback: "linear" # Optional, type str.
```

   

<!-- tab:Data input -->


?> Vectors that are identified as historical vectors (e.g. FOPTH is the history of FOPT) will be plotted together with their non-historical counterparts as reference lines, and they are therefore not selectable as vectors to plot initially.

?> The `obsfile` is a common (optional) file for all ensembles, which currently has to be made manually. [An example of the format can be found here](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/share/observations/observations.yml).

!> It is **strongly recommended** to keep the data frequency to a regular frequency (like `monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` (controlled by the `sampling` key). This is because the statistics and fancharts are calculated per DATE over all realizations in an ensemble, and the available dates should therefore not differ between individual realizations of an ensemble.

**Using aggregated data**

The `csvfile` must have columns `ENSEMBLE`, `REAL` and `DATE` in addition to the individual
vectors.
* [Example of aggregated file](https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/smry.csv).

**Using simulation time series data directly from `.UNSMRY` files**

Vectors are extracted automatically from the `UNSMRY` files in the individual realizations,
using the `fmu-ensemble` library.

?> Using the `UNSMRY` method will also extract metadata like units, and whether the vector is a rate, a cumulative, or historical. Units are e.g. added to the plot titles, while rates and cumulatives are used to decide the line shapes in the plot. Aggregated data may on the other speed up the build of the app, as processing of `UNSMRY` files can be slow for large models. Using this method is required to use the average rate and interval cumulative functionalities, as they require identification of vectors that are cumulatives.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the individual realizations. You should therefore not have more than one `UNSMRY` file in this folder, to avoid risk of not extracting the right data.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### ReservoirSimulationTimeSeriesOneByOne

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes reservoir simulation time series data for sensitivity studies based on a design matrix.

A tornado plot can be calculated interactively for each date/vector by selecting a date.
After selecting a date individual sensitivities can be selected to highlight the realizations
run with that sensitivity.


 

<!-- tab:Arguments -->

   
**Two main options for input data: Aggregated and read from UNSMRY.**

**Using aggregated data**
* **`csvfile_smry`:** Aggregated `csv` file for volumes with `REAL`, `ENSEMBLE`, `DATE` and     vector columns (absolute path or relative to config file).
* **`csvfile_parameters`:** Aggregated `csv` file for sensitivity information with `REAL`,     `ENSEMBLE`, `SENSNAME` and `SENSCASE` columns (absolute path or relative to config file).

**Using simulation time series data directly from `UNSMRY` files**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`column_keys`:** List of vectors to extract. If not given, all vectors     from the simulations will be extracted. Wild card asterisk `*` can be used.
* **`sampling`:** Time separation between extracted values. Can be e.g. `monthly` (default) or     `yearly`.

**Common optional settings for both input options**
* **`initial_vector`:** Initial vector to display
* **`line_shape_fallback`:** Fallback interpolation method between points. Vectors identified as     rates or phase ratios are always backfilled, vectors identified as cumulative (totals) are     always linearly interpolated. The rest use the fallback.
    Supported options:
    * `linear` (default)
    * `backfilled`
    * `hv`, `vh`, `hvh`, `vhv` and `spline` (regular Plotly options).



```yaml
    - ReservoirSimulationTimeSeriesOneByOne:
        csvfile_smry: null # Optional, type str (corresponding to a path).
        csvfile_parameters: null # Optional, type str (corresponding to a path).
        ensembles: null # Optional, type list.
        column_keys: null # Optional, type list.
        initial_vector: null # Optional.
        sampling: "monthly" # Optional, type str.
        line_shape_fallback: "linear" # Optional, type str.
```

   

<!-- tab:Data input -->

!> It is **strongly recommended** to keep the data frequency to a regular frequency (like `monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` (controlled by the `sampling` key). This is because the statistics and fancharts are calculated per DATE over all realizations in an ensemble, and the available dates should therefore not differ between individual realizations of an ensemble.


**Using aggregated data**

* [Example of csvfile_smry](https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/smry.csv).

* [Example of csvfile_parameters](https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/parameters.csv).


**Using simulation time series data directly from `.UNSMRY` files**

Time series data are extracted automatically from the `UNSMRY` files in the individual
realizations, using the `fmu-ensemble` library. The `SENSNAME` and `SENSCASE` values are read
directly from the `parameters.txt` files of the individual realizations, assuming that these
exist. If the `SENSCASE` of a realization is `p10_p90`, the sensitivity case is regarded as a
**Monte Carlo** style sensitivity, otherwise the case is evaluated as a **scalar** sensitivity.

?> Using the `UNSMRY` method will also extract metadata like units, and whether the vector is a rate, a cumulative, or historical. Units are e.g. added to the plot titles, while rates and cumulatives are used to decide the line shapes in the plot. Aggregated data may on the other speed up the build of the app, as processing of `UNSMRY` files can be slow for large models.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the individual realizations. You should therefore not have more than one `UNSMRY` file in this folder, to avoid risk of not extracting the right data.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### ReservoirSimulationTimeSeriesRegional

<!-- tabs:start -->
   

<!-- tab:Description -->

Aggregates and visualizes regional time series data from simulation ensembles. That
is: cumulatives, rates and inplace volumes. Allows human friendly filter names, e.g. regions,
zones and etc based on user input.

In addition recovery is calculated based on the changes in aggregated inplace volumes,
as long as all historical data is present in the data.

Example of aggregation of ROIP over regions in filter:

$$\sf Agg(\sf ROIP)_{\sf date} = \sum_{N\in \sf filter}\sf ROIP_{N,\sf date}$$

Example of recovery calculation for ROIP (where ROIP is already aggregated over the filtered
regions):

$$\sf Rec(\sf ROIP)_{\sf date} = \frac{\sf ROIP_{\sf init} - \sf ROIP_{\sf date}}{\sf ROIP_{\sf init}}$$


 

<!-- tab:Arguments -->

   

* **`ensembles`:** Which ensembles in `shared_settings` to include in the plugin.
* **`fipfile`:** Path to a yaml-file that defines a match between FIPXXX (e.g. FIPNUM) regions
    and human readable regions, zones and etc to be used as filters. If undefined, the FIPXXX     region numbers will be used for filtering (absolute path or relative to config file).
* **`initial_vector`:** First vector to plot (default is `ROIP` if it exists, otherwise first     found).
* **`column_keys`:** List of vectors to extract. If not given, all vectors     from the simulations will be extracted. Wild card asterisk `*` can be used.
Vectors that don't match the following patterns will be filtered out for this plugin:
    * `R[OGW]IP*` (regional in place),
    * `R[OGW][IP][RT]*` (regional injection and production rates and cumulatives)
* **`sampling`:** Time series data will be sampled (and interpolated) at this frequency. Options:
    * `daily`
    * `monthly` (default)
    * `yearly`
* **`line_shape_fallback`:** Fallback interpolation method between points. Vectors identified as     rates or phase ratios are always backfilled, vectors identified as cumulative (totals) are     always linearly interpolated. The rest use the fallback.
    Supported options:
    * `linear` (default)
    * `backfilled`
    * `hv`, `vh`, `hvh`, `vhv` and `spline` (regular Plotly options).



```yaml
    - ReservoirSimulationTimeSeriesRegional:
        ensembles:  # Required, type list.
        fipfile: null # Optional, type str (corresponding to a path).
        initial_vector: "ROIP" # Optional, type str.
        column_keys: null # Optional, type Union[list, NoneType].
        sampling: "monthly" # Optional, type str.
        line_shape_fallback: "linear" # Optional, type str.
```

   

<!-- tab:Data input -->

Vectors are extracted automatically from the `UNSMRY` files in the individual realizations,
using the `fmu-ensemble` library.

The `fipfile` is an optional user defined yaml-file to use for more human friendly filtering. If
undefined (either in general, or for the specific FIPXXX), the region numbers of FIPXXX will be
used as filters. If all region numbers for a filter value in `fipfile` are missing in the data,
this filter value will be silently ignored. E.g. if no vectors match 5 or 6 in
[this example file](https://github.com/equinor/webviz-subsurface-testdata/tree/master/reek_history_match/share/regions/fip.yaml), `ZONE` == `LowerReek` would be ignored in the plugin for `FIPNUM`. This
is to allow you to use the same file for e.g. a sector and a full field model.

?> To be able to calculate recoveries from inplace volumes, it is needed to ensure that the
inplace at the first time step actually is the initial inplace. It is therefore performed a check
at start-up of `FOPT`, `FGPT` and `FWPT` (at least one has to be present), if one of them is > 0
at the first DATE, a warning is written, and this ensemble will be excluded from recovery
calculations. For a restart run, an attempt is automatically made to find the history when
loading data, but this will unfortunately not work if the path to the restart case in the
simulation run is above 72 signs due to a file format limitation in the simulation metadata files.

?> `csv` input is currently not supported as the metadata aquired when reading from `UNSMRY`
is actively used to decide which vectors that can be used for recovery factors.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the
individual realizations. You should therefore not have more than one `UNSMRY` file in this
folder, to avoid risk of not extracting the right data.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### RftPlotter

<!-- tabs:start -->
   

<!-- tab:Description -->

This plugin visualizes simulated RFT results from
FMU ensembles combined with ERT observation data.

Several visualizations are available:

* Map view of RFT observations.

* Depth vs pressure plot showing simulated RFT data along wells together with observation points.

* Barchart showing sum of mean misfit for ERT observations per realization. One plot per ensemble.

* Crossplot of simulated RFT vs observed value per ERT observation. One plot per ensemble.

* Boxplot showing misfit per ERT observation for each ensemble.


 

<!-- tab:Arguments -->

   
**Using data per realization**

* **`ensembles`**: Which ensembles in `shared_settings` to visualize.

In addition, you need to have the following files in your realizations stored at the local path `share/results/tables`:

* **`rft.csv`**: A csv file containing simulated RFT data extracted from ECLIPSE RFT output files using [ecl2df](https://equinor.github.io/ecl2df/ecl2df.html#module-ecl2df.rft) [(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/tables/rft.csv).

* **`rft_ert.csv`**: A csv file containing simulated and observed RFT data for RFT observations defined in ERT [(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/tables/rft_ert.csv).


**Using aggregated data**

* **`csvfile_rft`**: Aggregated version of `rft.csv` [(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/rft.csv).
* **`csvfile_rft_ert`**: Aggregated version of `rft_ert.csv` [(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/rft_ert.csv).


**Optional input for both input options**

* **`obsdata`**: A csv file containing additional RFT observation data not defined in ERT for
visualization together with simulated RFT.
Mandatory column names: `WELL`, `DATE` (yyyy-mm-dd), `DEPTH` and `PRESSURE`

* **`formations`**: A csv file containing top and base values for each zone per well.
Used to visualize zone boundaries together with simulated RFT.
Mandatory column names: `WELL`, `ZONE`, `TOP_TVD`, `BASE_TVD` [(example file))](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/share/results/tables/formations.csv).

* **`faultlines`**: A csv file containing faultpolygons to be visualized together with the map view.
Export format from [xtgeo.xyz.polygons.dataframe](
https://xtgeo.readthedocs.io/en/latest/apiref/xtgeo.xyz.polygons.html#xtgeo.xyz.polygons.Polygons.dataframe
) [(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/share/results/polygons/faultpolygons.csv).



```yaml
    - RftPlotter:
        csvfile_rft: null # Optional, type str (corresponding to a path).
        csvfile_rft_ert: null # Optional, type str (corresponding to a path).
        ensembles: null # Optional, type list.
        formations: null # Optional, type str (corresponding to a path).
        obsdata: null # Optional, type str (corresponding to a path).
        faultlines: null # Optional, type str (corresponding to a path).
```

   

<!-- tab:Data input -->

?> Well name needs to be consistent with Eclipse well name.

?> Only RFT observations marked as active in ERT are used to generate plots.

?> Only TVD values are supported, plan to support MD values in a later release.

The `rft_ert.csv` file currently lacks a standardized method of generation. A **temporary** script can be found [here](https://github.com/equinor/webviz-subsurface-testdata/blob/b8b7f1fdd3abc505b137b587dcd9e44bbcf411c9/preprocessing_scripts/ert_rft.py).

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### RunningTimeAnalysisFMU

<!-- tabs:start -->
   

<!-- tab:Description -->

Can e.g. be used to investigate which jobs that are important for the running
time of realizations, and if specific parameter combinations increase running time or chance of
realization failure. Systematic realization failure could introduce bias to assisted history
matching.

Visualizations:
* Running time matrix, a heatmap of job running times relative to:
    * Same job in ensemble
    * Slowest job in ensemble
    * Slowest job in realization
* Parameter parallel coordinates plot:
    * Analyze running time and successful/failed run together with input parameters.


 

<!-- tab:Arguments -->

   

* **`ensembles`:** Which ensembles in `shared_settings` to include in check. Only required input.
* **`filter_shorter`:** Filters jobs with maximum run time in ensemble less than X seconds     (default: 10). Can be checked on/off interactively, this only sets the filtering value.
* **`status_file`:** Name of json file local per realization with job status     (default: `status.json`).
* **`visual_parameters`:** List of default visualized parameteres in parallel coordinates plot     (default: all parameters).



```yaml
    - RunningTimeAnalysisFMU:
        ensembles:  # Required, type list.
        filter_shorter: 10 # Optional, type Union[int, float].
        status_file: "status.json" # Optional, type str.
        visual_parameters: null # Optional, type Union[list, NoneType].
```

   

<!-- tab:Data input -->


Parameters are picked up automatically from `parameters.txt` in individual realizations in
defined ensembles using `fmu-ensemble`.

The `status.json` file is the standard status file when running
[`ERT`](https://github.com/Equinor/ert) runs. If defining a different name, it still has to be
on the same format [(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/status.json).

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### SegyViewer

<!-- tabs:start -->
   

<!-- tab:Description -->

Inspired by [SegyViewer for Python](https://github.com/equinor/segyviewer) this plugin
visualizes seismic 3D cubes with 3 plots (inline, crossline and zslice).
The plots are linked and updates are done by clicking in the plots.


 

<!-- tab:Arguments -->

   

* **`segyfiles`:** List of file paths to `SEGY` files (absolute or relative to config file).
* **`zunit`:** z-unit for display.
* **`colors`:** List of hex colors use. Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. `'#000000'` for black.



```yaml
    - SegyViewer:
        segyfiles:  # Required, type List[str (corresponding to a path)].
        zunit: "depth (m)" # Optional.
        colors: null # Optional, type list.
```

   

<!-- tab:Data input -->


* [Examples of segyfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/observed_data/seismic).

The segyfiles are on a `SEG-Y` format and can be investigated outside `webviz` using e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### SubsurfaceMap

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes reservoir grids in a map view, additionally it can
visualize the flow pattern in the simulation output using streamlines.
Input can be either a premade json object or data can be extracted from
a FMU ensemble.


 

<!-- tab:Arguments -->

   
**Two input options: Ensemble data or premade json file**

**json file**
* **`jsonfile`:** jsonfile with data, suitable for the corresponding [subsurface map component](https://github.com/equinor/webviz-subsurface-components)  (absolute path or relative to config file).

**Ensemble data**
* **`ensemble`:** Which ensemble in `shared_settings` to visualize (**just one**).
* **`map_value`:** Which property to show in the map (e.g. `PERMX`).
* **`flow_value`:** Which property to use for the streamlines animation
  (e.g. `FLOWAT`).
* **`time_step`:** Which report or time step to use in the simulation output.



```yaml
    - SubsurfaceMap:
        jsonfile: null # Optional, type str (corresponding to a path).
        ensemble: null # Optional, type str.
        map_value: null # Optional, type str.
        flow_value: null # Optional, type str.
        time_step: null # Optional.
```

   

<!-- tab:Data input -->


For ensemble data input, the key `FLORES` needs to be in the `RPTRST` keyword of the simulation
data deck for flow fields like `FLOWAT` and `FLOOIL` to be included in the data.

?> Using the ensemble method, the cell-by-cell mean values over all the grids in the ensemble are used, both for properties and flow fields. A consequence of this is that all the grids in the ensemble have to be equal (though the properties can vary), meaning that e.g. structural uncertainty unfortunately is not supported. Taking the cell-by-cell will also tend to give less property variations than you would see in a single realization. To look at a single realization you currently have to define a separate ensemble consisting of just a single realization.

!> Using the ensemble method, `UNRST` and `INIT` files are autodetected in the realizations under `eclipse/model`. You should therefore not have more than one of each of these files to make sure that you are reading the correct data.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### SurfaceViewerFMU

<!-- tabs:start -->
   

<!-- tab:Description -->

Covisualize surfaces from an ensemble.

There are 3 separate map views. 2 views can be set independently, while
the 3rd view displays the resulting map by combining the other maps, e.g.
by taking the difference or summing the values.

There is flexibility in which combinations of surfaces that are displayed
and calculated, such that surfaces can be compared across ensembles and realizations.

Statistical calculations across the ensemble(s) are
done on the fly. If the ensemble(s) or surfaces have a large size, it is recommended
to run webviz in `portable` mode so that the statistical surfaces are pre-calculated,
and available for instant viewing.


 

<!-- tab:Arguments -->

   

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`attributes`:** List of surface attributes to include, if not given
    all surface attributes will be included.
* **`attribute_settings`:** Dictionary with setting for each attribute.
    Available settings are:
    * `min`: Truncate colorscale (lower limit).
    * `max`: Truncate colorscale (upper limit).
    * `color`: Set the colormap (default is viridis).
    * `unit`: Text to display as unit in label.
* **`wellfolder`:** Folder with RMS wells.
* **`wellsuffix`:** File suffix for wells in well folder.



```yaml
    - SurfaceViewerFMU:
        ensembles:  # Required, type list.
        attributes: null # Optional, type list.
        attribute_settings: null # Optional, type dict.
        wellfolder: null # Optional, type str (corresponding to a path).
        wellsuffix: ".w" # Optional, type str.
```

   

<!-- tab:Data input -->

The available maps are gathered from the `share/results/maps/` folder
for each realization. Subfolders are not supported.

The filenames need to follow a fairly strict convention, as the filenames are used as metadata:
`horizon_name--attribute--date` (`--date` is optional). The files should be on `irap binary`
format (typically `.gri` or `.irapbin`) The date is of the form `YYYYMMDD` or
`YYYYMMDD_YYYYMMDD`, the latter would be for a delta surface between two dates.
See [this folder](https://github.com/equinor/webviz-subsurface-testdata/tree/master/reek_history_match/realization-0/iter-0/share/results/maps) for examples of file naming conventions.

The `attribute_settings` consists of optional settings for the individual attributes that are
extracted based on the filenames mentioned above. For attributes called `atr_a` and `atr_b`, the
configuration of `attribute_settings` could e.g. be:
```yaml
attribute_settings:
  atr_a:
    min: 4
    max: 10
    unit: m
  atr_b:
    color: rainbow
```
Valid options for `color` are `viridis` (default), `inferno`, `warm`, `cool` and `rainbow`.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### SurfaceWithGridCrossSection

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes surfaces in a map view and grid parameters in a cross section view. The cross section is defined by a polyline interactively edited in the map view.

!> This is an experimental plugin exploring how we can visualize 3D grid data in Webviz. The performance is currently slow for large grids.


 

<!-- tab:Arguments -->

   

* **`gridfile`:** Path to grid geometry (`ROFF` format) (absolute or relative to config file).
* **`gridparameterfiles`:** List of file paths to grid parameters (`ROFF` format)  (absolute or relative to config file).
* **`gridparameternames`:** List corresponding to filepaths of displayed parameter names.
* **`surfacefiles`:** List of file paths to surfaces (`irap binary` format)  (absolute or relative to config file).
* **`surfacenames`:** List corresponding to file paths of displayed surface names.
* **`zunit`:** z-unit for display.
* **`colors`:** List of hex colors to use. Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. `'#000000'` for black.



```yaml
    - SurfaceWithGridCrossSection:
        gridfile:  # Required, type str (corresponding to a path).
        gridparameterfiles:  # Required, type List[str (corresponding to a path)].
        surfacefiles:  # Required, type List[str (corresponding to a path)].
        gridparameternames: null # Optional, type list.
        surfacenames: null # Optional, type list.
        zunit: "depth (m)" # Optional.
        colors: null # Optional, type list.
```

   

<!-- tab:Data input -->

**Example files**

* [Gridfile](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/grids/geogrid.roff).
* [One file for gridparameterfiles](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/grids/geogrid--poro.roff).
* [One file for surfacefiles](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/maps/topupperreek--ds_extracted_horizons.gri).

The files above are on a `ROFF binary` format and can be investigated outside `webviz` using e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### SurfaceWithSeismicCrossSection

<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes surfaces in a map view and seismic in a cross section view.
The cross section is defined by a polyline interactively edited in the map view.


 

<!-- tab:Arguments -->

   

* **`segyfiles`:** List of file paths to SEG-Y files (absolute or relative to config file).
* **`segynames`:** Corresponding list of displayed seismic names.
* **`surfacefiles`:** List of file paths to Irap Binary surfaces (absolute or relative to config file).
* **`surfacenames`:** Corresponding list of displayed surface names.
* **`zunit`:** z-unit for display
* **`colors`:** List of hex colors to use. Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. `'#000000'` for black.



```yaml
    - SurfaceWithSeismicCrossSection:
        segyfiles:  # Required, type List[str (corresponding to a path)].
        surfacefiles:  # Required, type List[str (corresponding to a path)].
        surfacenames: null # Optional, type list.
        segynames: null # Optional, type list.
        zunit: "depth (m)" # Optional.
        colors: null # Optional, type list.
```

   

<!-- tab:Data input -->


**Example files**

* [Segyfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/observed_data/seismic).

* [One file for surfacefiles](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/maps/topupperreek--ds_extracted_horizons.gri).

The segyfiles are on a `SEG-Y` format and can be investigated outside `webviz` using e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

The surfacefiles are on a `ROFF binary` format and can be investigated outside `webviz` using e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### WellCrossSection

<!-- tabs:start -->
   

<!-- tab:Description -->

Displays a cross section along a well with intersected surfaces,
and optionally seismic cubes.

!> See also WellCrossSectionFMU for additional functionality with FMU ensembles.

 

<!-- tab:Arguments -->

   

* **`segyfiles`:** List of file paths to segyfiles (absolute or relative to config file).
* **`surfacefiles`:** List of file paths to Irap binary surfaces (absolute or relative to config file).
* **`surfacenames`:** Corresponding list of displayed surface names.
* **`wellfiles`:** List of file paths to RMS wells (absolute or relative to config file).
* **`zunit`:** z-unit for display.
* **`zonelog`:** Name of zonelog (for the RMS wells in `wellfiles`).
* **`zmin`:** Visualized minimum z-value in cross section.
* **`zmax`:** Visualized maximum z-value in cross section.
* **`zonemin`:** First zonenumber to draw in log.
* **`sampling`:** Sampling interval of well fence.
* **`nextend`:** Number of samples to extend well fence on each side of well, e.g. with distance of sampling=20 and nextend=2: extension=2*20 (nextend*sampling). 


```yaml
    - WellCrossSection:
        surfacefiles:  # Required, type List[str (corresponding to a path)].
        wellfiles:  # Required, type List[str (corresponding to a path)].
        segyfiles: null # Optional, type List[str (corresponding to a path)].
        surfacenames: null # Optional, type list.
        zonelog: null # Optional, type str.
        zunit: "depth (m)" # Optional.
        zmin: null # Optional, type float.
        zmax: null # Optional, type float.
        zonemin: 1 # Optional, type int.
        nextend: 2 # Optional, type int.
        sampling: 40 # Optional, type int.
```

   

<!-- tab:Data input -->


**Example files**

* [Segyfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/observed_data/seismic).

* [One file for surfacefiles](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/maps/topupperreek--ds_extracted_horizons.gri).

* [Wellfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/observed_data/wells).

The segyfiles are on a `SEG-Y` format and can be investigated outside `webviz` using e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

The surfacefiles are on a `ROFF binary` format and can be investigated outside `webviz` using e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### WellCrossSectionFMU

<!-- tabs:start -->
   

<!-- tab:Description -->

Well cross-section displaying statistical surfaces from a FMU ensemble.

Statistical surfaces are calculated automatically from surfaces stored
per realization.


 

<!-- tab:Arguments -->

   

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`surfacefiles`:** Surface file names (without folder).
* **`surfacenames`:** List corresponding to `surfacefiles` of displayed surface names.
* **`surfacefolder`:** Realization relative folder containing the `surfacefiles`.
* **`wellfiles`:** List of file paths to RMS wells (absolute or relative to config file).
* **`wellfolder`:** Alternative to `wellfiles`: provide a folder with RMS wells. (absolute or relative to config file).
* **`wellsuffix`:** File suffix for wells in `wellfolder`.
* **`segyfiles`:** List of file paths to `segyfiles` (absolute or relative to config file).
* **`zunit`:** z-unit for display.
* **`zonelog`:** Name of zonelog in `wellfiles` (displayed along well trajectory).
* **`marginal_logs`:** Logs in `wellfiles` to be displayed in separate horizontal plot.
* **`zmin`:** Visualized minimum z-value in cross section.
* **`zmax`:** Visualized maximum z-value in cross section.
* **`zonemin`:** First zonenumber to draw in zone log.
* **`sampling`:** Horizontal sampling interval.
* **`nextend`:** Number of samples to extend well fence on each side of well, e.g. `sampling=20` and `nextend=2` results in `extension=20*2`. * **`colors`:** List of hex colors corresponding to surfaces. Note that apostrophies     should be used to avoid that hex colors are read as comments. E.g. `'#000000'` for black.



```yaml
    - WellCrossSectionFMU:
        ensembles:  # Required, type list.
        surfacefiles:  # Required, type list.
        surfacenames: null # Optional, type list.
        surfacefolder: "share/results/maps" # Optional, type str (corresponding to a path).
        wellfiles: null # Optional, type List[str (corresponding to a path)].
        wellfolder: null # Optional, type str (corresponding to a path).
        wellsuffix: ".w" # Optional, type str.
        segyfiles: null # Optional, type List[str (corresponding to a path)].
        zonelog: null # Optional, type str.
        marginal_logs: null # Optional, type list.
        zunit: "depth (m)" # Optional.
        zmin: null # Optional, type float.
        zmax: null # Optional, type float.
        zonemin: 1 # Optional, type int.
        nextend: 2 # Optional, type int.
        sampling: 40 # Optional, type int.
        colors: null # Optional, type list.
```

   

<!-- tab:Data input -->


**Example files**

* [Segyfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/observed_data/seismic).

* [One file for surfacefiles](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/maps/topupperreek--ds_extracted_horizons.gri).

* [Wellfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/observed_data/wells).

The segyfiles are on a `SEG-Y` format and can be investigated outside `webviz` using e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

The surfacefiles are on a `ROFF binary` format and can be investigated outside `webviz` using e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

 

<!-- tabs:end -->

</div>

