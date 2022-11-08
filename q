commit 7d1c9d8b79a8b4d2d88b00f5d5cdf5e6c4070b48
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Tue Nov 8 11:57:20 2022 +0100

    arrow implementation and improvements to TimeseriesOneByOne

commit b6e7763c21e5f34865395290bd8207b1a6e9f39b
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Tue Nov 8 10:32:32 2022 +0100

    `GroupTree`: Improved terminal_node filtering (#1152)
    
    * Improved terminal_node filtering
    
    * Pinned mypy to <0.990
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 59a1e103be3155416c746d3d617934d377f80f1f
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Oct 27 10:56:26 2022 +0200

    Metadata functionality in `EnsembleTableProvider` (#1135)

commit 7c35594495cebb4d57584e7c2f8b347751b9f778
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Wed Oct 26 12:02:37 2022 +0200

    More flexibility in `GroupTree` (#1138)
    
    * Two new parameters in GroupTree for more flexibility, terminal_node and excl_well_startswith
    
    * Implemented new function get_filtered_dataframe in gruptree_model
    
    * New input excl_well_endswith
    
    * Improved Exception message for injection nodes in BRANPROP trees
    
    * Started on unit tests for the gruptree model
    
    * Fixed CI workflow issues
    
    * Improved tests with fixture creating the gruptree model
    
    * Improved handling of injection for BRANPROP nodes
    
    * Made terminal_node optional in get_filtered_dataframe
    
    * New input parameter tree_type which is GRUPTREE by default, and some other improvements
    
    * Relaxed the requirements on summary vectors
    
    * New StrEnum DataType for oilrate, gasrate etc
    
    * Eased the requirement on node summary vectors, they are now optional
    
    * New type EdgeOrNode
    
    * Small docstring update
    
    * Implemented mock GruptreeModel class with some new tests
    
    * Allowed tree_type to be defaulted in gruptree_model, in which case the tree is automatically selected
    
    * Changelog entry
    
    * Small update to comment
    
    * Set back scipy version in setup.py and installed v 1.9.2 in CI workflow
    
    * Updated CI workflow
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 1ad6de4249c3d317f1752fa4b1f8c26c0c49c0c3
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Mon Oct 10 23:12:31 2022 +0200

    Prepare release (#1132)

commit a077e475c2fdbd8124821b780e696135f119b69d
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Wed Oct 5 12:07:33 2022 +0200

    Fix `ConversionError` in `callback_typecheck`. (#1129)
    
    * Fix typecheck error
    
    * Updated type hinting and added stretch=True
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 99212d61fa7cb9e808b592ca22eeb6db375b6f90
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Wed Oct 5 10:21:14 2022 +0200

    Fix `pandas` `FutureWarnings` (#1128)

commit eb0a7e3dd7ed3d700bc3c5d9115ce5100c98a94e
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Tue Oct 4 09:58:16 2022 +0200

    Option to remove header from parameter filter (#1125)
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit b3702ca319ccb295e22d356d75a3e2e25ea2209b
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Mon Oct 3 15:40:43 2022 +0200

    Fix initial open state to prevent undefined type (#1121)
    
    open is not required prop for wcc.Dialog, thus initial value was undefined and type in Python was `None`. Resolved by defining initial state False.

commit ea2f9550c2ff42685195213646146374b368fd56
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Sep 29 16:15:44 2022 +0200

    `RftPlotter` to WLF (#1113)
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit f9662a272ef1cefd223d2d9e7abb756ed45bd029
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Thu Sep 29 15:47:32 2022 +0200

    Do not use pandas dataframe as argument to webvizstore function (#1061)

commit 939fa89a56cdb3013241c93bf3e2a10278e89d26
Author: EirikPeirik <104941095+EirikPeirik@users.noreply.github.com>
Date:   Thu Sep 29 13:53:08 2022 +0200

    `ProdMisfit` moved to WLF (#1085)
    
    Co-authored-by: Eirik Sundby Håland (OG SUB RPE) <ehala@be-linrgsn089.be.statoil.no>
    Co-authored-by: Roger Nybø <rnyb@equinor.com>

commit deef26fe2c4bf94bb1f7c2325c5fe24a3f1d77ca
Author: Viktoria Vahlin <107865041+vvahlin@users.noreply.github.com>
Date:   Thu Sep 29 13:25:34 2022 +0200

    Parameter vs parameter (#1083)
    
    Co-authored-by: Kasper Seglem (OG SUB RPE) <kseg@be-linrgsn101.be.statoil.no>
    Co-authored-by: Eirik Sundby Håland (OG SUB RPE) <ehala@be-linrgsn025.be.statoil.no>
    Co-authored-by: JinCheng2022 <107854035+JinCheng2022@users.noreply.github.com>

commit c2e073f04c2f2b7459cb33977b937a9af6663652
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Thu Sep 29 13:02:07 2022 +0200

    Fix `pandas` `FutureWarnings` (#1116)

commit f162f0f623acafcc7bfec708c13ad6d5ce463d63
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Wed Sep 28 20:56:23 2022 +0200

    Minor fixes to `MapViewerFMU` (#1114)
    
    * minor fixes
    
    * minor fixes
    
    Co-authored-by: Hans Kallekleiv <HansKallekleiv@users.noreply.github.com>

commit 4fe0e9ebd4c752722cdbda70049c23f96440ed8d
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Wed Sep 28 12:12:06 2022 +0200

    Update MapViewerFMU to new changes in DeckGLMap components (#1118)

commit b19406ea7fe3e1d4f623b09b43b34aebe3580c3e
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Tue Sep 27 19:04:59 2022 +0200

    Fix mypy errors in Tornado plot (#1117)

commit 89cd868d4be45ef0d312cbd943476993b1957d89
Author: Viktoria Vahlin <107865041+vvahlin@users.noreply.github.com>
Date:   Thu Sep 22 12:41:55 2022 +0200

    Tornado plotter (#1092)
    
    Converted `TornadoPlotterFMU` plugin to WLF
    Co-authored-by: Viktoria Christine Vahlin (OG SUB RPE) <vvah@be-linrgsn154.be.statoil.no>
    Co-authored-by: JinCheng2022 <107854035+JinCheng2022@users.noreply.github.com>
    Co-authored-by: Ruben <ruben.thoms@ceetronsolutions.com>

commit 7ff7635cd15dbbd65e42e753e8d1e1e67cebe922
Author: JinCheng2022 <107854035+JinCheng2022@users.noreply.github.com>
Date:   Thu Sep 22 09:15:09 2022 +0200

    Pvt trail (#1078)
    
    *Refactored PVT plugin to new layout framework (WLF)
    
    Co-authored-by: Kasper Seglem (OG SUB RPE) <kseg@be-linrgsn101.be.statoil.no>
    Co-authored-by: Eirik Sundby Håland (OG SUB RPE) <ehala@be-linrgsn025.be.statoil.no>
    Co-authored-by: Ruben <ruben.thoms@ceetronsolutions.com>

commit e94ca641a691d262ee42c244470bf337dc2f379d
Author: JinCheng2022 <107854035+JinCheng2022@users.noreply.github.com>
Date:   Wed Sep 21 11:06:55 2022 +0200

    Refactor SimulationTimeSeries plugin to WLF  (#1086)
    
    - Convert the plugin to use `WLF` for enhanced layout and improved code separation.
    - Number of maximum allowed initial selected vector increased from 3 to 5.

commit 6d093ef0473d574edb681c64f1ee04a02175105d
Author: EirikPeirik <104941095+EirikPeirik@users.noreply.github.com>
Date:   Thu Sep 15 10:16:27 2022 +0200

    Well analysis trail (#1089)
    
    * Refactored the code according to the WLF best practice
    
    * Removed well attributes filter, and more code improvements
    
    * Refactored code again, putting figures in view utils folders
    
    * Introduced a view element and got rid of the last store
    
    * Simplified tour_steps and removed some imports from init files
    
    * Added label to layout options checkbox
    
    * Implemented a view element also for the well control view
    
    * Added changelog
    
    * Removed the error layout
    
    * Implemented StrEnum and callback_typecheck
    
    * Fixed bug in callback so that only layout is updated if data is unchanged
    
    * Implemented new callback_typecheck that handles Optional type
    
    * Minor updates to tour_steps
    
    Co-authored-by: Eirik Sundby Håland (OG SUB RPE) <ehala@be-linrgsn025.be.statoil.no>
    Co-authored-by: Eirik Sundby Håland (OG SUB RPE) <ehala@be-linrgsn089.be.statoil.no>
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 251810d452a5b53b6f3a00a8964f496c262ec476
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Sep 15 09:20:32 2022 +0200

    New implementation of the `WellCompletion` plugin (with WLF). (#1058)
    
    * Initial commit
    
    started on reading of arrow files
    
    Added WellCompletionNew
    
    Implemented using EnsembleTableProvider to load arrow files
    
    Started on the create_ensemble_dataset function
    
    First implementation of create_ensemble_dataset
    
    Some improvements to create dataset code
    
    started implementing views
    
    Implemented WLF structure
    
    Implemented single realization
    
    Implemented a view element
    
    Wrote main plugin docstring
    
    * Started implementing portable
    
    * started implementing StratigraphyModel
    
    * Stratigraphy model and portable
    
    * webviz-store also on get_unit
    
    * Docstrings and some changes to what is returned if file is not found
    
    * Docstrings
    
    * Cleaned up naming confusion
    
    * logger and timer
    
    * Renamed the plugin WellCompletion, removed kh arguments
    
    * Removed print
    
    * Sorting
    
    * Deprecated old plugin
    
    * changelog entry
    
    * Formatting
    
    * Review related changes
    
    * Refactored the code according to new WLF best practice
    
    * Removed plugin_ids file and added str and Enum to Ids.
    
    * Moved Ids class into plugin class
    
    * Added tour steps and removed imports from _views
    
    * StrEnum and callback_typecheck
    
    * callback_typecheck imported from webviz_config.utils
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 271cc5f47206a6c2663507fa1c396a78df1de203
Author: JinCheng2022 <107854035+JinCheng2022@users.noreply.github.com>
Date:   Wed Sep 14 14:08:16 2022 +0200

    `GroupTree` to WLF (#1080)
    
    * Refactored the code in line with new WLF best practice
    
    * Added missing init files
    
    * renamed business_logic file
    
    * Fixed grouptree tests
    
    * Ids to Enums
    
    * Review related updates
    
    * Removed Settings groups from init functions
    
    * Fixed group_tree_component_id problem
    
    * Removed imports from _views init function
    
    * StrEnum and callback_typecheck
    
    * Added a comment about callback_typecheck
    
    * Implemented callback_checktype with Optional
    
    Co-authored-by: Jincheng Liu (OG SUB RPE) <jliu@be-linrgsn057.be.statoil.no>
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 1c4692728c70df53ab93deefa68fa667a704f617
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Tue Sep 13 09:16:35 2022 +0200

    Remove Python `3.6` and `3.7` support (#1109)

commit b9a29e31c400291f90db0e93ca91dfbb3c83ffb4
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Wed Aug 24 08:18:09 2022 +0200

    Bugfix in `ParameterResponseCorrelation` (#1107)
    
    * Removed if-statement for filters layout
    
    * Simplified layout and added changelog entry
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 15815e282b05fd6640f4ba40f9a9d4c4e0b68da1
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Wed Aug 10 15:28:50 2022 +0200

    Fixed issue with ambigious truth of `pd.Series` in `EnsembleSummaryProvider` (#1094)

commit 6f4bb4185491fe920eb91ec64131ee49d2a12e26
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Fri Aug 5 10:49:41 2022 +0200

    Support `dash>=2.6` (#1098)

commit e84c30a7f4396958e37600f014307572f980b0ce
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Thu Aug 4 11:28:15 2022 +0200

    removed requirement of "" around wildcarded paths in smry2arrow_batch (#1097)
    
    Removed requirement of "" around wildcarded paths in smry2arrow_batch

commit 65ca35eb21c4d7a7c839e38c8d3ae9eda3d51495
Author: rubenthoms <69145689+rubenthoms@users.noreply.github.com>
Date:   Wed Jul 20 09:37:56 2022 +0200

    Pinned `dash` to `<2.6.0` in order to keep `_NoUpdate` class available. (#1087)

commit f28f9998a6a4044fdf0341b1463aaa8f87952d10
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Jun 30 14:32:07 2022 +0200

    New implementation of `EnsembleTableProvider` (#1057)
    
    * Initial commit for new ensemble_table_provider
    
    * Added method docstrings and removed the EnsembleTableProviderSet class
    
    * Improved tests
    
    * Removed Table provider set from parameter response correlation
    
    * Adapted 4 plugins to new table provider and added a new function in the table provider factory
    
    * Adapted tornado_plotter_fmu to new table provider
    
    * Improved table provider tests
    
    * Worked more on table provider tests
    
    * one more test and updated docstring
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 824672eed99783f8adab6c918b889f9d8272fd18
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Tue Jun 28 09:14:47 2022 +0200

    Prepare release (#1059)

commit 0f05a533bd0e6ae2ab18148eb80a467744ca3247
Author: Roger Nybø <51825893+rnyb@users.noreply.github.com>
Date:   Tue Jun 14 09:58:08 2022 +0200

    `ProdMisfit`- bugfix related to the use of excl_name_contains. (#1055)

commit d74a8694804c4a3688f8defdf5cc2b39da2563ed
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Thu Jun 9 16:16:04 2022 +0200

    Fix relative path issue in SwatinitQC (#1053)
    
    * Fix relative path issue in SwatinitQC
    
    * changelog

commit 20afc6d16fd0221b1c8ae681a2a71d8f5a40662a
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Wed Jun 8 10:02:40 2022 +0200

    Fix for layer changes in map component (#1046)
    
    * Fix for layer changes in map component

commit 50266076b133a671bf39f79fc46279edffe8b73d
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Sun May 29 20:53:41 2022 +0200

    Add color tables to `MapViewer` (#1037)

commit 970e609c24798cd500739813b2bd0555e75c3dd4
Author: Roger Nybø <51825893+rnyb@users.noreply.github.com>
Date:   Sun May 29 20:12:48 2022 +0200

    `BhpQc` - Read from `.arrow` files instead of `.UNSMRY` files (#1028)

commit a8d3646501d9c2d8dc1a65f3f3cec534858b61a2
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Sun May 29 19:36:22 2022 +0200

    Remove `pydeck` dependency (#1035)

commit 7e8ad2ab48464f08e790e26d0844c02ac5d2299b
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Sun May 29 19:13:31 2022 +0200

    Add missing dependency upstream (#1042)

commit 9bb7e3781ef68a24279ce7875c53fcafcfb3de7c
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Fri May 27 11:45:33 2022 +0200

    Increased maximum number of selected vectors in SimulationTimeSeries (#1041)

commit b66f55a28df4241969d09ae0edcd8c03b3b4ebcf
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Fri May 27 08:36:09 2022 +0200

    `WellAnalysis` improvements (#1020)
    
    * Updated repr string
    
    * Implemented pressure plot mode type
    
    * Handling gruptrees that are different over realizations
    
    * New type NodeType and handling of interpolated wmctl values
    
    * Removed TERMINAL_NODE type
    
    * Well attribute filter
    
    * Refactored well_attributes_model a bit and extended the tests
    
    * Handling of undefined well attributes
    
    * Implemented production after date with a date selector dropdown
    
    * Prod after date also for the area chart
    
    * Implemented ChartType Enum
    
    * Date in title and clearable false on response selector
    
    * Changelog entry
    
    * Fixed the problem of well changing when changing ensemble
    
    * Bugfix: gruptree_model was crashing if file did not exist
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 6c56649299cf8e51400a94ef81ea29356ea7bf26
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Wed May 25 17:13:02 2022 +0200

    New data provider in `ParameterResponseCorrelation` (#1030)
    
    * added function to match column_keys
    
    * Implemented new data provider
    
    * Updated docstring
    
    * Moved get_matching_vector_names function to new utils module
    
    * changelog entry
    
    * Error message when column keys are not matching any vectors
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 616ee7c70cf74e02c172342c70c3e4447025d6e8
Author: Roger Nybø <51825893+rnyb@users.noreply.github.com>
Date:   Mon May 23 18:15:12 2022 +0200

    `SeismicMisfit` - support new polygon header standard (#1017)

commit 18318bf396068d5598cc8e623455a6224c8f7517
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Mon May 23 15:35:22 2022 +0200

    `ParameterResponseCorrelation`: parameter filter, correlation and aggregation selectors, and correlation cut-off (#936)

commit fe697ef0212a984779dec9048f4fd858e84cd4d8
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Mon May 23 14:24:52 2022 +0200

    Use latest official `webviz-subsurface-components` release in CI (#1036)

commit 32b16382dd1463c91025cf0a72a460c2710fd4c9
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Mon May 23 08:53:27 2022 +0200

    Add Python 3.10 to CI (#897)

commit 994dca86b85a487dd952d90f4cc53c3ca4dcdc02
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Thu May 19 15:30:39 2022 +0200

    Fix new `pylint` and `dash` test error (#1032)

commit 8dc83877e23f3d0013acf5afc95dc1f1a6808317
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Thu May 5 20:49:41 2022 +0200

    Prepare release (#1019)

commit 4026d92382de3c69ffdbbe89706fe9d0a9b7e62d
Author: Sigurd Pettersen <sigurd.pettersen@ceetronsolutions.com>
Date:   Mon May 2 21:07:09 2022 +0200

    Improved error reporting for `.arrow` files where dates are not monotonically increasing (#1015)

commit 4cce8cdfe33e9c0945a32fbc8aed15878e92d939
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Thu Apr 28 15:29:24 2022 +0200

    Various bugfixes (#1014)
    
    * various bugfixes

commit 9362b3374d53146608eea613b52d80ecde769b5c
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Wed Apr 27 13:57:44 2022 +0200

    Expose surface folder as an argument in `MapViewerFMU` (#1013)
    
    * Expose surface folder as argument in MapViewerFMU

commit 4e572eee56a01132f10f75c260333feb0149f38f
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Mon Apr 25 18:46:24 2022 +0200

    Fix `CHANGELOG.md` (#1012)

commit 831bef5071d66c975979084023995cfad6100123
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Mon Apr 25 12:48:30 2022 +0200

    Well attribute tests with mock data (#1010)
    
    * Well attribute tests with mock data
    
    * added pytest-mock to test requirements
    
    * bugfix
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 89d76ddd86342ba803a80301c80b5226607a1f66
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Sun Apr 24 22:17:47 2022 +0200

    Fix store for `ProdMisfit` (#1009)

commit 08cc8ee08549aea9577bfce559ecdc4e6f1978a4
Author: Roger Nybø <51825893+rnyb@users.noreply.github.com>
Date:   Sat Apr 23 08:31:13 2022 +0200

    New `ProdMisfit` plugin (#938)

commit 56a9607b4f4607620799152630c8014f14e16eff
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Fri Apr 22 11:54:37 2022 +0200

    General `WellAttributesModel` class (#1006)
    
    * New class WellAttributesModel
    
    * function that returns well attributes as dataframe
    
    * dataframe_melted function
    
    * Capital letters in dataframes and logging of well attributes file used
    
    * First saving the raw dict, then transforming it to simple form
    
    * ValueError changed to NotImplementedError
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit b09884d8abac086633c159f31283cb97412de72f
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Thu Apr 21 12:15:42 2022 +0200

    Fixes issues with just one parameter and for aggregated data in ParameterResponseCorrelation (#1001)

commit 7e8b4d390b3138194ab59807c3692be0a9dc342b
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Apr 21 08:03:27 2022 +0200

     `GroupTree` improvements (#999)
    
    * implemented property types
    
    * LayoutElements class
    
    * Using general class GruptreeModel to load gruptree data
    
    * Fixed tour_steps
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit df5e762f2b39dc06854b2fb521e301c61ea8a1a0
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Wed Apr 20 20:12:34 2022 +0200

    Fix test input argument for `SurfaceWithGridCrossSection` (#1005)

commit 3b8be31c38f46e1137d39cf9feb2695655de17ef
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Thu Apr 7 23:51:33 2022 +0200

    Prepare release (#1002)

commit e25e8cb82b7e206aaad7837f2c5613080a2636b7
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Wed Mar 30 09:19:53 2022 +0200

    Add backwards compatibility for older portables using `ParameterAnalysis` and `PropertyStatistic` (#995)
    
    * add backwards compatibility for older portables
    
    * get run_mode from WEBVIZ_INSTANCE_INFO

commit c72a9e2fb00e32c74b32c2d4b29ec6d09823ebd1
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Wed Mar 30 08:45:38 2022 +0200

    Bugfix `VolumetricAnalysis` - tornados hidden if both dynamic and static sources (#996)
    
    * bugfix tornados not appering if both dynamic and static sources

commit c5825b02946f84b53245df7a843beb23cf1330ea
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Tue Mar 29 16:30:55 2022 +0200

    Temporarily pin `werkzeug` in CI (#997)

commit 5dac1edd8fab54883f9b86a1b63b6048d6c890ef
Author: Sigurd Pettersen <sigurd.pettersen@ceetronsolutions.com>
Date:   Mon Mar 28 09:29:06 2022 +0200

    Avoid copying surfaces when using `MapViewerFMU` in non-portable mode (#986)

commit b5ef68c846b75921cb099d52d230bd0a60f3f637
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Sun Mar 27 20:20:51 2022 +0200

    Arrow support and other improvements to `ParameterAnalysis` and `PropertyStatistics` (#988)
    
    * Arrow support and fixes to ParameterAnalysis and PropertyStatistics
    
    * use table provider for aggregated smry [deploy test]
    
    * reintroduce column_keys argument for filtering of available vectors [deploy test]
    
    * some bugfixes
    
    * workaround for flaky test [deploy test]
    
    * [deploy test]

commit 272496df43d3b4de2e66b96c6277cbd4323d779c
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Sun Mar 27 11:03:05 2022 +0200

    New Water Initialization QC plugin `SwatinitQC` (#987)
    
    * New Water Initialization QC plugin
    
    * logarithic colors for PERMX and information in wcc.dialog

commit 452fc6ca6938c9c9851d35d8be44998288ed38a2
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Fri Mar 25 17:47:21 2022 +0100

    Place VectorCalculator in Div with fixed height (#989)
    
    Place in div with fixed height for new VectorCalculator refactoring.
    Possible to control/adjust height of VectorCalculaotr

commit d2b381f662cb30330f6cceba50d9f720bccef0a2
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Fri Mar 25 16:16:59 2022 +0100

    Update according to latest `pylint` (#991)

commit 687a5b36c3b9ecced8b3f559294f96a975baf7a6
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Tue Mar 22 14:03:07 2022 +0100

    Well analysis plugin (#981)
    
    * Basic file structure of new plugin
    
    * implemented the summary data provider
    
    * main layout for well control tab
    
    * well control layout in separate file
    
    * factored out well overview layout in separate file
    
    * split callbacks on two files
    
    * added well_control_figure
    
    * added node info code
    
    * gruptree model class implemented
    
    * started implementing the well control callbacks
    
    * Well control plot implemented
    
    * basic setup for the well overview charts
    
    * first version of the well overview barchart
    
    * chart type buttons logic implemented
    
    * started implementing pie charts and many other improvements
    
    * pie chart implemented
    
    * merged prod plots into one class
    
    * implemented display of only charttype settings
    
    * implemented area chart
    
    * Well filter implemented
    
    * Improved figure formatting
    
    * network pressures not added multiple times if they are in multiple networks
    
    * plugin docstring and renamed _ensemble_data.py to _ensemble_well_analysis_data.py
    
    * implemented webvizstore
    
    * standardized oil, water, gas colors
    
    * docstrings and some improvements
    
    * plot formatting without reloading the data
    
    * improved class docstring
    
    * Changelog entry
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 08335cfb094c588dd32a46f228cc70bfc434471b
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Mon Mar 21 10:32:28 2022 +0100

    Update `WellLogViewer` data format to latest version (#985)
    
    * Update WellLogViewer data format to latest version
    
    * Update CHANGELOG.md
    
    Co-authored-by: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
    
    Co-authored-by: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>

commit ef0d69f8ff952ce675b28b9bfff0dadf1cd46e7c
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Mon Mar 14 13:20:54 2022 +0100

    Prepare release (#983)

commit a9f3145a2da3b3063552aed6cfed1785829ce82e
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Mon Mar 14 09:31:55 2022 +0100

    Deprecate `SurfaceViewerFMU` (#980)

commit cf0e90bef4a02cac5d2d69b73805c043381b2b5b
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Fri Mar 11 15:02:19 2022 +0100

    Fix documentation in MapViewer (#975)

commit d57bc2e697b0329c01dc24ef97cc7af0aea1228e
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Fri Feb 25 17:45:07 2022 +0100

    Handle missing well picks (#977)

commit 993b08c64a0772699b14a07bc1ca4a8d67ea491d
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Fri Feb 25 13:40:29 2022 +0100

    Handle covisualizations of static and dynamic maps (#976)

commit cfde8751429058663d2c8850d25024b4fb8aadaf
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Thu Feb 24 22:43:19 2022 +0100

    Replace modals with `wcc.Dialog` in `StructuralUncertainty` (#970)

commit f717fa094c550e99443f4aeae7842ea5f63fe397
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Thu Feb 24 21:43:49 2022 +0100

    Allow filtered subset of surface names for multiple attributes in StructuralUncertainty (#965)

commit 94a54c68fd22f1461169b6503031fb219a2885b2
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Thu Feb 24 20:59:34 2022 +0100

    Map Viewer Plugin (#971)
    
    Co-Authored-By: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
    Co-Authored-By: Sigurd Pettersen <sigurd.pettersen@ceetronsolutions.com>
    
    Co-authored-by: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
    Co-authored-by: Sigurd Pettersen <sigurd.pettersen@ceetronsolutions.com>

commit 7372653bea0df3abce7cc098f1f4e567f9aa6bf7
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Thu Feb 24 20:22:38 2022 +0100

    Two bugfxes in VolumetricAnalysis (#972)

commit ec067f315d24a2de3949b126ebce6850812fd44c
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Thu Feb 24 09:51:40 2022 +0100

    SimulationTimeSeries: Handle defaulted options in deprecation check (#969)

commit 8ab46229236c6eb6e82d6796536c9cb72e9f1af2
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Wed Feb 23 14:39:59 2022 +0100

    Disable rangeslider marks in cross-section plugins (#958)
    
    * Disable rangeslider marks in cross-section plugins

commit 4f7d31d8c95cfda9dd6fd2713bb16404a1d3e4e4
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Wed Feb 23 10:35:58 2022 +0100

    Improve error message when there are zero valid realizations (#961)

commit 2d63edfab5105a6cf279921600db46962eb3a0b0
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Mon Feb 21 14:48:19 2022 +0100

    Zone filter and parameter filter in `RftPlotter` (#949)
    
    * Map zone filter functionality
    
    * Added date to title
    
    * parameter filter in parameter response tab
    
    * Sorting observations by MD instead of TVD in the errorplot
    
    * Depth option in the formations plot in the paramresponse tab
    
    * changelog entry
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 172d6890fe07d6dc38a39abfaa52fcb42b5b55d0
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Wed Feb 16 18:05:48 2022 +0100

    Replace modal with draggable dialog for VectorCalculator (#960)
    
    Replace the Modal-component from Dash Bootstrap Components with new draggable Dialog-component in wcc.

commit fc22e36c3228b25932ccdbd28abb13b34850c406
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Fri Feb 11 10:24:29 2022 +0100

    Add list of vectors as user input for `SimulationTimeSeries` (#956)
    
    - Add list of vectors as user input for initially selected vectors.
    - Deprecate usage of {vector1, vector2, vector3}
    - Add ValueError for missing vectors

commit 9609bb0403e92e0ce2dcad6f681cd15960f876f8
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Fri Feb 11 08:25:02 2022 +0100

    Delta relative to date within ensemble `SimulationTimeSeries` (#951)
    
    Calculate delta relative to date within ensemble for SimulationTimeSeries-plugin.
    
    - Selectable dates in dropdown
    - Calculate vector data in dataframes relative to selected date
    - Calculate statistics afterwards, i.e. "resetting" the statistics calculation!

commit 1785f150f66fd1d3f3c6b08067787522dede9e86
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Feb 10 11:54:02 2022 +0100

    `WellCompletion` handling different zone → layer mappings over realizations (#944)
    
    * Import the zone->layer mappings for all realizations and return the data as a dataframe
    
    * merge the zone->layer dataframe with the compdat data on layer and realization
    
    * changelog entry
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 106c5c926eae828e4be59310fe22b98fa43ad512
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Wed Feb 9 15:56:38 2022 +0100

    User defined vector definition in SimulationTimeSeries plugin (#940)
    
    - Added configurable user defined vector definitions.
    - Changed vector annotation from "AVG_" with suffix "R" and "INTVL_" to "PER_DAY_" and "PER_INTVL_". Retrieve `VectorDefinitions` via Python-API for `webviz-subsurface-components`.

commit 32bb6b074b84786ae13997253120013eba595c73
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Wed Feb 9 12:30:17 2022 +0100

    Prepare release (#952)

commit 927ef9ab071b59a0532dc5ba4c79a3a9ae9290d4
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Wed Feb 9 12:29:26 2022 +0100

    Temp. CI/CD workaround `statsmodels` (#953)

commit ce18444470c3b321ed53977fa77ccc9e8dae841d
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Mon Jan 31 14:51:23 2022 +0100

    Adjustments in  `RftPlotter` due to changes in `ParametersModel` (#945)
    
    * Pass dummy dataframe to ParametersModel
    
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 415d8697bdba9c999bffab6a8286e957b46a2ffb
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Mon Jan 31 11:46:20 2022 +0100

    Update according to new `black` version (#947)

commit 0fd30b1f6e82d2a4bb05e6725729567e0d8ff102
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Fri Jan 28 13:38:58 2022 +0100

    Fix hover info for observation trace in `SimulationTimeSeries` (#937)

commit e759bc691a39b376570a0e4f0197e6f97853508a
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Fri Jan 28 13:24:47 2022 +0100

    Fix `is_integer()` issue in `ParameterFilter` (#939)

commit c73a699e1e31b2efa384cba3e0b8ad5f2d1cb586
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Thu Jan 20 22:43:20 2022 +0100

    Deprecate `ReservoirSimulationTimeSeries` (#935)

commit 8cebeb1ae60cdb5cfb7fe0e2a127c3ec609addf4
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Thu Jan 20 21:48:48 2022 +0100

    Bugfixes and improvements to `ParameterFilter` and `ParameterAnalysis` (#924)
    
    Co-authored-by: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>

commit 996b773684e1799cb24b79981a270eee7bbc00b7
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Thu Jan 20 21:36:39 2022 +0100

    Don't skip `SENSNAME` `ref` if multiple realizations in tornado (#929)

commit 2011f0e7d537ee57b13b38af68d3c2482cde4a93
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Jan 20 21:08:35 2022 +0100

    `RftPlotter` fix: Handle correlate function returning `NaN` values (#932)

commit dab94696d2c6c6af6c0ca4404a44e02818f3970d
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Thu Jan 20 17:42:20 2022 +0100

    Fix: correct labels in tornado when both cases are on same side of ref (#934)

commit 05b1c8ea7813e8c0ad0f10c1f82039994e13c61b
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Thu Jan 20 16:44:38 2022 +0100

    Unit tests new SimulationTimeSeries plugin (#923)
    
    Unit tests for types, utility and general "business logic" in new `SimulationTimeSeries` plugin.
    
    - Unit tests for files in `utils/` and `types/`-folder.
    - Resolve issue with conversion of `datetime.datetime` to `pd.Timestamp` for `pd.DataFrame` by making utility functions.
    - Minor fixes/updates to code based on issues found during testing.

commit 39db9b92ad17f0ca0af27b15f8d674d2ab9c8108
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Wed Jan 19 14:06:29 2022 +0100

    Fix: Skip adding emodel to webvizstore in VolumetricAnalysis when using csv input (#926)

commit 10b792bed9ccc948095855582f102ee44a4c79e3
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Mon Jan 17 15:41:35 2022 +0100

    Ensure valid provider realization for History Vectors in new `SimulationTimeSeries` (#921)
    
    Replace usage of realization = 0, with retrieving valid realization numbers for provider and use lowest realization number to create history vector.

commit a5a7e410206ae0fede15a358922e3bd539fb7c6d
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Mon Jan 17 13:41:05 2022 +0100

    General figures in `ParameterAnalysis` (#919)
    
    * changed CorrelationFigure to general BarChart
    
    * Generalized scatter plot
    
    * bug fix and activated trendline in scatter plot
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 8f5e0e719664516e1b9c31f197dcffc8d567f435
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Jan 13 14:21:22 2022 +0100

    New data provider in GroupTree plugin (#902)
    
    * new data provider
    
    * converted files and file structure to best practice
    
    * gruptree testing rewritten for new data provider
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 0ac74cc619ca8e7808da2958eb53eeba8fa07679
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Jan 13 12:32:58 2022 +0100

    Update param response selections by clicking in bar chart (#914)
    
    * click response in bar chart also in param_vs_sim case
    
    * Fixed bug related to updating formations well by clicking in map
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit ab38a567e84067d31cdde4cecb32f26fd98ee124
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Fri Jan 7 12:43:39 2022 +0100

    `SimulationTimeSeries`: Add statistics after realizations (#913)
    
    `SimulationTimeSeries`: Add statistics after realizations

commit a8701c76e2e329795d586fa5fc3e6b3b74c6830a
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Thu Jan 6 15:33:29 2022 +0100

    Prepare release (#912)

commit e84317cd2d1ef898260683c86deb83ac33725952
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Thu Jan 6 13:52:29 2022 +0100

    Handle ensembles with missing surface folders (#911)

commit 011d37440a27cffe4205168995a1eeb809072e5c
Author: Sigurd Pettersen <sigurd.pettersen@ceetronsolutions.com>
Date:   Wed Jan 5 15:26:18 2022 +0100

    Fixed typing/mypy issues (#907)

commit 32b7352dae0ae1258a898a0c683f1a3b7acd8760
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Thu Dec 23 23:13:58 2021 +0100

    Workaround `astroid`/`pylint` bug (#901)

commit 91cdd14eb159f582de1fd283ce76115f209cdc1a
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Wed Dec 22 11:31:25 2021 +0100

    General improvements to VolumetricAnalysis (#895)
    
    * General improvements to VolumetricAnalysis
    
    * changelog

commit 4aebb47887a4c15dd20a7a63b7ef37cbf30e4a6e
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Wed Dec 22 09:03:13 2021 +0100

    Format dates in download for resampled date in SimulationTimeSeries (#898)

commit 4db719bb418e6c4ba3d70e8960a40c80b1d7fdd2
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Tue Dec 21 14:25:48 2021 +0100

    Add quarterly sampling frequency to summary provider and SimulationTimeSeries (#896)

commit ed92862c7ec9a87027a51f636604e5d1e1df69c0
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Tue Dec 21 13:26:38 2021 +0100

    Parameter response tab in RFT plotter (#884)
    
    * change data loading to EnsembleSetModel
    
    * Put figures in separate folder
    
    * new tab for correlations and class for layout element names
    
    * Main layout for correlations tab
    
    * loading of parameters
    
    * put callbacks in folder and renamed figures folder
    
    * Renamed correlations to parameter response
    
    * Added param respons layout element names
    
    * moved functionality from processing to business logic
    
    * first version of parameter response callbacks
    
    * param respon plugin framework
    
    * correlation bar chart implemented. some functionality generalized
    
    * general barchart implemented
    
    * generalized colors functionality
    
    * implemented scatterplot
    
    * clickdata callback
    
    * started implementing formations figure
    
    * added formation plot
    
    * Color coding of the formations plot
    
    * function to get ensemble wells and parameters
    
    * removed zone values from initial layout
    
    * implemented param_vs_sim correlation option
    
    * title option
    
    * made formation lines thinner and grayer
    
    * Updated plugin docstring
    
    * updated colors utils
    
    * fixed problems related to rebasing of colors file
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 59528d2449103e7bc142a147b7b6f610e5b35756
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Tue Dec 21 11:03:37 2021 +0100

    Change label and add hoverinfo for uncertainty envelope in StructuralUncertainty (#880)

commit 43543f1b23d14b3a8bced4bf87a08faf72be5420
Author: Roger Nybø <51825893+rnyb@users.noreply.github.com>
Date:   Fri Dec 17 16:11:52 2021 +0100

    `SeismicMisfit` -  improved polygon plotting performance (#888)

commit 15966e1ecb116ac17f6bee97f374ad31a50d2b7e
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Fri Dec 17 11:18:15 2021 +0100

    Add "Statistics + realizations"-plot to New SimulationTimeSeries plugin  (#883)
    
    Added `Statistics + Realizations`-plot for New `SimulationTimeSeries` plugin.
    
    Includes:
    - Statistics and individual realizations traces in same plot - realizations gets scaled color lightness on traces.
    - Filtering of realizations to include in visualization
    - Selection to calculate statistics from all realizations or selected subset of realizations
    - Update download of user data based on the new visualization mode

commit ab1a8334f1d8a26edaf646133f8739d27b8a45d3
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Thu Dec 16 21:24:38 2021 +0100

    Added new simulation time series plugin
    
    New `SimulationTimeSeries` plugin, with code structure according to best practice plugin example `webviz-plugin-boilerplate` and usage of `EnsembleSummaryProvider`. New functionality as multiple Delta Ensembles in same plot, selectable resampling frequency and possibility to group subplots per selected ensemble or per selected vector.

commit 465eb1f5f3d65fe5dc88ac9c2fce748b2bd64fff
Author: Sigurd Pettersen <sigurd.pettersen@ceetronsolutions.com>
Date:   Thu Dec 16 15:21:38 2021 +0100

    Added `rel_file_pattern` argument to EnsembleSummaryProviderFactory methods (#889)

commit d6560660a7143c3f81add8d6eee32aaf697bb4ed
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Fri Dec 10 08:51:41 2021 +0100

    Prepare release (#879)

commit a55058b49291b96dc181bd8b054c36cc674d3c3f
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Fri Dec 10 08:37:39 2021 +0100

    Use regular `numpy` for all map statistic calculations (#878)

commit 6f45250e5874a9cfac0aaec0aeb1e84427558545
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Fri Dec 10 08:35:23 2021 +0100

    Fix issues with `WellLogViewer` prop changes (#877)

commit f961069a27850b8c9d81a04e48b0e8cef18c34e1
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Thu Dec 9 14:35:50 2021 +0100

    Handle fancharts with intermittent nan values (#875)

commit 9bed882f3a86cfaaa30efd6568d08200262f9778
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Wed Dec 8 12:08:09 2021 +0100

    `GroupTree` bug fix related to `BRANPROP` group leaf nodes (#873)

commit 3477e94cdd6604beb6fa629f31472eb233c89634
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Tue Dec 7 15:29:57 2021 +0100

    Comply with latest `pylint` version (#872)
    
    iterating the dictionary directly instead of calling .keys()

commit a930a86f17d83e7e5bc092ef8d5c786b0d1843a1
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Tue Dec 7 13:47:40 2021 +0100

    Remove `CODEOWNERS` (#868)

commit 710a5f455bf7646d3a472c430eef2ff9d667e84c
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Thu Dec 2 12:59:29 2021 +0100

    Fix `xtgeo` lint issue (#869)

commit 924ac97a1e73a27d88c853950c1aa9161d544550
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Wed Dec 1 10:31:46 2021 +0100

    Second bugfix on sensitivity comparison in VolumetricAnalysis (#863)

commit 0771e9f2c74465c7b2bf5764470a18ddd4f249e4
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Tue Nov 30 16:02:41 2021 +0100

    Fix xtgeo/pylint linting issues (#865)

commit 3302f0c694d590522cde560535d975a356acc383
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Fri Nov 26 13:32:06 2021 +0100

    Regression fix after sensitivity comparison (#860)

commit 0ac83c421d6377a2e92915253b2f9981e6f62605
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Thu Nov 25 20:40:13 2021 +0100

    Update to latest `pylint` (#857)

commit edfec8e88867b3a5c0e5201e3be83f5771adf1d4
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Nov 25 16:00:22 2021 +0100

    `RftPlotter` bug fixes and improvements (#854)
    
    * refactored code into files for layout, callbacks and business logic
    
    * fixed deselecting all ensembles bug
    
    * Fixed problem with no data matching filters
    
    * added title to the formations plot
    
    * Removed one date mark from the slider in the map controls
    
    * simplified title placement
    
    * updated links in documentation
    
    * fixed the problem of map plot changing size
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit a3043fd76f8905fb028a079694e8abbc50f5a1ff
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Thu Nov 25 14:49:28 2021 +0100

    Sensitivity comparison in `VolumetricAnalysis` (#856)

commit 8fd9504e4dc6ddefea68360d173000d7fc56eed0
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Thu Nov 25 12:02:17 2021 +0100

    support both sensitivity and gen_kw ensembles (#855)

commit 9297c35f5efe4b861ba1abdde0d443bfc20bd18a
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Nov 25 09:45:47 2021 +0100

    Groups as leaf nodes in the `GroupTree` plugin (#842)
    
    * implemented nodes as leaf nodes
    
    * implemented tests for add_nodetype function
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit 4398f481298bb5db7ffc2cc172112d9cd524c7c3
Author: Sigurd Pettersen <sigurd.pettersen@ceetronsolutions.com>
Date:   Wed Nov 24 22:31:14 2021 +0100

    Added ensemble summary provider (#721)

commit 8d3442a343b5d45f47d9febb9b8601e7afd96dc7
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Wed Nov 24 17:45:23 2021 +0100

    Refactoring `WellCompletions` code (#847)
    
    `WellCompletions` code refactored according to the best practice

commit 2ad114470b54215006e16ca66e57fcb28a4cbd0e
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Wed Nov 24 15:06:17 2021 +0100

    added realplot to tornadopage in VolumetricAnalysis (#845)

commit cf0eeff730f67d172b22f52e9f7c03bcdd46bc43
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Wed Nov 24 14:02:17 2021 +0100

    added combined sensname-senscase column (#851)

commit 35763e82982df6d34d6feefd076bb4971561fb52
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Wed Nov 24 09:47:54 2021 +0100

    Fixes to ParameterResponseCorrelation (#853)

commit 39ad4bc6e64d4f0036ba98faaf27808b97514110
Author: Sigurd Pettersen <sigurd.pettersen@ceetronsolutions.com>
Date:   Wed Nov 17 15:16:28 2021 +0100

    Updated target values in tests due to fixes in ecl 2.13.1 (#848)
    
    Updated target values in tests due to fixes in ecl 2.13.1

commit 6c8c719ac38620e591067b9ec4871aa1aee937f5
Author: Sigurd Pettersen <sigurd.pettersen@ceetronsolutions.com>
Date:   Wed Nov 17 08:29:17 2021 +0100

    Removed ert from test dependencies (#846)

commit 8b6187a8d8aca38a8f0205e43ae91040931ec854
Author: Roger Nybø <51825893+rnyb@users.noreply.github.com>
Date:   Fri Nov 12 10:21:55 2021 +0100

    Seismic misfit improvements (#844)

commit b75e88d924509de60c456a2725a938dd545588b7
Author: Sigurd Pettersen <sigurd.pettersen@ceetronsolutions.com>
Date:   Thu Nov 11 18:22:44 2021 +0100

    Add script for doing batch conversion of UNSMRY files to .arrow (#772)
    
    Added script for doing batch conversion of UNSMRY files to Arrow
    Smry data in arrow format for SOME.UNSMRY will now be stored in the file share/results/unsmry/SOME.arrow

commit f61ad71498fd7c4158721ab2d57c1b8d1a47ad8a
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Nov 11 13:04:43 2021 +0100

    Changed well connection status filetype to csv and updated docstring (#832)
    
    * renamed wellconnstatus filetype to csv and updated docstring
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit edf06baaba276d1a27a007e9694866605e643cd7
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Nov 11 10:07:26 2021 +0100

    Deleted files related to `ert` jobs (#831)
    
    * deleted files related to ert jobs
    
    * removed ert jobs and console scripts from setup.py
    
    Co-authored-by: Øyvind Lind-Johansen <olind@equinor.com>

commit ed38ad57e01733aad9fbef0d73fb0e9f4d0c2f3c
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Mon Nov 8 11:22:58 2021 +0100

    Prepare release (#843)

commit 451912aa0ba41899688bd46951b14ea445f100cd
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Mon Nov 8 11:20:17 2021 +0100

    Bugfixes and improved hoverlabels for `Tornado component` (#841)
    
    Co-authored-by: Asgeir Nyvoll <asny@equinor.com>

commit 4a08827598d90615fbe46dce956a445013fb1946
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Wed Nov 3 15:38:31 2021 +0100

    Fix timing bug in `AssistedHistoryMatchingAnalysis` by preventing initial callback (#838)

commit 7e7b92a10681f187e2b322f794c5918f741c2714
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Wed Nov 3 13:09:06 2021 +0100

    Bugfixes (#833)

commit 9df1a7f0c9345795b5545b5796bf8f0347fe08cb
Author: Roger Nybø <51825893+rnyb@users.noreply.github.com>
Date:   Mon Nov 1 22:31:48 2021 +0100

    `SeismicMisfit` - fixes to doc and polygon selector (#830)

commit 08483d0e1912105e0dbd91a6e8950e6d02d7fe32
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Thu Oct 28 09:08:05 2021 +0200

    Change from ensembles to ensemble in TornadoPlotterFMU doc (#828)

commit dc8494099d65601a18fa2d822f29102dd604586a
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Mon Oct 25 11:32:07 2021 +0200

    Tornado improvements (#825)

commit 04a66158234b8781404dd262b4062c48757ff5dc
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Sun Oct 24 23:56:15 2021 +0200

    Handle invalid subgrid definition in `SurfaceWithGridCrossSection` (#820)
    
    * Handle invalid subgrid definition

commit a0806d8d36f63a2d812c851479228cd01d917d63
Author: Roger Nybø <51825893+rnyb@users.noreply.github.com>
Date:   Sun Oct 24 13:56:42 2021 +0200

    `SeismicMisfit` update (#821)

commit 1a7fe1dff94e598b5d4824583987a1027e495ece
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Fri Oct 15 08:37:21 2021 +0200

    Fixed formatting error in `DiskUsage` bar chart tooltip (#817)

commit 9b78322aa22eeeb0335353318f33615977f975bc
Author: Roger Nybø <51825893+rnyb@users.noreply.github.com>
Date:   Tue Oct 12 11:29:55 2021 +0200

    Add new `SeismicMisfit` plugin (#734)

commit a8852ccbf32daef4852aceb8ce143ed5596747b3
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Mon Oct 11 11:53:10 2021 +0200

    More statistical options in GroupTree plugin (#809)
    
    More statistical options and better menu behavior.
    
    Co-authored-by: Øyvind Lind-Johansen (CCI RPT RES1) <olind@st-linrgsn232.st.statoil.no>

commit f57bff775bbc09becbce4a10710f18d69b23f589
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Fri Oct 8 21:29:09 2021 +0200

    Add Python 3.9 to CI (#588)

commit f4673f66da568572d17ad1b17f91fb3ae63efb38
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Fri Oct 8 15:03:58 2021 +0200

    Prepare release (#812)

commit e2a9a0df327b92de51375d4ebe869170242306a8
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Thu Oct 7 15:31:49 2021 +0200

    Bugfixes VolumetricAnalysis (#810)

commit 259f678650e7d8bf84914d6f7e58914d4b82b090
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Mon Oct 4 15:08:50 2021 +0200

    Runtime improvement in `GroupTree` plugin (#807)

commit 8f6bd76b2cba38efda2e3a95d363b3bd1de7a03e
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Mon Oct 4 08:01:45 2021 +0200

    Update according to new data (#805)

commit 7c5f23da87c464e7ae16e7cbc891ff4b7c84b6a2
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Thu Sep 30 08:13:48 2021 +0200

    Bugfixes `VolumetricAnalysis` (#802)
    
    * Bugfixes VolumetricsAnalysis

commit adccf1029baa85a747664bde9bf2a181c032dbb5
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Tue Sep 28 12:26:18 2021 +0200

    Bugfix ParametersModel sensrun check logic (#794)

commit 263fe9b22411c59faac4eb73ef28b4ca7951306f
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Mon Sep 27 19:05:24 2021 +0200

    Update tests based on change in testdata set (#792)

commit ea0e22a16d298b00a5be2dbf87a9f9d163625985
Author: Håvard Berland <havb@equinor.com>
Date:   Mon Sep 27 17:48:55 2021 +0200

    Import sorting with `isort` (#795)

commit 0a4d12e73096d4f141be353aae20b37f096f865a
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Fri Sep 24 20:09:08 2021 +0200

    `GroupTree` plugin for network visualization (#771)

commit 8ebbfa64c6ece0eec8e425ce4f7d632c321c23fa
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Fri Sep 24 19:19:47 2021 +0200

    Ensure map bounds are updated when switching attribute (#791)

commit d5f446e6bf0bfdddbab0c2f35f3b8f5367bab037
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Fri Sep 24 16:29:20 2021 +0200

    Remove REAL grouping on ensemble comparison (#784)

commit d6172ea2086c5847ed4420ee165ee10bbb22443b
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Fri Sep 24 15:41:09 2021 +0200

    Added fipfile QC tab to VolumetricAnalysis (#783)

commit b6bdd88d729e76384b9493d45c589aeeee0001c4
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Fri Sep 24 14:08:10 2021 +0200

    Prvent possibility of calculating statistics over different SENSNAME's in VolumetricAnalysis (#788)

commit f52650c7455feb09c2ec6a14f44db2278243f056
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Thu Sep 23 19:46:33 2021 +0200

    Fix bug when no predefined_expressions are defined (#779)

commit 0815246b62f86db3a552c10a8e87b024e35117fb
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Thu Sep 23 18:48:13 2021 +0200

    Bugfix property calculation in mean table `VolumetricAnalysis` (#782)
    
    * Bugfix property calculation in mean table VolumetricAnalysis

commit c62ecb931057addf2a022870820ccfb84bb8a9c1
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Thu Sep 23 14:29:27 2021 +0200

    Reset `dash` imports in `volumetric_analysis.py` to Dash 2.0 format (#780)

commit bf1bff60ce3ee8cfe67ece084f62a8e2a37b7265
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Thu Sep 23 10:29:10 2021 +0200

    Added source and ensemble comparison tabs in VolumetricAnalysis (#777)

commit bb960afa95230ccc69e424e64711c6c7bcaa6a8b
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Tue Sep 21 19:20:17 2021 +0200

    Added region/zone vs fipnum filter switch (#773)

commit b747851a32d896da56cafe51fb730f5f803e4ac4
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Tue Sep 21 16:01:17 2021 +0200

    Add `VectorCalculator` in `ReservoirSimulationTimeseries` plugin (#709)
    
    Add usage of `VectorCalculator` component in reservoir simulation timeseries plugin for calculation and graphing of custom simulation time series vectors.
    
    - Add usage of `VectorCalculator` react component in `ReservoirSimulationTimeSeries` plugin
    - Add utility functions for handling vector calculator functionality
    - Add utility functions for predefining calculated expressions in configuration file (test data)
    - Add calculated vector expressions into vector selectors
    
    
    Closes issue https://github.com/equinor/webviz-subsurface/issues/293

commit 9621b0f30730664a0b2f118cdf16e1c8f52f9696
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Tue Sep 21 13:53:10 2021 +0200

    Support eclipse volumes in VolumetricAnalysis (#770)

commit dc50f8e9e4cf0fa1f1ad6bf2b4a02eed009c5fc4
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Fri Sep 17 13:34:18 2021 +0200

    Adjust to latest `pylint` (#768)

commit 1257f54e9e3213277a861b0081bafa2ba5c4d0bb
Author: Åshild Skålnes <35798031+ashildskalnes@users.noreply.github.com>
Date:   Wed Sep 15 09:19:35 2021 +0200

    Use correct inline/xline ranges in ` SegyViewer` (#765)

commit 25314f5ba6ad88d20e285d30007600f243458e32
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Tue Sep 14 11:49:38 2021 +0200

    Lint tests (#766)

commit 617f717b9277cbd9691036ce26c2c98a65d8efbf
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Mon Sep 13 14:54:43 2021 +0200

    Bump Dash to 2.0.0 (#760)

commit 2562a2f306201f82cc155e12221cfabe8b6ac747
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Mon Sep 13 14:16:13 2021 +0200

    Load/Save xtgeo.RegularSurface as bytestream (#761)

commit 6dfc70364045d5bb905b123179eb06762aae7ed2
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Mon Sep 13 12:26:01 2021 +0200

    Skip dash-renderer errors in VolumetricAnalysis log assertion test (#763)

commit cf5f97eee2ffb549733df5339d91c712bab81eba
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Fri Sep 10 11:18:16 2021 +0200

    Add `useless-suppression` to `pylint` checks (#759)

commit 895455e068285a607d229ec73a23de2bdd504839
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Tue Sep 7 14:42:15 2021 +0200

    Updated tests for Drogon (#755)

commit 51f9cf331298766bf4a7573a890ea24f3722b4d7
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Fri Sep 3 14:41:42 2021 +0200

    Prepare for release (#757)

commit edd9675eabc25ad793f21e7ef5bd53b5e0fcfbb4
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Fri Sep 3 13:30:57 2021 +0200

    🩹 for flaky test (#756)

commit bd84101ca577a54152f7f3e9612dac0e2e9c518f
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Wed Sep 1 14:58:06 2021 +0200

    Handle missing surfaces in PropertyStatistics (#753)

commit 86ac51b206f84094545a6871c4cd574a73b5987c
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Wed Sep 1 10:04:54 2021 +0200

    Filter on OK in `ensemble_table_provider_factory` (#747)

commit 64ec6054f614d462fc424b71f25740aac2205fcf
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Wed Sep 1 09:22:57 2021 +0200

    Fix for single valued columns in `LinePlotterFMU` (#749)

commit b12c3d142f95b4a374d08a3367e7412e92d84d13
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Tue Aug 31 17:45:29 2021 +0200

    Bugfix in `VolumetricAnalysis` to trigger callbacks on page refresh (#748)

commit ec5aad348915ad2f38115f661ecc313ae38038a9
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Tue Aug 24 22:11:23 2021 +0200

    Removed warning from well completion documentation (#744)

commit 7eea7c6642f5bef3f95768995fbe2437bb661fe7
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Tue Aug 24 22:05:16 2021 +0200

    Generalize plot functions (#707)

commit 5af705e2f4a5398f0555479cc0328147235d7f3c
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Tue Aug 24 21:31:31 2021 +0200

    Move `types-dataclasses` to test requirements (#742)

commit 07d4c5531808ab7ba08cfa517a00dd23824ed713
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Tue Aug 24 20:00:14 2021 +0200

    Well Log Viewer (#733)

commit 2c14fd9d768affadadf4f4007ef6a1a59511129b
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Tue Aug 24 19:09:35 2021 +0200

    Bugfix for the case of missing `BULK` column (#741)

commit 2e60b901c28006fa0858b64c0934f90ae09ae25e
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Tue Aug 24 13:46:17 2021 +0200

    Common fan chart input utility (#719)

commit c2e9e62c215557a3913720142993c855dfe686f0
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Mon Aug 23 20:42:37 2021 +0200

    Tables as tab for easier access (#724)

commit ac5485f0e5d6bc08e14fa59c5f1ccb22a804b15e
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Mon Aug 23 16:38:17 2021 +0200

    Use `ParametersModel` in `InplaceVolumesModel` and `ParameterAnalysis` (#700)

commit ca01f4c2cdf36bc97611956b481bf2e8fb204720
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Mon Aug 23 13:32:52 2021 +0200

    Use dict literal and add exception for encoding in pylint (#739)

commit 97ddbc3ffb2e41c9bff257f049b54cbe2c4bbb3b
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Wed Aug 18 14:08:05 2021 +0200

    Layout updates to ParameterFilter (#729)

commit e321f960e06f64d3413bcd456032259370695b3d
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Tue Aug 17 16:22:38 2021 +0200

    Added parameter filter to ParameterAnalysis (#730)

commit 674bff65e121cca59999802ddc5d86df8d9ee805
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Tue Aug 17 10:21:44 2021 +0200

    Preserve uirevision in timeseries and relperm plugins (#717)

commit 8561b9d97cd5f102e4460537ad4420eb9a03cef7
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Mon Aug 16 11:25:03 2021 +0200

    Table fixes to `ParameterAnalysis` and `PropertyStatistics` (#728)

commit 2f09c3f8474f98733b2e0bd62b500b8f513d475b
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Thu Aug 12 12:23:14 2021 +0200

    Update DiskUsage to support new format (#708)

commit 5947d01b3d501fcc6ae37fa4cd8278a7aab6ca0d
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Thu Aug 12 10:59:38 2021 +0200

    Set required init values to `xtgeo.RegularSurface()` (#726)
    
    * Set required init values to xtgeo.RegularSurface()
    * Initialize RegularSurface using from_file()
    
    Co-authored-by: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>

commit bd7aa85ff559e5c8447de25cdfa02d3245221113
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Wed Aug 11 11:35:32 2021 +0200

    Custom tornado plot response option in `VolumetricAnalysis` (#723)

commit 85994d8782809319a695cc47bfa1091bf81a5602
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Wed Jul 14 10:43:49 2021 +0200

    Prepare for new release (#720)

commit 25b5dfa60594f9da1b61726110dde996c6facfb7
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Fri Jul 9 12:29:20 2021 +0200

    Avoided recalculation of unique dates in `WellCompletions` (#718)

commit a331f2884c785ffff63fc791666ac292438e060a
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Thu Jul 8 09:24:56 2021 +0200

    Improved search for unit system + ERT-job user interface (#715)

commit 52507febfb702fb53c42d575e2bdf1e493835879
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Tue Jul 6 09:39:33 2021 +0200

    Fix callback issue `VolumetricAnalysis` (#712)

commit 66486740369b38a0119ae997d4327ad9af31bf97
Author: Øyvind Lind-Johansen <47847084+lindjoha@users.noreply.github.com>
Date:   Mon Jul 5 22:18:26 2021 +0200

    Removed `output` argument from ERT jobs (#710)

commit f69a545b3d895208de663a604a5a0d81a6a1248a
Author: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
Date:   Mon Jul 5 21:32:52 2021 +0200

    Change usage of `df.all()` (#714)

commit cf253fd8384f08b1bb2e68b867865e72984b3f87
Author: Jørgen Herje <82032112+jorgenherje@users.noreply.github.com>
Date:   Sun Jul 4 21:51:19 2021 +0200

    Update `dash` version to 1.20 (#711)

commit 554a609eb9e32df618c7556421c1452f6f87a157
Author: Therese Natterøy <61694854+tnatt@users.noreply.github.com>
Date:   Thu Jul 1 12:22:25 2021 +0200

    Bugfix TornadoPlot when no sensitivities have impact (#704)

commit 3653f79e89b855dccca32cf1a22d853919b84902
Author: Asgeir Nyvoll <47146384+asnyv@users.noreply.github.com>
Date:   Thu Jul 1 10:38:36 2021 +0200

    adhere to pylint 2.9.0 (#705)

commit 3cf03cbef68a7120471a771eb11dbd7dc6fa1538
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Sun Jun 27 17:01:12 2021 +0200

    Remove Frame wrapper from WellCompletions (#691)

commit 23b3e10250ebced51aedb7712c284ec0f39c75ca
Author: Hans Kallekleiv <16436291+HansKallekleiv@users.noreply.github.com>
Date:   Sun Jun 27 16:15:07 2021 +0200

    Add deprecation warning to InplaceVolumesOneByOne (#683)
    
    Co-authored-by: Anders Fredrik Kiær <31612826+anders-kiaer@users.noreply.github.com>
