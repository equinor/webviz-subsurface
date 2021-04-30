## Deprecated plugins
### Plugin project webviz-subsurface

?> :bookmark: This documentation is valid for version `0.2.2` of `webviz-subsurface`. 

   
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

##### HorizonUncertaintyViewer

> :warning: Plugin 'HorizonUncertaintyViewer' has been deprecated.

Relevant functionality is implemented in the StructuralUncertainty plugin.



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

##### WellCrossSection

> :warning: Plugin 'WellCrossSection' has been deprecated.

Relevant functionality is implemented in the StructuralUncertainty plugin.



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

##### WellCrossSectionFMU

> :warning: Plugin 'WellCrossSectionFMU' has been deprecated.

Relevant functionality is implemented in the StructuralUncertainty plugin.



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


