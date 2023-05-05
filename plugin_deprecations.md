
### webviz-subsurface package

?> :bookmark: This documentation is valid for version `0.2.19` of `webviz-subsurface`.



---

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

#### WellCompletions

<details>
  <summary markdown="span"> :warning: Plugin 'WellCompletions' has been deprecated.</summary>

  This plugin has been replaced by the `WellCompletion` plugin (without the `s`) which is based on the `wellcompletionsdata` export from `ecl2df`. The new plugin is faster and has more functionality. 
</details>


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



