# Plugin project webviz-subsurface

?> :bookmark: This documentation is valid for version `0.2.13rc0` of `webviz-subsurface`.



---

<div class="plugin-doc">

#### AssistedHistoryMatchingAnalysis


<!-- tabs:start -->


<!-- tab:Description -->

Visualize parameter distribution change prior to posterior     per observation group in an assisted history matching process.
This is done by using a     [KS (Kolmogorov Smirnov) test](https://en.wikipedia.org/wiki/Kolmogorov%E2%80%93Smirnov_test)     matrix, and scatter plot/map for any given pair of parameter/observation.     KS values are between 0 and 1.     The closer to zero the KS value is, the smaller the change in parameter distribution     between prior/posterior and vice-versa.     The top 10 biggest parameters change are also shown in a table.




<!-- tab:Arguments -->









* **`input_dir`:** Path to the directory where the `csv` files created         by the `AHM_ANALYSIS` ERT postprocess workflow are stored
* **`ks_filter`:** optional argument to filter output to the data table based on ks value,         only values above entered value will be displayed in the data table.         This can be used if needed to speed-up vizualization of cases with         high number of parameters and/or observations group. Default value is 0.0.



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
* **`date`:** Date as string of form YYYY-MM-DD to request an explisit date. Default is to
to use the most recent file avaialable, limited to the last week.



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

#### GroupTree


<!-- tabs:start -->


<!-- tab:Description -->

This plugin vizualizes the network tree and displays pressures,
rates and other network related information.




<!-- tab:Arguments -->












* **`ensembles`:** Which ensembles in `shared_settings` to include.
* **`gruptree_file`:** `.csv` with gruptree information.
* **`time_index`:** Frequency for the data sampling.


---
How to use in YAML config file:
```yaml
    - GroupTree:
        ensembles:  # Required, type list.
        gruptree_file:  # Optional, type str.
        rel_file_pattern:  # Optional, type str.
        time_index:  # Optional, type str.
```



<!-- tab:Data input -->


**Summary data**

This plugin needs the following summary vectors to be exported:
* FOPR, FWPR, FOPR, FWIR and FGIR
* GPR for all group nodes in the network
* GOPR, GWPR and GGPR for all group nodes in the production network     (GOPRNB etc for BRANPROP trees)
* GGIR and/or GWIR for all group nodes in the injection network
* WSTAT, WTHP, WBHP, WMCTL for all wells
* WOPR, WWPR, WGPR for all producers
* WWIR and/or WGIR for all injectors

**GRUPTREE input**

`gruptree_file` is a path to a file stored per realization (e.g. in     `share/results/tables/gruptree.csv"`).

The `gruptree_file` file can be dumped to disk per realization by the `ECL2CSV` forward
model with subcommand `gruptree`. The forward model uses `ecl2df` to export a table
representation of the Eclipse network:
[Link to ecl2csv gruptree documentation.](https://equinor.github.io/ecl2df/usage/gruptree.html).

**time_index**

This is the sampling interval of the summary data. It is `yearly` by default, but can be set
to `monthly` if needed.



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















**Using aggregated data**
* **`csvfile`:** Aggregated csvfile with `REAL`, `ENSEMBLE` and `SOURCE` columns (absolute path or relative to config file).

**Using data stored per realization**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`volfiles`:**  Key/value pair of csv files E.g. `{geogrid: geogrid--oil.csv}`.
Only relevant if `ensembles` is defined. The key (e.g. `geogrid`) will be used as `SOURCE`.
* **`volfolder`:** Local folder for the `volfiles`.

**Common settings for both input options**
* **`response`:** Optional volume response to visualize initially.



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

<details>
  <summary markdown="span"> :warning: Plugin 'InplaceVolumesOneByOne' has been deprecated.</summary>

  Relevant functionality is implemented in the VolumetricAnalysis plugin.
</details>


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



























* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`csvfile`:** Relative path to Csv file stored per realization
 * **`observation_file`:** Yaml file with observations
* **`observation_group`:** Top-level key in observation file.
* **`remap_observation_keys`:** Remap observation keys to columns in csv file
* **`remap_observation_values`:** Remap observation values to columns in csv file
* **`colors`:** Set colors for each ensemble
* **`initial_data`:** Initialize data selectors (x,y,ensemble, parameter)
* **`initial_layout`:** Initialize plot layout (x and y axis direction and type)


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

#### MapViewerFMU


<!-- tabs:start -->


<!-- tab:Description -->

Surface visualizer for FMU ensembles.
A dashboard to covisualize arbitrary surfaces generated by FMU.




<!-- tab:Arguments -->

















* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`attributes`:** List of surface attributes to include, if not given
    all surface attributes will be included.
* **`well_pick_file`:** A csv file with well picks.  See data input.
* **`fault_polygon_attribute`:** Which set of fault polygons to use.
* **`map_surface_names_to_well_pick_names`:** Allows mapping of file surface names
    to the relevant well pick name
* **`map_surface_names_to_fault_polygons`:** Allows mapping of file surface names
    to the relevant fault polygon set name



---
How to use in YAML config file:
```yaml
    - MapViewerFMU:
        ensembles:  # Required, type list.
        attributes:  # Optional, type list.
        well_pick_file:  # Optional, type str (corresponding to a path).
        fault_polygon_attribute:  # Optional, type Union[str, NoneType].
        map_surface_names_to_fault_polygons:  # Optional, type Dict[str, str].
        map_surface_names_to_well_pick_names:  # Optional, type Dict[str, str].
```



<!-- tab:Data input -->

The available maps are gathered from the `share/results/maps/` folder
for each realization. Subfolders are not supported.

Observed maps are gathered from the `share/observations/maps/` folder in the case folder.<br>
The filenames need to follow a fairly strict convention, as the filenames are used as metadata:
`horizon_name--attribute--date` (`--date` is optional).<br> The files should be on `irap binary`
format with the suffix `.gri`.

The date is of the form `YYYYMMDD` or `YYYYMMDD_YYYYMMDD`, the latter would be for a delta
surface between two dates.<br>
See [this folder](https://github.com/equinor/webviz-subsurface-testdata/tree/master/01_drogon_ahm/realization-0/iter-0/share/results/maps) for examples of file naming conventions.

Fault polygons are gathered from the `share/results/polygons` folder for each realization.<br>
Same file naming convention as for surfaces must be followed and the suffix should be `.pol`,
representing XYZ format usable by xtgeo.<br>
See [this file](https://github.com/equinor/webviz-subsurface-testdata/blob/master/01_drogon_ahm/realization-0/iter-0/share/results/polygons/toptherys--gl_faultlines_extract_postprocess.pol) for an example.

Well picks are provided as a csv file with columns `X_UTME,Y_UTMN,Z_TVDSS,MD,WELL,HORIZON`.
See [wellpicks.csv](https://github.com/equinor/webviz-subsurface-testdata/tree/master/observed_data/drogon_well_picks/wellpicks.csv) for an example.<br>
Well picks can be exported from RMS using this script: [extract_well_picks_from_rms.py](https://github.com/equinor/webviz-subsurface-testdata/tree/master/observed_data/drogon_well_picks/extract_well_picks_from_rms.py)



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

> :warning: At least one argument has a deprecation warning.</summary>


<!-- tabs:start -->


<!-- tab:Description -->

This plugin visualizes parameter distributions and statistics.
for FMU ensembles, and can be used to investigate parameter correlations
on reservoir simulation time series data.




<!-- tab:Arguments -->












>:warning: **`csvfile_parameters`:** Certain values for the argument have been deprecated and might soon not be accepted anymore. See function below for details.


>:warning: **`csvfile_smry`:** Certain values for the argument have been deprecated and might soon not be accepted anymore. See function below for details.



---



**Using raw ensemble data stored in realization folders**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`rel_file_pattern`:** path to `.arrow` files with summary data.
* **`time_index`:** Time separation between extracted values. Can be e.g. `monthly` (default) or     `yearly`.
* **`drop_constants`:** Bool used to determine if constant parameters should be dropped.     Default is True.
* **`column_keys`:** List of vectors to extract. If not given, all vectors     from the simulations will be extracted. Wild card asterisk `*` can be used.


Function checking for deprecations:
```python
def check_deprecation_argument(
    csvfile_parameters: Optional[Path], csvfile_smry: Optional[Path]
) -> Optional[Tuple[str, str]]:
    if any(elm is not None for elm in [csvfile_parameters, csvfile_smry]):
        return (
            "The usage of aggregated csvfiles as user input options are deprecated. "
            "Please provide feedback if you see a need for a continuation "
            "of this functionality ",
            "",
        )
    return None

```
---

---
How to use in YAML config file:
```yaml
    - ParameterAnalysis:
        ensembles:  # Optional, type Union[list, NoneType].
        time_index:  # Optional, type str.
        column_keys:  # Optional, type Union[list, NoneType].
        drop_constants:  # Optional, type bool.
        rel_file_pattern:  # Optional, type str.
        csvfile_parameters:  # Deprecated, type str (corresponding to a path).
        csvfile_smry:  # Deprecated, type str (corresponding to a path).
```



<!-- tab:Data input -->


?> `Arrow` format for simulation time series data can be generated using the `ECL2CSV` forward model in ERT. On existing ensembles the command line tool `smry2arrow_batch` can be used to generate arrow files.

!> For smry data it is **strongly recommended** to keep the data frequency to a regular frequency (like `monthly` or `yearly`). This is because the statistics are calculated per DATE over all realizations in an ensemble, and the available dates should therefore not differ between individual realizations of an ensemble.

?> Vectors that are identified as historical vectors (e.g. FOPTH is the history of FOPT) will be plotted together with their non-historical counterparts as reference lines.

!> Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations if you have defined `ensembles`.



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









**Using aggregated data**
* **`csvfile`:** Aggregated `csv` file with `REAL`, `ENSEMBLE` and parameter columns.  (absolute path or relative to config file).

**Reading data from ensembles**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.



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

#### ProdMisfit


<!-- tabs:start -->


<!-- tab:Description -->

Visualizes production data misfit at selected date(s).

When not dealing with absolute value of differences, difference plots are
represented as: (simulated - observed),
i.e. negative values means sim is lower than obs and vice versa.

**Features**
* Visualization of prod misfit at selected time.
* Visualization of prod coverage at selected time.
* Heatmap representation of ensemble mean misfit for selected dates.




<!-- tab:Arguments -->


















* **`ensembles`:** Which ensembles in `shared_settings` to include.
* **`rel_file_pattern`:** path to `.arrow` files with summary data.
* **`gruptree_file`:** `.csv` with gruptree information.
* **`sampling`:** Frequency for the data sampling.
* **`well_attributes_file`:** Path to json file containing info of well attributes.
The attribute category values can be used for filtering of well collections.
* **`excl_name_startswith`:** Filter out wells that starts with this string
* **`excl_name_contains`:** Filter out wells that contains this string
* **`phase_weights`:** Dict of "Oil", "Water" and "Gas" (inverse) weight factors that
are included as weight option for misfit per real calculation.


---
How to use in YAML config file:
```yaml
    - ProdMisfit:
        ensembles:  # Required, type list.
        rel_file_pattern:  # Optional, type str.
        sampling:  # Optional, type str.
        well_attributes_file:  # Optional, type str.
        excl_name_startswith:  # Optional, type list.
        excl_name_contains:  # Optional, type list.
        phase_weights:  # Optional, type dict.
```



<!-- tab:Data input -->


**Summary data**

This plugin needs the following summary vectors to be stored with arrow format:
* WOPT+WOPTH and/or WWPT+WWPTH and/or WGPT+WGPTH

Summary files can be converted to arrow format with the `ECL2CSV` forward model.


`well_attributes_file`: Optional json file with well attributes.
The file needs to follow the format below. The categorical attributes     are completely flexible (user defined).
```json
{
    "version" : "0.1",
    "wells" : [
    {
        "alias" : {
            "eclipse" : "A1"
        },
        "attributes" : {
            "structure" : "East",
            "welltype" : "producer"
        },
        "name" : "55_33-A-1"
    },
    {
        "alias" : {
            "eclipse" : "A5"
        },
        "attributes" : {
            "structure" : "North",
            "welltype" : "injector"
        },
        "name" : "55_33-A-5"
    },
    ]
}
```



<!-- tabs:end -->

</div>

<div class="plugin-doc">

#### PropertyStatistics

> :warning: At least one argument has a deprecation warning.</summary>


<!-- tabs:start -->


<!-- tab:Description -->

This plugin visualizes ensemble statistics calculated from grid properties.




<!-- tab:Arguments -->














>:warning: **`csvfile_statistics`:** Certain values for the argument have been deprecated and might soon not be accepted anymore. See function below for details.


>:warning: **`csvfile_smry`:** Certain values for the argument have been deprecated and might soon not be accepted anymore. See function below for details.



---


**The main input to this plugin is property statistics extracted from grid models.
See the documentation in [fmu-tools](http://fmu-docs.equinor.com/) on how to generate this data.
Additional data includes UNSMRY data and optionally irap binary surfaces stored in standardized FMU format.


**Using raw ensemble data stored in realization folders**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`rel_file_pattern`:** path to `.arrow` files with summary data.
* **`statistic_file`:** Csv file for each realization with property statistics. See the     documentation in [fmu-tools](http://fmu-docs.equinor.com/) on how to generate this data.
* **`column_keys`:** List of vectors to extract. If not given, all vectors     from the simulations will be extracted. Wild card asterisk `*` can be used.
* **`time_index`:** Time separation between extracted values. Can be e.g. `monthly` (default) or     `yearly`.
* **`surface_renaming`:** Optional dictionary to rename properties/zones to match filenames     stored on FMU standardized format (zone--property.gri)



Function checking for deprecations:
```python
def check_deprecation_argument(
    csvfile_statistics: Optional[Path], csvfile_smry: Optional[Path]
) -> Optional[Tuple[str, str]]:
    if any(elm is not None for elm in [csvfile_statistics, csvfile_smry]):
        return (
            "The usage of aggregated csvfiles as user input options are deprecated. "
            "Please provide feedback if you see a need for a continuation "
            "of this functionality ",
            "",
        )
    return None

```
---

---
How to use in YAML config file:
```yaml
    - PropertyStatistics:
        ensembles:  # Optional, type Union[list, NoneType].
        rel_file_pattern:  # Optional, type str.
        statistics_file:  # Optional, type str.
        surface_renaming:  # Optional, type Union[dict, NoneType].
        time_index:  # Optional, type str.
        column_keys:  # Optional, type Union[list, NoneType].
        csvfile_statistics:  # Deprecated, type str (corresponding to a path).
        csvfile_smry:  # Deprecated, type str (corresponding to a path).
```



<!-- tab:Data input -->


?> `Arrow` format for simulation time series data can be generated using the `ECL2CSV` forward model in ERT. On existing ensembles the command line tool `smry2arrow_batch` can be used to generate arrow files.

?> Folders with statistical surfaces are assumed located at `<ensemble_path>/share/results/maps/<ensemble>/<statistic>` where `statistic` are subfolders with statistical calculation: `mean`, `stddev`, `p10`, `p90`, `min`, `max`.

!> For smry data it is **strongly recommended** to keep the data frequency to a regular frequency (like `monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` (controlled by the `sampling` key). This is because the statistics and fancharts are calculated per DATE over all realizations in an ensemble, and the available dates should therefore not differ between individual realizations of an ensemble.



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
* **`relpermfile`:** Local path to a csvfile in each realization with dumped relperm data.
* **`scalfile`:** Path to a reference file with SCAL recommendationed data.     Path to a single file, **not** per realization/ensemble. The path can be absolute or     relative to the `webviz` configuration.
* **`sheet_name`:** Which sheet to use for the `scalfile`, only relevant if `scalfile` is an     `xlsx` file (recommended to use csv files with `webviz`).



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

<details>
  <summary markdown="span"> :warning: Plugin 'ReservoirSimulationTimeSeries' has been deprecated.</summary>

  This plugin has been replaced by the faster, more flexible and less memory hungry plugin `SimulationTimeSeries`
</details>


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
    * `visualization` : `realizations`, `statistics` or `fanchart`
    * `date` : Date to show by default in histograms
* **`line_shape_fallback`:** Fallback interpolation method between points. Vectors identified as     rates or phase ratios are always backfilled, vectors identified as cumulative (totals) are     always linearly interpolated. The rest use the fallback.
    Supported options:
    * `linear` (default)
    * `backfilled`
    * `hv`, `vh`, `hvh`, `vhv` and `spline` (regular Plotly options).

**Calculated vector expressions**
* **`predefined_expressions`:** yaml file with pre-defined expressions



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
        predefined_expressions:  # Optional, type str.
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

* Plots for analysing the parameter response of the RFT data. Not available for aggregated data.




<!-- tab:Arguments -->
















**Using data per realization**

* **`ensembles`**: Which ensembles in `shared_settings` to visualize.

In addition, you need to have rft-files in your realizations stored at the local path `share/results/tables`. The `rft_ert.csv` is required as input, while the `rft.csv` is optional:

* **`rft_ert.csv`**: A csv file containing simulated and observed RFT data for RFT observations defined in ERT [(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/01_drogon_ahm/realization-0/iter-0/share/results/tables/rft_ert.csv).

* **`rft.csv`**: A csv file containing simulated RFT data extracted from ECLIPSE RFT output files using [ecl2df](https://equinor.github.io/ecl2df/ecl2df.html#module-ecl2df.rft) [(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/01_drogon_ahm/realization-0/iter-0/share/results/tables/rft.csv). Simulated RFT data can be visualized along MD if a "CONMD" column is present in the dataframe and only for wells where each RFT datapoint has a unique MD.

* **`parameters.txt`**: File with parameters and values

**Using aggregated data**

* **`csvfile_rft`**: Aggregated version of `rft.csv` [(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_test_data/aggregated_data/rft.csv).
* **`csvfile_rft_ert`**: Aggregated version of `rft_ert.csv` [(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_test_data/aggregated_data/rft_ert.csv).


**Optional input for both input options**

* **`obsdata`**: A csv file containing additional RFT observation data not defined in ERT for
visualization together with simulated RFT.
Mandatory column names: `WELL`, `DATE` (yyyy-mm-dd), `DEPTH` and `PRESSURE`

* **`formations`**: A csv file containing top and base values for each zone per well.
Used to visualize zone boundaries together with simulated RFT.
Mandatory column names: `WELL`, `ZONE`, `TOP_TVD`, `BASE_TVD` [(example file))](https://github.com/equinor/webviz-subsurface-testdata/blob/master/01_drogon_ahm/realization-0/iter-0/share/results/tables/formations.csv).

* **`faultlines`**: A csv file containing faultpolygons to be visualized together with the map view.
Export format from [xtgeo.xyz.polygons.dataframe](
https://xtgeo.readthedocs.io/en/latest/apiref/xtgeo.xyz.polygons.html#xtgeo.xyz.polygons.Polygons.dataframe
) [(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/01_drogon_ahm/realization-0/iter-0/share/results/polygons/toptherys--gl_faultlines_extract_postprocess.csv).



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
* **`filter_shorter`:** Filters jobs with maximum run time in ensemble less than X seconds     (default: 10). Can be checked on/off interactively, this only sets the filtering value.
* **`status_file`:** Name of json file local per realization with job status     (default: `status.json`).
* **`visual_parameters`:** List of default visualized parameteres in parallel coordinates plot     (default: all parameters).



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
* **`zunit`:** z-unit for display.
* **`colors`:** List of hex colors use. Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. `'#000000'` for black.



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

#### SeismicMisfit


<!-- tabs:start -->


<!-- tab:Description -->

Seismic misfit plotting.
Consists of several tabs with different plots of
observed and simulated seismic 4d attribute.
* Seismic obs data (overview)
* Seismic misfit per real (misfit quantification and ranking)
* Seismic crossplot - sim vs obs (data points statistics)
* Seismic errorbar plot - sim vs obs (data points statistics)
* Seismic map plot - sim vs obs (data points statistics)




<!-- tab:Arguments -->





















* **`ensembles`:** Which *scratch_ensembles* in *shared_settings* to include.
<br>(Note that **realization-** must be part of the *shared_settings* paths.)

* **`attributes`:** List of the simulated attribute file names to include.
It is a requirement that there is a corresponding file with the observed
and meta data included. This file must have the same name, but with an
additional prefix = "meta--". For example, if one includes a file
called "my_awesome_attribute.txt" in the attributes list, the corresponding
obs/meta file must be called "meta--my_awesome_attribute.txt". See Data input
section for more  details.

* **`attribute_sim_path`:** Path to the `attributes` simulation file.
Path is given as relative to *runpath*, where *runpath* = path as defined
for `ensembles` in shared settings.

* **`attribute_obs_path`:** Path to the `attributes` obs/meta file.
Path is either given as relative to *runpath* or as an absolute path.

* **`obs_mult`:** Multiplier for all observation and observation error data.
Can be used for calibration purposes.

* **`sim_mult`:** Multiplier for all simulated data.
Can be used for calibration purposes.

* **`polygon`:** Path to a folder or a file containing (fault-) polygons.
If value is a folder all csv files in that folder will be included
(e.g. "share/results/polygons/").
If value is a file, then that file will be read. One can also use \*-notation
in filename to read filtered list of files
(e.g. "share/results/polygons/\*faultlines\*csv").
Path is either given as relative to *runpath* or as an absolute path.
If path is ambigious (e.g. with multi-realization runpath),
only the first successful find is used.

* **`realrange`:** Realization range filter for each of the ensembles.
Assign as list of two integers in square brackets (e.g. [0, 99]).
Realizations outside range will be excluded.
If `realrange` is omitted, no realization filter will be applied (i.e. include all).



---
How to use in YAML config file:
```yaml
    - SeismicMisfit:
        ensembles:  # Required, type List[str].
        attributes:  # Required, type List[str].
        attribute_sim_path:  # Optional, type str.
        attribute_obs_path:  # Optional, type str.
        obs_mult:  # Optional, type float.
        sim_mult:  # Optional, type float.
        polygon:  # Optional, type str.
        realrange:  # Optional, type List[typing.List[int]].
```



<!-- tab:Data input -->


a) The required input data consists of 2 different file types.<br>

1) Observation and meta data csv file (one per attribute):
This csv file must contain the 5 column headers "EAST" (or "X_UTME"),
"NORTH" (or "Y_UTMN"), "REGION", "OBS" and "OBS_ERROR".
The column names are case insensitive and can be in any order.
"OBS" is the observed attribute value and "OBS_ERROR"
is the corresponding error.<br>
```csv
    X_UTME,Y_UTMN,REGION,OBS,OBS_ERROR
    456166.26,5935963.72,1,0.002072,0.001
    456241.17,5935834.17,2,0.001379,0.001
    456316.08,5935704.57,3,0.001239,0.001
    ...
    ...
```
2) Simulation data file (one per attribute and realization):
This is a 1 column file (ERT compatible format).
The column is the simulated attribute value. This file has no header.
```
    0.0023456
    0.0012345
    0.0013579
    ...
    ...
```

It is a requirement that each line of data in these 2 files represent
the same data point. I.e. line number N+1 in obs/metadata file corresponds to
line N in sim files. The +1 shift for the obs/metadata file
is due to that file is the only one with a header.

b) Polygon data is optional to include. Polygons must be stored in
csv file(s) on the format shown below. A csv file can have multiple
polygons (e.g. fault polygons), identified with the POLY_ID value.
```csv
    X_UTME,Y_UTMN,Z_TVDSS,POLY_ID
    460606.36,5935605.44,1676.49,0
    460604.92,5935583.99,1674.84,0
    460604.33,5935575.08,1674.16,2
    ...
    ...
```



<!-- tabs:end -->

</div>

<div class="plugin-doc">

#### SimulationTimeSeries

> :warning: At least one argument has a deprecation warning.</summary>


<!-- tabs:start -->


<!-- tab:Arguments -->










>:warning: **`options`:** Certain values for the argument have been deprecated and might soon not be accepted anymore. See function below for details.











---



Function checking for deprecations:
```python
def check_deprecation_argument(options: Optional[dict]) -> Optional[Tuple[str, str]]:
    if options is None:
        return None
    if any(elm in options for elm in ["vector1", "vector2", "vector3"]):
        return (
            'The usage of "vector1", "vector2" and "vector3" as user input options are deprecated. '
            'Please replace options with list named "vectors"',
            'The usage of "vector1", "vector2" and "vector3" as user input in options for '
            "initially selected vectors are deprecated. Please replace user input options with "
            'list named "vectors", where each element represent the corresponding initially '
            "selected vector.",
        )
    return None

```
---

---
How to use in YAML config file:
```yaml
    - SimulationTimeSeries:
        ensembles:  # Optional, type Union[list, NoneType].
        rel_file_pattern:  # Optional, type str.
        perform_presampling:  # Optional, type bool.
        obsfile:  # Optional, type str (corresponding to a path).
        options:  # Deprecated, type dict.
        sampling:  # Optional, type str.
        predefined_expressions:  # Optional, type str.
        user_defined_vector_definitions:  # Optional, type str.
        line_shape_fallback:  # Optional, type str.
```



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
* **`surface_attributes`:** List of surface attributes from surface filenames(FMU standard). All surface_attributes must have the same surface names.
 * **`surface_name_filter`:** List of the surface names (FMU standard) in stratigraphic order
* **`wellfolder`:** A folder with wells on RMS Well format. (absolute or relative to config file).
* **`wellsuffix`:** File suffix for wells in `wellfolder`.
* **`zonelog`:** Name of zonelog in `wellfiles` (displayed along well trajectory).
* **`mdlog`:** Name of mdlog in `wellfiles` (displayed along well trajectory).
* **`well_tvdmin`:** Truncate well trajectory values above this depth.
* **`well_tvdmax`:** Truncate well trajectory values below this depth.
* **`well_downsample_interval`:** Sampling interval used for coarsening a well trajectory
* **`calculate_percentiles`:** Only relevant for portable. Calculating P10/90 is
time consuming and is by default disabled to allow fast generation of portable apps. Activate to precalculate these percentiles for all realizations. * **`initial_settings`:** Configuration for initializing the plugin with various     properties set. All properties are optional.
    ```yaml
        initial_settings:
            intersection_data: # Data to populate the intersection view
                surface_attribute: ds_extracted_horizons  #name of active attribute
                surface_names: #list of active surfacenames
                    - topupperreek
                    - baselowerreek
                ensembles: #list of active ensembles
                    - iter-0
                    - iter-1
                calculation: #list of active calculations
                    - Mean
                    - Min
                    - Max
                    - Realizations
                    - Uncertainty envelope
                well: OP_6 #Active well
                realizations: #List of active realizations
                    - 0
                resolution: 20 # Horizontal distance between points in the intersection
                             # (Usually in meters)
                extension: 500 # Horizontal extension of the intersection
                depth_truncations: # Truncations to use for yaxis range
                    min: 1500
                    max: 3000
            colors: # Colors to use for surfaces in the intersection view specified
                    # for each ensemble
                topupperreek:
                    iter-0: '#2C82C9' #hex color code with apostrophies and hash prefix
            intersection_layout: # The full plotly layout
                                 # (https://plotly.com/python/reference/layout/) is
                                 # exposed to allow for customization of e.g. plot title
                                 # and axis ranges. A small example:
                yaxis:
                    title: True vertical depth [m]
                xaxis:
                    title: Lateral distance [m]
    ```


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














**Two input options: Ensemble data or premade json file**

**json file**
* **`jsonfile`:** jsonfile with data, suitable for the corresponding [subsurface map component](https://github.com/equinor/webviz-subsurface-components)  (absolute path or relative to config file).

**Ensemble data**
* **`ensemble`:** Which ensemble in `shared_settings` to visualize (**just one**).
* **`map_value`:** Which property to show in the map (e.g. `PERMX`).
* **`flow_value`:** Which property to use for the streamlines animation
  (e.g. `FLOWAT`).
* **`time_step`:** Which report or time step to use in the simulation output.



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

<details>
  <summary markdown="span"> :warning: Plugin 'SurfaceViewerFMU' has been deprecated.</summary>

  Relevant functionality is implemented in the MapViewerFMU plugin.
</details>


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
    * `color`: List of hexadecimal colors.
    * `unit`: Text to display as unit in label.
* **`wellfolder`:** Folder with RMS wells.
* **`wellsuffix`:** File suffix for wells in well folder.
* **`map_height`:** Set the height in pixels for the map views.



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
* **`gridparameterfiles`:** List of file paths to grid parameters (`ROFF` format)  (absolute or relative to config file).
* **`gridparameternames`:** List corresponding to filepaths of displayed parameter names.
* **`surfacefiles`:** List of file paths to surfaces (`irap binary` format)  (absolute or relative to config file).
* **`surfacenames`:** List corresponding to file paths of displayed surface names.
* **`zunit`:** z-unit for display.
* **`colors`:** List of hex colors to use. Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. `'#000000'` for black.



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
* **`segynames`:** Corresponding list of displayed seismic names.
* **`surfacefiles`:** List of file paths to Irap Binary surfaces (absolute or relative to config file).
* **`surfacenames`:** Corresponding list of displayed surface names.
* **`zunit`:** z-unit for display
* **`colors`:** List of hex colors to use. Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. `'#000000'` for black.



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

#### SwatinitQC


<!-- tabs:start -->


<!-- tab:Description -->

This plugin is used to visualize the output from [check_swatinit](https://fmu-docs.equinor.com/docs/subscript/scripts/check_swatinit.html) which is a QC tool
for Water Initialization in Eclipse runs when the `SWATINIT` keyword has been used. It is used to
quantify how much the volume changes from `SWATINIT` to `SWAT` at time zero in the dynamical model,
and help understand why it changes.




<!-- tab:Arguments -->












* **`csvfile`:** Path to an csvfile from check_swatinit. The path should be relative to the runpath
if ensemble and realization is given as input, if not the path needs to be absolute.
* **`ensemble`:** Which ensemble in `shared_settings` to visualize.
* **`realization`:** Which realization to pick from the ensemble
* **`faultlines`**: A csv file containing faultpolygons to be visualized together with the map view.
Export format from [xtgeo.xyz.polygons.dataframe](
https://xtgeo.readthedocs.io/en/latest/apiref/xtgeo.xyz.polygons.html#xtgeo.xyz.polygons.Polygons.dataframe
) [(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/01_drogon_ahm/realization-0/iter-0/share/results/polygons/toptherys--gl_faultlines_extract_postprocess.csv).



---
How to use in YAML config file:
```yaml
    - SwatinitQC:
        csvfile:  # Optional, type str.
        ensemble:  # Optional, type Union[str, NoneType].
        realization:  # Optional, type Union[int, NoneType].
        faultlines:  # Optional, type Union[str (corresponding to a path), NoneType].
```



<!-- tab:Data input -->

The `csvfile` can be generated by running the [CHECK_SWATINIT](https://fmu-docs.equinor.com/docs/ert/reference/forward_models.html?highlight=swatinit#CHECK_SWATINIT) forward model in ERT,
or with the "check_swatinit" command line tool.



<!-- tabs:end -->

</div>

<div class="plugin-doc">

#### TornadoPlotterFMU


<!-- tabs:start -->


<!-- tab:Description -->

General tornado plotter for FMU data from a csv file of responses.



<!-- tab:Arguments -->


















* **`ensemble`:** Which ensemble in `shared_settings` to visualize.
* **`csvfile`:** Relative ensemble path to csv file with responses
* **`aggregated_csvfile`:** Alternative to ensemble + csvfile with
aggregated responses. Requires REAL and ENSEMBLE columns
* **`aggregated_parameterfile`:** Necessary when aggregated_csvfile
is specified. File with sensitivity specification for each realization.
Requires columns REAL, ENSEMBLE, SENSNAME and SENSCASE.
* **`initial_response`:** Initialize plugin with this response column
visualized
* **`single_value_selectors`:** List of columns in response csv file
that should be used to select/filter data. E.g. for UNSMRY data the DATE
column can be used. For each entry a Dropdown is shown with all unique
values and a single value can be selected at a time.
* **`multi_value_selectors`:** List of columns in response csv file
to filter/select data. For each entry a Select is shown with
all unique values. Multiple values can be selected at a time,
and a tornado plot will be shown from the matching response rows.
Used e.g. for volumetrics data, to select a subset of ZONES and
REGIONS.


---
How to use in YAML config file:
```yaml
    - TornadoPlotterFMU:
        csvfile:  # Optional, type str.
        ensemble:  # Optional, type str.
        aggregated_csvfile:  # Optional, type str (corresponding to a path).
        aggregated_parameterfile:  # Optional, type str (corresponding to a path).
        initial_response:  # Optional, type str.
        single_value_selectors:  # Optional, type List[str].
        multi_value_selectors:  # Optional, type List[str].
```



<!-- tabs:end -->

</div>

<div class="plugin-doc">

#### VolumetricAnalysis


<!-- tabs:start -->


<!-- tab:Description -->

Dashboard to analyze volumetrics results from FMU ensembles, both monte carlo
and sensitivity runs are supported.

This dashboard is built with static volumetric data in mind. However both static and dynamic
volumefiles are supported as input, and the type is determined by an automatic check. To be
defined as a static source the standard FMU-format of such files must be followed.
[see FMU wiki for decription of volumetric standards](https://wiki.equinor.com/wiki/index.php/FMU_standards/Volumetrics)

The dashboard can be used as a tool to compare dynamic and static volumes.
This is done by creating sets of FIPNUM's and REGION∕ZONE's that are comparable
in volumes, and combining volumes per set. To trigger this behaviour a
fipfile with FIPNUM to REGION∕ZONE mapping information must be provided. Different formats
of this fipfile are supported [examples can be seen here](https://fmu-docs.equinor.com/docs/subscript/scripts/rmsecl_volumetrics.html#example).

The plugin behavoiur is dependent on the input files and their type (static/dynamic):
* If the input file(s) are static, different input preparations are triggered to enhance the
  analysis:
    * The fluid type is determined by the column name suffixes, either (_OIL or _GAS). This suffix
      is removed and a `FLUID_ZONE` column is added to be used as a filter or selector.
    * If total geometric volumes are included (suffix _TOTAL) they will be used to compute volumes
      from the water zone and "water" will be added to the `FLUID_ZONE` column.
    * Property columns (e.g. PORO, SW) are automatically computed from the data as long as
      relevant volumetric columns are present. NET volume and NTG can be computed from a FACIES
      column by defining which facies are non-net.
* If the input file(s) are dynamic these operations are skipped.

!> Be aware that if more than one source is given as input, only common columns between the sources
   are kept. Hence it is often preferrable to initialize the plugin multiple times dependent on the
   analysis task in question. E.g. a pure static input will allow for a detailed analysis of
   volumetric data due to the input preparations mentioned above. While a mix of both static and
   dynamic data will limit the available columns but enable comparison of these data on a
   comparable level.

Input can be given either as aggregated `csv` files or as ensemble name(s)
defined in `shared_settings` (with volumetric `csv` files stored per realization).




<!-- tab:Arguments -->



















**Using aggregated data**
* **`csvfile_vol`:** Aggregated csvfile with `REAL`, `ENSEMBLE` and `SOURCE` columns (absolute path or relative to config file).
* **`csvfile_parameters`:** Aggregated csvfile with parameter data (absolute path or relative to config file).`REAL` and `ENSEMBLE` are mandatory columns.


**Using data stored per realization**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`volfiles`:**  Key/value pair of csv files E.g. `{geogrid: geogrid--oil.csv}`.
Only relevant if `ensembles` is defined. The key (e.g. `geogrid`) will be used as `SOURCE`.
* **`volfolder`:** Local folder for the `volfiles`.


**Common settings**
* **`non_net_facies`:** List of facies which are non-net.
* **`fipfile`:** Path to a yaml-file that defines a match between FIPNUM regions
    and human readable regions, zones and etc to be used as filters.


---
How to use in YAML config file:
```yaml
    - VolumetricAnalysis:
        csvfile_vol:  # Optional, type str (corresponding to a path).
        csvfile_parameters:  # Optional, type str (corresponding to a path).
        ensembles:  # Optional, type list.
        volfiles:  # Optional, type dict.
        volfolder:  # Optional, type str.
        non_net_facies:  # Optional, type Union[typing.List[str], NoneType].
        fipfile:  # Optional, type str (corresponding to a path).
```



<!-- tab:Data input -->


?> The input files must follow FMU standards.


The input files are given to the plugin in the 'volfiles' argument. This is a dictionary
where the key will used in the SOURCE column and the value is the name of a volumetric file,
or a list of volumetric files belonging to the specific data source (e.g. geogrid).
If users have multiple csv-files from one data source e.g. geogrid_oil.csv and geogrid_gas.csv,
it is recommended to put these into a list of files for the source geogrid as such:

```yaml
volfiles:
    geogrid:
        - geogrid_oil.csv
        - geogrid_gas.csv
```

* [Example of an aggregated file for `csvfiles`](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_test_data/aggregated_data/volumes.csv).

* [Example of a file per realization that can be used with `ensembles` and `volfiles`](https://github.com/equinor/webviz-subsurface-testdata/blob/master/01_drogon_ahm/realization-0/iter-0/share/results/volumes/geogrid--vol.csv).

For sensitivity runs the sensitivity information is extracted automatically if `ensembles`is given as input, as long as `SENSCASE` and `SENSNAME` are found in `parameters.txt`.* [Example of an aggregated file to use with `csvfile_parameters`](https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_test_data/aggregated_data/parameters.csv)


**The following columns will be used as available filters, if present:**

* `ZONE`
* `REGION`
* `FACIES`
* `FIPNUM`
* `SET`
* `LICENSE`
* `SOURCE`
* `SENSNAME`
* `SENSCASE`


**Remaining columns are seen as volumetric responses.**



<!-- tabs:end -->

</div>

<div class="plugin-doc">

#### WellAnalysis


<!-- tabs:start -->


<!-- tab:Description -->

This plugin is for visualizing and analysing well data. There are different tabs
for visualizing:

* Well Production
* Well control modes and network pressures




<!-- tab:Arguments -->














* **`ensembles`:** Which ensembles in `shared_settings` to include.
* **`rel_file_pattern`:** path to `.arrow` files with summary data.
* **`gruptree_file`:** `.csv` with gruptree information.
* **`time_index`:** Frequency for the data sampling.
* **`filter_out_startswith`:** Filter out wells that starts with this string


---
How to use in YAML config file:
```yaml
    - WellAnalysis:
        ensembles:  # Optional, type Union[typing.List[str], NoneType].
        rel_file_pattern:  # Optional, type str.
        gruptree_file:  # Optional, type str.
        time_index:  # Optional, type str.
        filter_out_startswith:  # Optional, type Union[str, NoneType].
```



<!-- tab:Data input -->


**Summary data**

This plugin needs the following summary vectors to be exported:
* WOPT, WGPT and WWPT for all wells for the well overview plots
* WMCTL, WTHP and WBHP for all wells for the well control plots
* GPR for all network nodes downstream/upstream the wells

**GRUPTREE input**

`gruptree_file` is a path to a file stored per realization (e.g. in     `share/results/tables/gruptree.csv"`).

The `gruptree_file` file can be dumped to disk per realization by the `ECL2CSV` forward
model with subcommand `gruptree`. The forward model uses `ecl2df` to export a table
representation of the Eclipse network:
[Link to ecl2csv gruptree documentation.](https://equinor.github.io/ecl2df/usage/gruptree.html).

**time_index**

This is the sampling interval of the summary data. It is `yearly` by default, but can be set
to f.ex `monthly` if needed.

**filter_out_startswith**

Filter out well names that starts with this. Can f.ex be "R_" in order to filter out RFT wells
without production.



<!-- tabs:end -->

</div>

<div class="plugin-doc">

#### WellCompletions


<!-- tabs:start -->


<!-- tab:Description -->

Visualizes well completions data per well coming from export of the Eclipse COMPDAT output.     Data is grouped per well and zone and can be filtered accoring to flexible well categories.




<!-- tab:Arguments -->





















* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`compdat_file`:** `.csv` file with compdat data per realization
* **`well_connection_status_file`:** `.parquet` file with well connection status per realization
* **`zone_layer_mapping_file`:** `.lyr` file specifying the zone ➔ layer mapping
* **`stratigraphy_file`:** `.json` file defining the stratigraphic levels
* **`well_attributes_file`:** `.json` file with categorical well attributes
* **`kh_unit`:** e.g. mD·m, will try to extract from eclipse files if defaulted
* **`kh_decimal_places`:**



---
How to use in YAML config file:
```yaml
    - WellCompletions:
        ensembles:  # Required, type list.
        compdat_file:  # Optional, type str.
        well_connection_status_file:  # Optional, type str.
        zone_layer_mapping_file:  # Optional, type str.
        stratigraphy_file:  # Optional, type str.
        well_attributes_file:  # Optional, type str.
        kh_unit:  # Optional, type str.
        kh_decimal_places:  # Optional, type int.
```



<!-- tab:Data input -->

The minimum requirement is to define `ensembles`.

**COMPDAT input**

`compdat_file` is a path to a file stored per realization (e.g. in     `share/results/tables/compdat.csv`). This file can be exported to disk per realization by using
the `ECL2CSV` forward model in ERT with subcommand `compdat`. [Link to ecl2csv compdat documentation.](https://equinor.github.io/ecl2df/usage/compdat.html)

The connection status history of each cell is not necessarily complete in the `ecl2df` export,
because status changes resulting from ACTIONs can't be extracted from the Eclipse input
files. If the `ecl2df` export is good, it is recommended to use that. This will often be the
case for history runs. But if not, an alternative way of extracting the data is described in
the next section.

**Well Connection status input**

The `well_connection_status_file` is a path to a file stored per realization (e.g. in     `share/results/tables/wellconnstatus.csv`. This file can be exported to disk per realization
by using the `ECL2CSV` forward model in ERT with subcommand `wellconnstatus`.  [Link to ecl2csv wellconnstatus documentation.](https://equinor.github.io/ecl2df/usage/wellconnstatus.html)

This approach uses the CPI summary data to create a well connection status history: for
each well connection cell there is one line for each time the connection is opened or closed.
This data is sparse, but be aware that the CPI summary data can potentially become very large.

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
                "name": "ZoneA.1"
            },
            {
                "name": "ZoneA.2"
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
                "name": "ZoneB.2",
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

<div class="plugin-doc">

#### WellLogViewer


<!-- tabs:start -->


<!-- tab:Description -->

Uses [videx-welllog](https://github.com/equinor/videx-wellog) to visualize well logs
    from files stored in RMS well format.

?> Currently tracks for visualizing discrete logs are not included. This will
be added in later releases.




<!-- tab:Arguments -->























* **`wellfolder`:** Path to a folder with well files stored in RMS well format.
* **`wellsuffix`:** File suffix of well files
* **`logtemplates`:** List of yaml based log template configurations.     See the data section for description of the format.
* **`mdlog`:** Name of the md log. If not specified, MD will be calculated.
* **`well_tvdmin`:** Truncate well data values above this depth.
* **`well_tvdmax`:** Truncate well data values below this depth.
* **`well_downsample_interval`:** Sampling interval used for coarsening a well trajectory
* **`colortables`:** Color tables on json format. See https://git.io/JDLyb     for an example file.
* **`initial_settings`:** Configuration for initializing the plugin with various     properties set. All properties are optional.
    See the data section for available properties.



---
How to use in YAML config file:
```yaml
    - WellLogViewer:
        wellfolder:  # Required, type str (corresponding to a path).
        logtemplates:  # Required, type List[str (corresponding to a path)].
        colortables:  # Optional, type str (corresponding to a path).
        wellsuffix:  # Optional, type str.
        mdlog:  # Optional, type str.
        well_tvdmin:  # Optional, type Union[int, float].
        well_tvdmax:  # Optional, type Union[int, float].
        well_downsample_interval:  # Optional, type int.
        initial_settings:  # Optional, type Dict.
```



<!-- tab:Data input -->


?> The format and documentation of the log template configuration will be improved in later releases. A small configuration sample is provided below.

```yaml
name: All logs # Name of the log template
scale:
  primary: MD # Which reference track to visualize as default (MD/TVD)
  allowSecondary: False # Set to True to show both MD and TVD reference tracks.
tracks: # The list of log tracks
  - title: Porosity # Optional title of log track
    plots: # List of which logs to include in the track
      - name: PHIT # Upper case name of log
        type: area # Type of visualiation (area, line, linestep, dot)
        color: green # Color of log
      - name: PHIT_ORIG
        type: line
  - plots:
      - name: ZONE
        type: area
  - plots:
      - name: FACIES
        type: area
  - plots:
      - name: VSH
        type: area
  - plots:
      - name: SW
        type: dot
styles: # List of styles that can be added to tracks
```


Format of the `initial_settings` argument:
```yaml
        initial_settings:
            well: str # Name of well
            logtemplate: str # Name of log template
```



<!-- tabs:end -->

</div>
