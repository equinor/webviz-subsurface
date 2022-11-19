from ._business_logic import SwatinitQcDataModel


def qc_flag_description() -> str:
    return """
- **PC_SCALED**  - Capillary pressure have been scaled and SWATINIT was accepted.
- **FINE_EQUIL**  - If item 9 in EQUIL is nonzero then initialization happens in a vertically
    refined model. Capillary pressure is still scaled, but water might be added or lost.
- **SWL_TRUNC**  - If SWL is larger than SWATINIT, SWAT will be reset to SWL. Extra water is
    added and hydrocarbons are lost.
- **SWATINIT_1**  - When SWATINIT is 1 above the contact, Eclipse will ignore SWATINIT and not
    touch the capillary pressure function which typically results in extra hydrocarbons.
    This could be ok as long as the porosities and/or permeabilities of these cells are small.
    If SWU is included, cells where SWATINIT is equal or larger than SWU will
    also be flagged as SWATINIT_1
- **HC_BELOW_FWL**  - If SWATINIT is less than 1 below the contact provided in EQUIL, Eclipse will
    ignore it and not scale the capillary pressure function. SWAT will be 1, unless a capillary
    pressure function with negative values is in SWOF/SWFN. This results in the loss of HC volumes.
- **PPCWMAX**  - If an upper limit of how much capillary pressure scaling is allowed is set, water will be
    lost if this limit is hit.
- **WATER**  - SWATINIT was 1 in the water zone, and SWAT is set to 1.

> **Consult the [check_swatinit](https://fmu-docs.equinor.com/docs/subscript/scripts/check_swatinit.html) 
  documentation for more detailed descriptions**

"""


def check_swatinit_description() -> str:
    return """
This plugin is used to visualize the output from **check_swatinit** which is a **QC tool for Water Initialization in Eclipse runs
when the SWATINIT keyword has been used**. It is used to quantify how much the volume changes from **SWATINIT** to **SWAT** at time
zero in the dynamical model, and help understand why it changes.

When the keyword SWATINIT has been used as water initialization option in Eclipse, capillary pressure scaling on a cell-by-cell basis will
occur in order to match SWATINIT from the geomodel. 
This process has some exceptions which can cause volume changes from SWATINIT to SWAT at time zero.
Each cell in the dynamical model has been flagged according to what has happened during initialization, and information is stored
in the **QC_FLAG** column.

> Check the maximum capillary pressure pr SATNUM in each EQLNUM to ensure extreme values were not necessary

[check_swatinit documentation](https://fmu-docs.equinor.com/docs/subscript/scripts/check_swatinit.html) 
"""


# pylint: disable=anomalous-backslash-in-string
def pc_columns_description() -> str:
    return f"""
> **Column descriptions**
> - **PCOW_MAX**  - Maximum capillary pressure from the input SWOF/SWFN tables
> - **PC_SCALING**  - Maximum capillary pressure scaling applied
> - **PPCW**  - Maximum capillary pressure after scaling
> - **{SwatinitQcDataModel.COLNAME_THRESHOLD}**  - Column showing how many percent of the pc-scaled dataset that match the user-selected threshold

*PPCW = PCOW_MAX \* PC_SCALING*

A threshold for the maximum capillary scaling can be set in the menu.
The table will show how many percent of the dataset that exceeds this value, and cells above the threshold will be shown in the map ➡️
"""
