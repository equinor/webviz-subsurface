
### webviz-subsurface package

?> :bookmark: This documentation is valid for version `0.2.15` of `webviz-subsurface`.



---

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


