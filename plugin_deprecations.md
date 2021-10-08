
### webviz-subsurface package

?> :bookmark: This documentation is valid for version `0.2.6` of `webviz-subsurface`.



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



