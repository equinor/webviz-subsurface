# Plugin project webviz-subsurface

?> :bookmark: This documentation is valid for version `0.2.3rc0` of `webviz-subsurface`. 

   
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

#### AssistedHistoryMatchingAnalysis


<!-- tabs:start -->
   

<!-- tab:Description -->

Visualize parameter distribution change prior to posterior     per observation group in an assisted history matching process.
This is done by using a     [KS (Kolmogorov Smirnov) test](https://en.wikipedia.org/wiki/Kolmogorov%E2%80%93Smirnov_test)     matrix, and scatter plot/map for any given pair of parameter/observation.     KS values are between 0 and 1.     The closer to zero the KS value is, the smaller the change in parameter distribution     between prior/posterior and vice-versa.     The top 10 biggest parameters change are also shown in a table.


 

<!-- tab:Arguments -->


* **`input_dir`:** Path to the directory where the `csv` files created by the `AHM_ANALYSIS` ERT postprocess workflow are stored

*Required, type str (corresponding to a path)*


---

* **`ks_filter`:** optional argument to filter output to the data table based on ks value, only values above entered value will be displayed in the data table. This can be used if needed to speed-up vizualization of cases with high number of parameters and/or observations group. Default value is 0.0.

*default = 0.0, Optional, type float*


---



How to use in YAML config file:
```yaml
    - AssistedHistoryMatchingAnalysis:
        input_dir:  # Required, type str (corresponding to a path).
        ks_filter:  # Optional, type float.
```

   

<!-- tab:Data input -->



?> The input_dir      is where the results (csv files) from     the ERT `AHM_ANALYSIS` worflow are stored.
?> The ks_filter value should typically be between 0 and 0.5.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### BhpQc


<!-- tabs:start -->
   

<!-- tab:Description -->

QC simulated bottom hole pressures (BHP) from reservoir simulations.

Can be used to check if your simulated BHPs are in a realistic range.
E.g. check if your simulated bottom hole pressures are very low in producers,
or very high injectors.

 

<!-- tab:Arguments -->


* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

*Required, type list*


---

* **`wells`:** 

*default = null, Optional, type Union[typing.List[str], NoneType]*


---



How to use in YAML config file:
```yaml
    - BhpQc:
        ensembles:  # Required, type list.
        wells:  # Optional, type Union[typing.List[str], NoneType].
```

   

<!-- tab:Data input -->

Data is read directly from the UNSMRY files with the raw frequency (not resampled).
Resampling and csvs are not supported to avoid potential of interpolation, which
might cover extreme BHP values.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the     individual realizations. You should therefore not have more than one `UNSMRY` file in this     folder, to avoid risk of not extracting the right data.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### DiskUsage


<!-- tabs:start -->
   

<!-- tab:Description -->

Visualize disk usage in a FMU project. It adds a dashboard showing disk usage per user.


 

<!-- tab:Arguments -->


* **`scratch_dir`:** Path to the scratch directory to show disk usage for.

*Required, type str (corresponding to a path)*


---

* **`date`:** Date as string of form YYYY-MM-DD to request an explisit date. Default is to to use the most recent file avaialable, limited to the last week.

*default = null, Optional, type Union[_ForwardRef('str'), NoneType]*


---



How to use in YAML config file:
```yaml
    - DiskUsage:
        scratch_dir:  # Required, type str (corresponding to a path).
        date:  # Optional, type Union[_ForwardRef('str'), NoneType].
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

*Required, type List[str]*


---

* **`observation_file`:** Path to the observation `.yaml` file (absolute or relative to config file).

*Required, type str (corresponding to a path)*


---



How to use in YAML config file:
```yaml
    - HistoryMatch:
        ensembles:  # Required, type List[str].
        observation_file:  # Required, type str (corresponding to a path).
```

   

<!-- tab:Data input -->

Parameter values are extracted automatically from the `parameters.txt` files
of the individual realizations of your given `ensembles`, using the `fmu-ensemble` library.

?> The `observation_file` is a common (optional) file for all ensembles, which can be converted from e.g. ERT and ResInsight formats using the [fmuobs](https://equinor.github.io/subscript/scripts/fmuobs.html) script. [An example of the format can be found here](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/share/observations/observations.yml).

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### HorizonUncertaintyViewer

<details>
  <summary markdown="span"> :warning: Plugin 'HorizonUncertaintyViewer' has been deprecated.</summary>

  Relevant functionality is implemented in the StructuralUncertainty plugin.
</details>


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


* **`basedir`:** 

*Required, type str (corresponding to a path)*


---

* **`planned_wells_dir`:** 

*default = null, Optional, type str (corresponding to a path)*


---



How to use in YAML config file:
```yaml
    - HorizonUncertaintyViewer:
        basedir:  # Required, type str (corresponding to a path).
        planned_wells_dir:  # Optional, type str (corresponding to a path).
```

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### InplaceVolumes

<details>
  <summary markdown="span"> :warning: Plugin 'InplaceVolumes' has been deprecated.</summary>

  Relevant functionality is implemented in the VolumetricAnalysis plugin.
</details>


<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes inplace volumetric results from
FMU ensembles.

Input can be given either as aggregated `csv` files or as ensemble name(s)
defined in `shared_settings` (with volumetric `csv` files stored per realization).


 

<!-- tab:Arguments -->


* **`csvfile`:** Aggregated csvfile with `REAL`, `ENSEMBLE` and `SOURCE` columns (absolute path or relative to config file). **Using data stored per realization**

*default = null, Optional, type str (corresponding to a path)*


---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

*default = null, Optional, type list*


---

* **`volfiles`:** Key/value pair of csv files E.g. `{geogrid: geogrid--oil.csv}`. Only relevant if `ensembles` is defined. The key (e.g. `geogrid`) will be used as `SOURCE`.

*default = null, Optional, type dict*


---

* **`volfolder`:** Local folder for the `volfiles`. **Common settings for both input options**

*default = "share/results/volumes", Optional, type str*


---

* **`response`:** Optional volume response to visualize initially.

*default = "STOIIP_OIL", Optional, type str*


---



How to use in YAML config file:
```yaml
    - InplaceVolumes:
        csvfile:  # Optional, type str (corresponding to a path).
        ensembles:  # Optional, type list.
        volfiles:  # Optional, type dict.
        volfolder:  # Optional, type str.
        response:  # Optional, type str.
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

*default = null, Optional, type str (corresponding to a path)*


---

* **`csvfile_parameters`:** Aggregated csvfile of parameters for sensitivity information with `REAL`, `ENSEMBLE`, `SENSNAME` and `SENSCASE` columns.

*default = null, Optional, type str (corresponding to a path)*


---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize (not to be used with `csvfile_vol` and `csvfile_parameters`).

*default = null, Optional, type list*


---

* **`volfiles`:** Key/value pair of csv files when using `ensembles`. E.g. `{geogrid: geogrid--oil.csv}`.

*default = null, Optional, type dict*


---

* **`volfolder`:** Optional local folder for the `volfiles`.

*default = "share/results/volumes", Optional, type str*


---

* **`response`:** Optional volume response to visualize initially.

*default = "STOIIP_OIL", Optional, type str*


---



How to use in YAML config file:
```yaml
    - InplaceVolumesOneByOne:
        csvfile_vol:  # Optional, type str (corresponding to a path).
        csvfile_parameters:  # Optional, type str (corresponding to a path).
        ensembles:  # Optional, type list.
        volfiles:  # Optional, type dict.
        volfolder:  # Optional, type str.
        response:  # Optional, type str.
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

#### LinePlotterFMU


<!-- tabs:start -->
   

<!-- tab:Description -->

General line plotter for FMU data


 

<!-- tab:Arguments -->


* **`csvfile`:** Relative path to Csv file stored per realization

*default = null, Optional, type str*


---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

*default = null, Optional, type list*


---

* **`aggregated_csvfile`:** 

*default = null, Optional, type str (corresponding to a path)*


---

* **`aggregated_parameterfile`:** 

*default = null, Optional, type str (corresponding to a path)*


---

* **`observation_file`:** Yaml file with observations

*default = null, Optional, type str (corresponding to a path)*


---

* **`observation_group`:** Top-level key in observation file.

*default = "general", Optional, type str*


---

* **`remap_observation_keys`:** Remap observation keys to columns in csv file

*default = null, Optional, type Dict[str, str]*


---

* **`remap_observation_values`:** Remap observation values to columns in csv file

*default = null, Optional, type Dict[str, str]*


---

* **`colors`:** Set colors for each ensemble

*default = null, Optional, type Dict*


---

* **`initial_data`:** Initialize data selectors (x,y,ensemble, parameter)

*default = null, Optional, type Dict*


---

* **`initial_layout`:** Initialize plot layout (x and y axis direction and type)

*default = null, Optional, type Dict*


---



How to use in YAML config file:
```yaml
    - LinePlotterFMU:
        csvfile:  # Optional, type str.
        ensembles:  # Optional, type list.
        aggregated_csvfile:  # Optional, type str (corresponding to a path).
        aggregated_parameterfile:  # Optional, type str (corresponding to a path).
        observation_file:  # Optional, type str (corresponding to a path).
        observation_group:  # Optional, type str.
        remap_observation_keys:  # Optional, type Dict[str, str].
        remap_observation_values:  # Optional, type Dict[str, str].
        colors:  # Optional, type Dict.
        initial_data:  # Optional, type Dict.
        initial_layout:  # Optional, type Dict.
```

 

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

*Required, type str (corresponding to a path)*


---



How to use in YAML config file:
```yaml
    - MorrisPlot:
        csv_file:  # Required, type str (corresponding to a path).
```

   

<!-- tab:Data input -->


[Example of input file](https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/morris.csv).

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### ParameterAnalysis


<!-- tabs:start -->
   

<!-- tab:Description -->

This plugin visualizes parameter distributions and statistics. /
    for FMU ensembles, and can be used to investigate parameter correlations /
    on reservoir simulation time series data.


 

<!-- tab:Arguments -->


* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

*default = null, Optional, type Union[list, NoneType]*


---

* **`csvfile_parameters`:** Aggregated `csv` file with `REAL`, `ENSEMBLE` and parameter columns. (absolute path or relative to config file).

*default = null, Optional, type str (corresponding to a path)*


---

* **`csvfile_smry`:** (Optional) Aggregated `csv` file for volumes with `REAL`, `ENSEMBLE`, `DATE` and vector columns (absolute path or relative to config file). **Using raw ensemble data stored in realization folders**

*default = null, Optional, type str (corresponding to a path)*


---

* **`time_index`:** Time separation between extracted values. Can be e.g. `monthly` (default) or `yearly`. **Common settings for all input options**

*default = "monthly", Optional, type str*


---

* **`column_keys`:** List of vectors to extract. If not given, all vectors from the simulations will be extracted. Wild card asterisk `*` can be used.

*default = null, Optional, type Union[list, NoneType]*


---

* **`drop_constants`:** Bool used to determine if constant parameters should be dropped. Default is True.

*default = true, Optional, type bool*


---



How to use in YAML config file:
```yaml
    - ParameterAnalysis:
        ensembles:  # Optional, type Union[list, NoneType].
        csvfile_parameters:  # Optional, type str (corresponding to a path).
        csvfile_smry:  # Optional, type str (corresponding to a path).
        time_index:  # Optional, type str.
        column_keys:  # Optional, type Union[list, NoneType].
        drop_constants:  # Optional, type bool.
```

   

<!-- tab:Data input -->


!> For smry data it is **strongly recommended** to keep the data frequency to a regular frequency (like `monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` (controlled by the `sampling` key). This is because the statistics and fancharts are calculated per DATE over all realizations in an ensemble, and the available dates should therefore not differ between individual realizations of an ensemble.

?> Vectors that are identified as historical vectors (e.g. FOPTH is the history of FOPT) will be plotted together with their non-historical counterparts as reference lines.

**Using simulation time series data directly from `.UNSMRY` files**

!> Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations if you have defined `ensembles`, using the `fmu-ensemble` library.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the individual realizations. You should therefore not have more than one `UNSMRY` file in this folder, to avoid risk of not extracting the right data.

**Using aggregated data**

?> Aggregated data may speed up the build of the app, as processing of `UNSMRY` files can be slow for large models.

 

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

*Required, type list*


---

* **`drop_constants`:** Drop constant parameters.

*default = true, Optional, type bool*


---



How to use in YAML config file:
```yaml
    - ParameterCorrelation:
        ensembles:  # Required, type list.
        drop_constants:  # Optional, type bool.
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


* **`csvfile`:** Aggregated `csv` file with `REAL`, `ENSEMBLE` and parameter columns. (absolute path or relative to config file). **Reading data from ensembles**

*default = null, Optional, type str (corresponding to a path)*


---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

*default = null, Optional, type list*


---



How to use in YAML config file:
```yaml
    - ParameterDistribution:
        csvfile:  # Optional, type str (corresponding to a path).
        ensembles:  # Optional, type list.
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


* **`ensembles`:** Which ensembles in `shared_settings` to visualize. The lack of `response_file` implies that the input data should be time series data from simulation `.UNSMRY` files, read using `fmu-ensemble`.

*default = null, Optional, type list*


---

* **`parameter_csv`:** Aggregated csvfile for input parameters with `REAL` and `ENSEMBLE` columns (absolute path or relative to config file).

*default = null, Optional, type str (corresponding to a path)*


---

* **`response_csv`:** Aggregated csvfile for response parameters with `REAL` and `ENSEMBLE` columns (absolute path or relative to config file). **Using a response file per realization**

*default = null, Optional, type str (corresponding to a path)*


---

* **`response_file`:** Local (per realization) csv file for response parameters (Cannot be combined with `response_csv` and `parameter_csv`). * Parameter values are extracted automatically from the `parameters.txt` files in the individual realizations of your defined `ensembles`, using the `fmu-ensemble` library. **Using simulation time series data directly from `UNSMRY` files as responses**

*default = null, Optional, type str*


---

* **`response_filters`:** Optional dictionary of responses (columns in csv file or simulation vectors) that can be used as row filtering before aggregation. Valid options: * `single`: Dropdown with single selection. * `multi`: Dropdown with multiple selection. * `range`: Slider with range selection.

*default = null, Optional, type dict*


---

* **`response_ignore`:** List of response (columns in csv or simulation vectors) to ignore (cannot use with response_include).

*default = null, Optional, type list*


---

* **`response_include`:** List of response (columns in csv or simulation vectors) to include (cannot use with response_ignore).

*default = null, Optional, type list*


---

* **`parameter_ignore`:** 

*default = null, Optional, type list*


---

* **`column_keys`:** (Optional) slist of simulation vectors to include as responses when reading from UNSMRY-files in the defined ensembles (default is all vectors). * can be used as wild card.

*default = null, Optional, type list*


---

* **`sampling`:** (Optional) sampling frequency when reading simulation data directly from `.UNSMRY`-files (default is monthly). * Parameter values are extracted automatically from the `parameters.txt` files in the individual realizations of your defined `ensembles`, using the `fmu-ensemble` library. ?> The `UNSMRY` input method implies that the "DATE" vector will be used as a filter of type `single` (as defined below under `response_filters`). **Using the plugin without responses** It is possible to use the plugin with only parameter data, in that case set the option `no_responses` to True, and give either `ensembles` or `parameter_csv` as input as described above. Response coloring and filtering will then not be available. **Common settings for responses** All of these are optional, some have defaults seen in the code snippet below.

*default = "monthly", Optional, type str*


---

* **`aggregation`:** How to aggregate responses per realization. Either `sum` or `mean`. Parameter values are extracted automatically from the `parameters.txt` files in the individual realizations of your defined `ensembles`, using the `fmu-ensemble` library.

*default = "sum", Optional, type str*


---

* **`no_responses`:** 

*default = false, Optional*


---



How to use in YAML config file:
```yaml
    - ParameterParallelCoordinates:
        ensembles:  # Optional, type list.
        parameter_csv:  # Optional, type str (corresponding to a path).
        response_csv:  # Optional, type str (corresponding to a path).
        response_file:  # Optional, type str.
        response_filters:  # Optional, type dict.
        response_ignore:  # Optional, type list.
        response_include:  # Optional, type list.
        parameter_ignore:  # Optional, type list.
        column_keys:  # Optional, type list.
        sampling:  # Optional, type str.
        aggregation:  # Optional, type str.
        no_responses:  # Optional.
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


* **`parameter_csv`:** Aggregated csvfile for input parameters with `REAL` and `ENSEMBLE` columns (absolute path or relative to config file).

*default = null, Optional, type str (corresponding to a path)*


---

* **`response_csv`:** Aggregated csvfile for response parameters with `REAL` and `ENSEMBLE` columns (absolute path or relative to config file). **Using a response file per realization**

*default = null, Optional, type str (corresponding to a path)*


---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize. The lack of `response_file` implies that the input data should be time series data from simulation `.UNSMRY` files, read using `fmu-ensemble`.

*default = null, Optional, type list*


---

* **`response_file`:** Local (per realization) csv file for response parameters (Cannot be combined with `response_csv` and `parameter_csv`). **Using simulation time series data directly from `UNSMRY` files as responses**

*default = null, Optional, type str*


---

* **`response_filters`:** Optional dictionary of responses (columns in csv file or simulation vectors) that can be used as row filtering before aggregation. Valid options: * `single`: Dropdown with single selection. * `multi`: Dropdown with multiple selection. * `range`: Slider with range selection.

*default = null, Optional, type dict*


---

* **`response_ignore`:** List of response (columns in csv or simulation vectors) to ignore (cannot use with response_include).

*default = null, Optional, type list*


---

* **`response_include`:** List of response (columns in csv or simulation vectors) to include (cannot use with response_ignore).

*default = null, Optional, type list*


---

* **`column_keys`:** (Optional) slist of simulation vectors to include as responses when reading from UNSMRY-files in the defined ensembles (default is all vectors). * can be used as wild card.

*default = null, Optional, type list*


---

* **`sampling`:** (Optional) sampling frequency when reading simulation data directly from `.UNSMRY`-files (default is monthly). ?> The `UNSMRY` input method implies that the "DATE" vector will be used as a filter of type `single` (as defined below under `response_filters`). **Common settings for all input options** All of these are optional, some have defaults seen in the code snippet below.

*default = "monthly", Optional, type str*


---

* **`aggregation`:** How to aggregate responses per realization. Either `sum` or `mean`.

*default = "sum", Optional, type str*


---

* **`corr_method`:** Correlation method. Either `pearson` or `spearman`.

*default = "pearson", Optional, type str*


---



How to use in YAML config file:
```yaml
    - ParameterResponseCorrelation:
        parameter_csv:  # Optional, type str (corresponding to a path).
        response_csv:  # Optional, type str (corresponding to a path).
        ensembles:  # Optional, type list.
        response_file:  # Optional, type str.
        response_filters:  # Optional, type dict.
        response_ignore:  # Optional, type list.
        response_include:  # Optional, type list.
        column_keys:  # Optional, type list.
        sampling:  # Optional, type str.
        aggregation:  # Optional, type str.
        corr_method:  # Optional, type str.
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

#### PropertyStatistics


<!-- tabs:start -->
   

<!-- tab:Description -->

This plugin visualizes ensemble statistics calculated from grid properties.


 

<!-- tab:Arguments -->


* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

*default = null, Optional, type Union[list, NoneType]*


---

* **`statistics_file`:** 

*default = "share/results/tables/gridpropstatistics.csv", Optional, type str*


---

* **`csvfile_statistics`:** Aggregated `csv` file for property statistics. See the documentation in [fmu-tools](http://fmu-docs.equinor.com/) on how to generate this data. **Using raw ensemble data stored in realization folders**

*default = null, Optional, type str (corresponding to a path)*


---

* **`csvfile_smry`:** Aggregated `csv` file for volumes with `REAL`, `ENSEMBLE`, `DATE` and vector columns (absolute path or relative to config file).

*default = null, Optional, type str (corresponding to a path)*


---

* **`surface_renaming`:** Optional dictionary to rename properties/zones to match filenames stored on FMU standardized format (zone--property.gri)

*default = null, Optional, type Union[dict, NoneType]*


---

* **`time_index`:** Time separation between extracted values. Can be e.g. `monthly` (default) or `yearly`.

*default = "monthly", Optional, type str*


---

* **`column_keys`:** List of vectors to extract. If not given, all vectors from the simulations will be extracted. Wild card asterisk `*` can be used.

*default = null, Optional, type Union[list, NoneType]*


---



How to use in YAML config file:
```yaml
    - PropertyStatistics:
        ensembles:  # Optional, type Union[list, NoneType].
        statistics_file:  # Optional, type str.
        csvfile_statistics:  # Optional, type str (corresponding to a path).
        csvfile_smry:  # Optional, type str (corresponding to a path).
        surface_renaming:  # Optional, type Union[dict, NoneType].
        time_index:  # Optional, type str.
        column_keys:  # Optional, type Union[list, NoneType].
```

   

<!-- tab:Data input -->


?> Folders with statistical surfaces are assumed located at `<ensemble_path>/share/results/maps/<ensemble>/<statistic>` where `statistic` are subfolders with statistical calculation: `mean`, `stddev`, `p10`, `p90`, `min`, `max`.

!> Surface data is currently not available when using aggregated files.

!> For smry data it is **strongly recommended** to keep the data frequency to a regular frequency (like `monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` (controlled by the `sampling` key). This is because the statistics and fancharts are calculated per DATE over all realizations in an ensemble, and the available dates should therefore not differ between individual realizations of an ensemble.


**Using aggregated data**


**Using simulation time series data directly from `.UNSMRY` files**

Time series data are extracted automatically from the `UNSMRY` files in the individual
realizations, using the `fmu-ensemble` library.

?> Using the `UNSMRY` method will also extract metadata like units, and whether the vector is a rate, a cumulative, or historical. Units are e.g. added to the plot titles, while rates and cumulatives are used to decide the line shapes in the plot. Aggregated data may on the other speed up the build of the app, as processing of `UNSMRY` files can be slow for large models.

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

*Required, type List[str]*


---

* **`pvt_relative_file_path`:** Local path to a csv file in each realization with dumped pvt data.

*default = null, Optional, type str*


---

* **`read_from_init_file`:** A boolean flag stating if data shall be read from an Eclipse INIT file instead of an INCLUDE file. This is only used when **pvt_relative_file_path** is not given.

*default = false, Optional, type bool*


---

* **`drop_ensemble_duplicates`:** A boolean flag stating if ensembles which are holding duplicate data of other ensembles shall be dropped. Defaults to False.

*default = false, Optional, type bool*


---



How to use in YAML config file:
```yaml
    - PvtPlot:
        ensembles:  # Required, type List[str].
        pvt_relative_file_path:  # Optional, type str.
        read_from_init_file:  # Optional, type bool.
        drop_ensemble_duplicates:  # Optional, type bool.
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
* One column named `RATIO` or `R` with the gas-oil-ratio as the primary variate.
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

*Required, type list*


---

* **`relpermfile`:** Local path to a csvfile in each realization with dumped relperm data.

*default = null, Optional, type str*


---

* **`scalfile`:** Path to a reference file with SCAL recommendationed data. Path to a single file, **not** per realization/ensemble. The path can be absolute or relative to the `webviz` configuration.

*default = null, Optional, type str (corresponding to a path)*


---

* **`sheet_name`:** Which sheet to use for the `scalfile`, only relevant if `scalfile` is an `xlsx` file (recommended to use csv files with `webviz`).

*default = null, Optional, type Union[str, int, list, NoneType]*


---



How to use in YAML config file:
```yaml
    - RelativePermeability:
        ensembles:  # Required, type list.
        relpermfile:  # Optional, type str.
        scalfile:  # Optional, type str (corresponding to a path).
        sheet_name:  # Optional, type Union[str, int, list, NoneType].
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
* Visualization of ensemble time series statistics as line or fan charts.
* Visualization of single date ensemble statistics as histograms.
* Calculation and visualization of delta ensembles.
* Calculation and visualization of average rates and cumulatives over a specified time interval.
* Download of visualized data to csv files (except histogram data).


 

<!-- tab:Arguments -->


* **`csvfile`:** Aggregated csv file with `REAL`, `ENSEMBLE`, `DATE` and vector columns. **Using simulation time series data directly from `UNSMRY` files**

*default = null, Optional, type str (corresponding to a path)*


---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

*default = null, Optional, type list*


---

* **`obsfile`:** 

*default = null, Optional, type str (corresponding to a path)*


---

* **`column_keys`:** List of vectors to extract. If not given, all vectors from the simulations will be extracted. Wild card asterisk `*` can be used.

*default = null, Optional, type list*


---

* **`sampling`:** Time separation between extracted values. Can be e.g. `monthly` (default) or `yearly`. **Common optional settings for both input options** * **`obsfile`**: File with observations to plot together with the relevant time series. (absolute path or relative to config file).

*default = "monthly", Optional, type str*


---

* **`options`:** Options to initialize plots with: * `vector1` : First vector to display * `vector2` : Second vector to display * `vector3` : Third vector to display * `visualization` : `realizations`, `statistics` or `fanchart` * `date` : Date to show by default in histograms

*default = null, Optional, type dict*


---

* **`line_shape_fallback`:** Fallback interpolation method between points. Vectors identified as rates or phase ratios are always backfilled, vectors identified as cumulative (totals) are always linearly interpolated. The rest use the fallback. Supported options: * `linear` (default) * `backfilled` * `hv`, `vh`, `hvh`, `vhv` and `spline` (regular Plotly options).

*default = "linear", Optional, type str*


---



How to use in YAML config file:
```yaml
    - ReservoirSimulationTimeSeries:
        csvfile:  # Optional, type str (corresponding to a path).
        ensembles:  # Optional, type list.
        obsfile:  # Optional, type str (corresponding to a path).
        column_keys:  # Optional, type list.
        sampling:  # Optional, type str.
        options:  # Optional, type dict.
        line_shape_fallback:  # Optional, type str.
```

   

<!-- tab:Data input -->


?> Vectors that are identified as historical vectors (e.g. FOPTH is the history of FOPT) will be plotted together with their non-historical counterparts as reference lines, and they are therefore not selectable as vectors to plot initially.

?> The `obsfile` is a common (optional) file for all ensembles, which can be converted from e.g. ERT and ResInsight formats using the [fmuobs](https://equinor.github.io/subscript/scripts/fmuobs.html) script. [An example of the format can be found here](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/share/observations/observations.yml).

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


* **`csvfile_smry`:** Aggregated `csv` file for volumes with `REAL`, `ENSEMBLE`, `DATE` and vector columns (absolute path or relative to config file).

*default = null, Optional, type str (corresponding to a path)*


---

* **`csvfile_parameters`:** Aggregated `csv` file for sensitivity information with `REAL`, `ENSEMBLE`, `SENSNAME` and `SENSCASE` columns (absolute path or relative to config file). **Using simulation time series data directly from `UNSMRY` files**

*default = null, Optional, type str (corresponding to a path)*


---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

*default = null, Optional, type list*


---

* **`column_keys`:** List of vectors to extract. If not given, all vectors from the simulations will be extracted. Wild card asterisk `*` can be used.

*default = null, Optional, type list*


---

* **`initial_vector`:** Initial vector to display

*default = null, Optional, type str*


---

* **`sampling`:** Time separation between extracted values. Can be e.g. `monthly` (default) or `yearly`. **Common optional settings for both input options**

*default = "monthly", Optional, type str*


---

* **`line_shape_fallback`:** Fallback interpolation method between points. Vectors identified as rates or phase ratios are always backfilled, vectors identified as cumulative (totals) are always linearly interpolated. The rest use the fallback. Supported options: * `linear` (default) * `backfilled` * `hv`, `vh`, `hvh`, `vhv` and `spline` (regular Plotly options).

*default = "linear", Optional, type str*


---



How to use in YAML config file:
```yaml
    - ReservoirSimulationTimeSeriesOneByOne:
        csvfile_smry:  # Optional, type str (corresponding to a path).
        csvfile_parameters:  # Optional, type str (corresponding to a path).
        ensembles:  # Optional, type list.
        column_keys:  # Optional, type list.
        initial_vector:  # Optional, type str.
        sampling:  # Optional, type str.
        line_shape_fallback:  # Optional, type str.
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

*Required, type list*


---

* **`fipfile`:** Path to a yaml-file that defines a match between FIPXXX (e.g. FIPNUM) regions and human readable regions, zones and etc to be used as filters. If undefined, the FIPXXX region numbers will be used for filtering (absolute path or relative to config file).

*default = null, Optional, type str (corresponding to a path)*


---

* **`initial_vector`:** First vector to plot (default is `ROIP` if it exists, otherwise first found).

*default = "ROIP", Optional, type str*


---

* **`column_keys`:** List of vectors to extract. If not given, all vectors from the simulations will be extracted. Wild card asterisk `*` can be used. Vectors that don't match the following patterns will be filtered out for this plugin: * `R[OGW]IP*` (regional in place), * `R[OGW][IP][RT]*` (regional injection and production rates and cumulatives)

*default = null, Optional, type Union[list, NoneType]*


---

* **`sampling`:** Time series data will be sampled (and interpolated) at this frequency. Options: * `daily` * `monthly` (default) * `yearly`

*default = "monthly", Optional, type str*


---

* **`line_shape_fallback`:** Fallback interpolation method between points. Vectors identified as rates or phase ratios are always backfilled, vectors identified as cumulative (totals) are always linearly interpolated. The rest use the fallback. Supported options: * `linear` (default) * `backfilled` * `hv`, `vh`, `hvh`, `vhv` and `spline` (regular Plotly options).

*default = "linear", Optional, type str*


---



How to use in YAML config file:
```yaml
    - ReservoirSimulationTimeSeriesRegional:
        ensembles:  # Required, type list.
        fipfile:  # Optional, type str (corresponding to a path).
        initial_vector:  # Optional, type str.
        column_keys:  # Optional, type Union[list, NoneType].
        sampling:  # Optional, type str.
        line_shape_fallback:  # Optional, type str.
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


* **`csvfile_rft`:** 

*default = null, Optional, type str (corresponding to a path)*


---

* **`csvfile_rft_ert`:** 

*default = null, Optional, type str (corresponding to a path)*


---

* **`ensembles`:** 

*default = null, Optional, type Union[typing.List[str], NoneType]*


---

* **`formations`:** 

*default = null, Optional, type str (corresponding to a path)*


---

* **`obsdata`:** 

*default = null, Optional, type str (corresponding to a path)*


---

* **`faultlines`:** 

*default = null, Optional, type str (corresponding to a path)*


---



How to use in YAML config file:
```yaml
    - RftPlotter:
        csvfile_rft:  # Optional, type str (corresponding to a path).
        csvfile_rft_ert:  # Optional, type str (corresponding to a path).
        ensembles:  # Optional, type Union[typing.List[str], NoneType].
        formations:  # Optional, type str (corresponding to a path).
        obsdata:  # Optional, type str (corresponding to a path).
        faultlines:  # Optional, type str (corresponding to a path).
```

   

<!-- tab:Data input -->

?> Well name needs to be consistent with Eclipse well name.

?> Only RFT observations marked as active in ERT are used to generate plots.

The `rft_ert.csv` file can be generated by running the "MERGE_RFT_ERTOBS" forward model in ERT, this will collect ERT RFT observations and merge with CSV output from the "GENDATA_RFT" forward model. [ERT docs](https://fmu-docs.equinor.com/docs/ert/reference/forward_models.html?highlight=gendata_rft#MERGE_RFT_ERTOBS).

 

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

*Required, type list*


---

* **`filter_shorter`:** Filters jobs with maximum run time in ensemble less than X seconds (default: 10). Can be checked on/off interactively, this only sets the filtering value.

*default = 10, Optional, type Union[int, float]*


---

* **`status_file`:** Name of json file local per realization with job status (default: `status.json`).

*default = "status.json", Optional, type str*


---

* **`visual_parameters`:** List of default visualized parameteres in parallel coordinates plot (default: all parameters).

*default = null, Optional, type Union[list, NoneType]*


---



How to use in YAML config file:
```yaml
    - RunningTimeAnalysisFMU:
        ensembles:  # Required, type list.
        filter_shorter:  # Optional, type Union[int, float].
        status_file:  # Optional, type str.
        visual_parameters:  # Optional, type Union[list, NoneType].
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

*Required, type List[str (corresponding to a path)]*


---

* **`zunit`:** z-unit for display.

*default = "depth (m)", Optional, type str*


---

* **`colors`:** List of hex colors use. Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. `'#000000'` for black.

*default = null, Optional, type list*


---



How to use in YAML config file:
```yaml
    - SegyViewer:
        segyfiles:  # Required, type List[str (corresponding to a path)].
        zunit:  # Optional, type str.
        colors:  # Optional, type list.
```

   

<!-- tab:Data input -->


* [Examples of segyfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/observed_data/seismic).

The segyfiles are on a `SEG-Y` format and can be investigated outside `webviz` using e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### StructuralUncertainty


<!-- tabs:start -->
   

<!-- tab:Description -->

Dashboard to analyze structural uncertainty results from FMU runs.

A cross-section along a well or from a polyline drawn interactively on a map.
Map views to compare two surfaces from e.g. two iterations.

Both individual realization surfaces and statistical surfaces can be plotted.

Wells are required. If a zonelog is provided formation tops are extracted
and plotted as markers along the well trajectory.

Customization of colors and initialization of plugin with predefined selections
is possible. See the `Arguments` sections for details.

!> This plugin follows the FMU standards for storing and naming surface files.
Surface files must be stored at `share/results/maps` for each ensemble,
and be named as `surfacename--surfaceattribute.gri`


 

<!-- tab:Arguments -->


* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

*Required, type list*


---

* **`surface_attributes`:** List of surface attributes from surface filenames(FMU standard). All surface_attributes must have the same surface names.

*Required, type list*


---

* **`surface_name_filter`:** List of the surface names (FMU standard) in stratigraphic order

*default = null, Optional, type List[str]*


---

* **`wellfolder`:** A folder with wells on RMS Well format. (absolute or relative to config file).

*default = null, Optional, type str (corresponding to a path)*


---

* **`wellsuffix`:** File suffix for wells in `wellfolder`.

*default = ".w", Optional, type str*


---

* **`zonelog`:** Name of zonelog in `wellfiles` (displayed along well trajectory).

*default = null, Optional, type str*


---

* **`mdlog`:** Name of mdlog in `wellfiles` (displayed along well trajectory).

*default = null, Optional, type str*


---

* **`well_tvdmin`:** Truncate well trajectory values above this depth.

*default = null, Optional, type Union[int, float]*


---

* **`well_tvdmax`:** Truncate well trajectory values below this depth.

*default = null, Optional, type Union[int, float]*


---

* **`well_downsample_interval`:** Sampling interval used for coarsening a well trajectory

*default = null, Optional, type int*


---

* **`calculate_percentiles`:** Only relevant for portable. Calculating P10/90 is time consuming and is by default disabled to allow fast generation of portable apps. Activate to precalculate these percentiles for all realizations.

*default = false, Optional, type bool*


---

* **`initial_settings`:** Configuration for initializing the plugin with various properties set. All properties are optional. ```yaml initial_settings: intersection_data: # Data to populate the intersection view surface_attribute: ds_extracted_horizons #name of active attribute surface_names: #list of active surfacenames - topupperreek - baselowerreek ensembles: #list of active ensembles - iter-0 - iter-1 calculation: #list of active calculations - Mean - Min - Max - Realizations - Uncertainty envelope well: OP_6 #Active well realizations: #List of active realizations - 0 resolution: 20 # Horizontal distance between points in the intersection # (Usually in meters) extension: 500 # Horizontal extension of the intersection depth_truncations: # Truncations to use for yaxis range min: 1500 max: 3000 colors: # Colors to use for surfaces in the intersection view specified # for each ensemble topupperreek: iter-0: '#2C82C9' #hex color code with apostrophies and hash prefix intersection_layout: # The full plotly layout # (https://plotly.com/python/reference/layout/) is # exposed to allow for customization of e.g. plot title # and axis ranges. A small example: yaxis: title: True vertical depth [m] xaxis: title: Lateral distance [m] ```

*default = null, Optional, type Dict*


---



How to use in YAML config file:
```yaml
    - StructuralUncertainty:
        ensembles:  # Required, type list.
        surface_attributes:  # Required, type list.
        surface_name_filter:  # Optional, type List[str].
        wellfolder:  # Optional, type str (corresponding to a path).
        wellsuffix:  # Optional, type str.
        zonelog:  # Optional, type str.
        mdlog:  # Optional, type str.
        well_tvdmin:  # Optional, type Union[int, float].
        well_tvdmax:  # Optional, type Union[int, float].
        well_downsample_interval:  # Optional, type int.
        calculate_percentiles:  # Optional, type bool.
        initial_settings:  # Optional, type Dict.
```

   

<!-- tab:Data input -->


**Example files**

* [One file for surfacefiles](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/maps/topupperreek--ds_extracted_horizons.gri).

* [Wellfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/observed_data/wells).

The surfacefiles are on a `Irap binary` format and can be investigated outside `webviz` using e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

 

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


* **`jsonfile`:** jsonfile with data, suitable for the corresponding [subsurface map component](https://github.com/equinor/webviz-subsurface-components) (absolute path or relative to config file). **Ensemble data**

*default = null, Optional, type str (corresponding to a path)*


---

* **`ensemble`:** Which ensemble in `shared_settings` to visualize (**just one**).

*default = null, Optional, type str*


---

* **`map_value`:** Which property to show in the map (e.g. `PERMX`).

*default = null, Optional, type str*


---

* **`flow_value`:** Which property to use for the streamlines animation (e.g. `FLOWAT`).

*default = null, Optional, type str*


---

* **`time_step`:** Which report or time step to use in the simulation output.

*default = null, Optional, type int*


---



How to use in YAML config file:
```yaml
    - SubsurfaceMap:
        jsonfile:  # Optional, type str (corresponding to a path).
        ensemble:  # Optional, type str.
        map_value:  # Optional, type str.
        flow_value:  # Optional, type str.
        time_step:  # Optional, type int.
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

*Required, type list*


---

* **`attributes`:** List of surface attributes to include, if not given all surface attributes will be included.

*default = null, Optional, type list*


---

* **`attribute_settings`:** Dictionary with setting for each attribute. Available settings are: * `min`: Truncate colorscale (lower limit). * `max`: Truncate colorscale (upper limit). * `color`: List of hexadecimal colors. * `unit`: Text to display as unit in label.

*default = null, Optional, type dict*


---

* **`wellfolder`:** Folder with RMS wells.

*default = null, Optional, type str (corresponding to a path)*


---

* **`wellsuffix`:** File suffix for wells in well folder.

*default = ".w", Optional, type str*


---

* **`map_height`:** Set the height in pixels for the map views.

*default = 600, Optional, type int*


---



How to use in YAML config file:
```yaml
    - SurfaceViewerFMU:
        ensembles:  # Required, type list.
        attributes:  # Optional, type list.
        attribute_settings:  # Optional, type dict.
        wellfolder:  # Optional, type str (corresponding to a path).
        wellsuffix:  # Optional, type str.
        map_height:  # Optional, type int.
```

   

<!-- tab:Data input -->

The available maps are gathered from the `share/results/maps/` folder
for each realization. Subfolders are not supported.

The filenames need to follow a fairly strict convention, as the filenames are used as metadata:
`horizon_name--attribute--date` (`--date` is optional). The files should be on `irap binary`
format with the suffix `.gri`. The date is of the form `YYYYMMDD` or
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
    color:
    - "#000004"
    - "#1b0c41"
    - "#4a0c6b"
    - "#781c6d"
```

 

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

*Required, type str (corresponding to a path)*


---

* **`gridparameterfiles`:** List of file paths to grid parameters (`ROFF` format) (absolute or relative to config file).

*Required, type List[str (corresponding to a path)]*


---

* **`surfacefiles`:** List of file paths to surfaces (`irap binary` format) (absolute or relative to config file).

*Required, type List[str (corresponding to a path)]*


---

* **`gridparameternames`:** List corresponding to filepaths of displayed parameter names.

*default = null, Optional, type list*


---

* **`surfacenames`:** List corresponding to file paths of displayed surface names.

*default = null, Optional, type list*


---

* **`zunit`:** z-unit for display.

*default = "depth (m)", Optional*


---

* **`colors`:** List of hex colors to use. Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. `'#000000'` for black.

*default = null, Optional, type list*


---



How to use in YAML config file:
```yaml
    - SurfaceWithGridCrossSection:
        gridfile:  # Required, type str (corresponding to a path).
        gridparameterfiles:  # Required, type List[str (corresponding to a path)].
        surfacefiles:  # Required, type List[str (corresponding to a path)].
        gridparameternames:  # Optional, type list.
        surfacenames:  # Optional, type list.
        zunit:  # Optional.
        colors:  # Optional, type list.
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

*Required, type List[str (corresponding to a path)]*


---

* **`surfacefiles`:** List of file paths to Irap Binary surfaces (absolute or relative to config file).

*Required, type List[str (corresponding to a path)]*


---

* **`surfacenames`:** Corresponding list of displayed surface names.

*default = null, Optional, type list*


---

* **`segynames`:** Corresponding list of displayed seismic names.

*default = null, Optional, type list*


---

* **`zunit`:** z-unit for display

*default = "depth (m)", Optional*


---

* **`colors`:** List of hex colors to use. Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. `'#000000'` for black.

*default = null, Optional, type list*


---



How to use in YAML config file:
```yaml
    - SurfaceWithSeismicCrossSection:
        segyfiles:  # Required, type List[str (corresponding to a path)].
        surfacefiles:  # Required, type List[str (corresponding to a path)].
        surfacenames:  # Optional, type list.
        segynames:  # Optional, type list.
        zunit:  # Optional.
        colors:  # Optional, type list.
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

#### VolumetricAnalysis


<!-- tabs:start -->
   

<!-- tab:Description -->

Dashboard to analyze volumetrics results from
FMU ensembles.

This plugin supports both monte carlo and sensitivity runs, and will automatically detect
which case has been run.

The fluid type is determined by the column name suffixes, either (_OIL or _GAS). This suffix
is removed and a `FLUID` column is added to be used as a filter or selector.

Input can be given either as aggregated `csv` files or as ensemble name(s)
defined in `shared_settings` (with volumetric `csv` files stored per realization).


 

<!-- tab:Arguments -->


* **`csvfile_vol`:** 

*default = null, Optional, type str (corresponding to a path)*


---

* **`csvfile_parameters`:** 

*default = null, Optional, type str (corresponding to a path)*


---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

*default = null, Optional, type list*


---

* **`volfiles`:** Key/value pair of csv files E.g. `{geogrid: geogrid--oil.csv}`. Only relevant if `ensembles` is defined. The key (e.g. `geogrid`) will be used as `SOURCE`.

*default = null, Optional, type dict*


---

* **`volfolder`:** Local folder for the `volfiles`.

*default = "share/results/volumes", Optional, type str*


---

* **`drop_constants`:** 

*default = true, Optional, type bool*


---



How to use in YAML config file:
```yaml
    - VolumetricAnalysis:
        csvfile_vol:  # Optional, type str (corresponding to a path).
        csvfile_parameters:  # Optional, type str (corresponding to a path).
        ensembles:  # Optional, type list.
        volfiles:  # Optional, type dict.
        volfolder:  # Optional, type str.
        drop_constants:  # Optional, type bool.
```

   

<!-- tab:Data input -->


?> The input files must follow FMU standards.

* [Example of an aggregated file for `csvfiles`](https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/volumes.csv).

* [Example of a file per realization that can be used with `ensembles` and `volfiles`](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/realization-0/iter-0/share/results/volumes/geogrid--oil.csv).

For sensitivity runs the sensitivity information is extracted automatically if `ensembles`is given as input, as long as `SENSCASE` and `SENSNAME` is found in `parameters.txt`.* [Example of an aggregated file to use with `csvfile_parameters`](https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/parameters.csv)


**The following columns will be used as available filters, if present:**

* `ZONE`
* `REGION`
* `FACIES`
* `LICENSE`
* `SOURCE` (relevant if calculations are done for multiple grids)
* `SENSNAME`
* `SENSCASE`


**Remaining columns are seen as volumetric responses.**

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### WellCompletions


<!-- tabs:start -->
   

<!-- tab:Description -->

Visualizes well completions data per well coming from export of the Eclipse COMPDAT output.     Data is grouped per well and zone and can be filtered accoring to flexible well categories.

!> The plugin will not see lumps of completions that are shut using the WELOPEN keyword.     This is being worked on and will be fixed in future relases.


 

<!-- tab:Arguments -->


* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

*Required, type list*


---

* **`compdat_file`:** `.csv` file with compdat data per realization

*default = "share/results/wells/compdat.csv", Optional, type str*


---

* **`zone_layer_mapping_file`:** `.lyr` file specifying the zone ➔ layer mapping

*default = "rms/output/zone/simgrid_zone_layer_mapping.lyr", Optional, type str*


---

* **`stratigraphy_file`:** `.json` file defining the stratigraphic levels

*default = "rms/output/zone/stratigraphy.json", Optional, type str*


---

* **`well_attributes_file`:** `.json` file with categorical well attributes

*default = "rms/output/wells/well_attributes.json", Optional, type str*


---

* **`kh_unit`:** e.g. mD·m, will try to extract from eclipse files if defaulted

*default = null, Optional, type str*


---

* **`kh_decimal_places`:** 

*default = 2, Optional, type int*


---



How to use in YAML config file:
```yaml
    - WellCompletions:
        ensembles:  # Required, type list.
        compdat_file:  # Optional, type str.
        zone_layer_mapping_file:  # Optional, type str.
        stratigraphy_file:  # Optional, type str.
        well_attributes_file:  # Optional, type str.
        kh_unit:  # Optional, type str.
        kh_decimal_places:  # Optional, type int.
```

   

<!-- tab:Data input -->

The minimum requirement is to define `ensembles`.

**COMPDAT input**

`compdat_file` is a path to a file stored per realization (e.g. in     `share/results/wells/compdat.csv`.

The `compdat_file` file can be dumped to disk per realization by a forward model in ERT that
wraps the command `ecl2csv compdat input_file -o output_file` (requires that you have `ecl2df`
installed).
[Link to ecl2csv compdat documentation.](https://equinor.github.io/ecl2df/usage/compdat.html)

**Zone layer mapping**

The `zone_layer_mapping_file` file can be dumped to disk per realization by an internal     RMS script as part of the FMU workflow. A sample python script should be available in the     Drogon project.

The file needs to be on the lyr format used by ResInsight:
[Link to description of lyr format](https://resinsight.org/3d-main-window/formations/#formation-names-description-files-_lyr_).

Zone colors can be specified in the lyr file, but only 6 digit hexadecimal codes will be used.

If no file exists, layers will be used as zones.

**Stratigraphy file**

The `stratigraphy_file` file is intended to be generated per realization by an internal     RMS script as part of the FMU workflow, but can also be set up manually and copied to each
realization. The stratigraphy is a tree structure, where each node has a name, an optional
`color` parameter, and an optional `subzones` parameter which itself is a list of the same format.
```json
[
    {
        "name": "ZoneA",
        "color": "#FFFFFF",
        "subzones": [
            {
                "name": "ZoneA.1
            },
            {
                "name": "ZoneA.2
            }
        ]
    },
    {
        "name": "ZoneB",
        "color": "#FFF000",
        "subzones": [
            {
                "name": "ZoneB.1",
                "color": "#FFF111"
            },
            {
                "name": "ZoneB.2,
                "subzones: {"name": "ZoneB.2.2"}
            }
        ]
    },
]
```
The `stratigraphy_file` and the `zone_layer_mapping_file` will be combined to create the final     stratigraphy. A node will be removed if the name or any of the subnode names are not     present in the zone layer mapping. A Value Error is raised if any zones are present in the
zone layer mapping but not in the stratigraphy.

Colors can be supplied both trough the stratigraphy and through the zone_layer_mapping.     The following prioritization will be applied:
1. Colors specified in the stratigraphy
2. Colors specified in the zone layer mapping lyr file
3. If none of the above is specified, theme colors will be added to the leaves of the tree

**Well Attributes file**

The `well_attributes_file` file is intended to be generated per realization by an internal     RMS script as part of the FMU workflow. A sample script will be made available, but it is     possible to manually set up the file and copy it to the correct folder on the scratch disk.    The categorical well attributes are completely flexible.

The file should be a `.json` file on the following format:
```json
{
    "version" : "0.1",
    "wells" : [
    {
        "alias" : {
            "eclipse" : "OP_1"
        },
        "attributes" : {
            "mlt_singlebranch" : "mlt",
            "structure" : "East",
            "welltype" : "producer"
        },
        "name" : "OP_1"
    },
    {
        "alias" : {
            "eclipse" : "GI_1"
        },
        "attributes" : {
            "mlt_singlebranch" : "singlebranch",
            "structure" : "West",
            "welltype" : "gas injector"
        },
        "name" : "GI_1"
    },
    ]
}
```

**KH unit**

If defaulted, the plugin will look for the unit system of the Eclipse deck in the DATA file.     The kh unit will be deduced from the unit system, e.g. mD·m if METRIC.

 

<!-- tabs:end -->

</div>



<div class="plugin-doc">

#### WellCrossSection

<details>
  <summary markdown="span"> :warning: Plugin 'WellCrossSection' has been deprecated.</summary>

  Relevant functionality is implemented in the StructuralUncertainty plugin.
</details>


<!-- tabs:start -->
   

<!-- tab:Description -->

Displays a cross section along a well with intersected surfaces,
and optionally seismic cubes.

!> See also WellCrossSectionFMU for additional functionality with FMU ensembles.

 

<!-- tab:Arguments -->


* **`surfacefiles`:** List of file paths to Irap binary surfaces (absolute or relative to config file).

*Required, type List[str (corresponding to a path)]*


---

* **`wellfiles`:** List of file paths to RMS wells (absolute or relative to config file).

*Required, type List[str (corresponding to a path)]*


---

* **`segyfiles`:** List of file paths to segyfiles (absolute or relative to config file).

*default = null, Optional, type List[str (corresponding to a path)]*


---

* **`surfacenames`:** Corresponding list of displayed surface names.

*default = null, Optional, type list*


---

* **`zonelog`:** Name of zonelog (for the RMS wells in `wellfiles`).

*default = null, Optional, type str*


---

* **`zunit`:** z-unit for display.

*default = "depth (m)", Optional, type str*


---

* **`zmin`:** Visualized minimum z-value in cross section.

*default = null, Optional, type float*


---

* **`zmax`:** Visualized maximum z-value in cross section.

*default = null, Optional, type float*


---

* **`zonemin`:** First zonenumber to draw in log.

*default = 1, Optional, type int*


---

* **`nextend`:** Number of samples to extend well fence on each side of well, e.g. with distance of sampling=20 and nextend=2: extension=2*20 (nextend*sampling).

*default = 2, Optional, type int*


---

* **`sampling`:** Sampling interval of well fence.

*default = 40, Optional, type int*


---



How to use in YAML config file:
```yaml
    - WellCrossSection:
        surfacefiles:  # Required, type List[str (corresponding to a path)].
        wellfiles:  # Required, type List[str (corresponding to a path)].
        segyfiles:  # Optional, type List[str (corresponding to a path)].
        surfacenames:  # Optional, type list.
        zonelog:  # Optional, type str.
        zunit:  # Optional, type str.
        zmin:  # Optional, type float.
        zmax:  # Optional, type float.
        zonemin:  # Optional, type int.
        nextend:  # Optional, type int.
        sampling:  # Optional, type int.
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

<details>
  <summary markdown="span"> :warning: Plugin 'WellCrossSectionFMU' has been deprecated.</summary>

  Relevant functionality is implemented in the StructuralUncertainty plugin.
</details>


<!-- tabs:start -->
   

<!-- tab:Description -->

Well cross-section displaying statistical surfaces from a FMU ensemble.

Statistical surfaces are calculated automatically from surfaces stored
per realization.


 

<!-- tab:Arguments -->


* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

*Required, type list*


---

* **`surfacefiles`:** Surface file names (without folder).

*Required, type list*


---

* **`surfacenames`:** List corresponding to `surfacefiles` of displayed surface names.

*default = null, Optional, type list*


---

* **`surfacefolder`:** Realization relative folder containing the `surfacefiles`.

*default = "share/results/maps", Optional, type str (corresponding to a path)*


---

* **`wellfiles`:** List of file paths to RMS wells (absolute or relative to config file).

*default = null, Optional, type List[str (corresponding to a path)]*


---

* **`wellfolder`:** Alternative to `wellfiles`: provide a folder with RMS wells. (absolute or relative to config file).

*default = null, Optional, type str (corresponding to a path)*


---

* **`wellsuffix`:** File suffix for wells in `wellfolder`.

*default = ".w", Optional, type str*


---

* **`segyfiles`:** List of file paths to `segyfiles` (absolute or relative to config file).

*default = null, Optional, type List[str (corresponding to a path)]*


---

* **`zonelog`:** Name of zonelog in `wellfiles` (displayed along well trajectory).

*default = null, Optional, type str*


---

* **`marginal_logs`:** Logs in `wellfiles` to be displayed in separate horizontal plot.

*default = null, Optional, type list*


---

* **`zunit`:** z-unit for display.

*default = "depth (m)", Optional, type str*


---

* **`zmin`:** Visualized minimum z-value in cross section.

*default = null, Optional, type float*


---

* **`zmax`:** Visualized maximum z-value in cross section.

*default = null, Optional, type float*


---

* **`zonemin`:** First zonenumber to draw in zone log.

*default = 1, Optional, type int*


---

* **`nextend`:** Number of samples to extend well fence on each side of well, e.g. `sampling=20` and `nextend=2` results in `extension=20*2`.

*default = 2, Optional, type int*


---

* **`sampling`:** Horizontal sampling interval.

*default = 40, Optional, type int*


---

* **`colors`:** List of hex colors corresponding to surfaces. Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. `'#000000'` for black.

*default = null, Optional, type list*


---



How to use in YAML config file:
```yaml
    - WellCrossSectionFMU:
        ensembles:  # Required, type list.
        surfacefiles:  # Required, type list.
        surfacenames:  # Optional, type list.
        surfacefolder:  # Optional, type str (corresponding to a path).
        wellfiles:  # Optional, type List[str (corresponding to a path)].
        wellfolder:  # Optional, type str (corresponding to a path).
        wellsuffix:  # Optional, type str.
        segyfiles:  # Optional, type List[str (corresponding to a path)].
        zonelog:  # Optional, type str.
        marginal_logs:  # Optional, type list.
        zunit:  # Optional, type str.
        zmin:  # Optional, type float.
        zmax:  # Optional, type float.
        zonemin:  # Optional, type int.
        nextend:  # Optional, type int.
        sampling:  # Optional, type int.
        colors:  # Optional, type list.
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

