from typing import List, Dict, Tuple, Any
import time
import json

import pandas as pd

from webviz_config.common_cache import CACHE


class GroupTreeData:
    """ """

    def __init__(self, smry, gruptree):

        self.smry = smry
        self.gruptree = gruptree
        self.ensembles = gruptree["ENSEMBLE"].unique()
        self.wells = gruptree[gruptree["KEYWORD"] == "WELSPECS"]["CHILD"].unique()

        self.check_that_sumvecs_exists(
            ["FOPR", "FGPR", "FWPR", "FWIR", "FGIR"],
            error_message="All field rate summary vectors must exist.",
        )
        self.check_that_sumvecs_exists(
            [f"WSTAT:{well}" for well in self.wells],
            error_message="WSTAT must be exported for all wells",
        )

        self.gruptree = add_nodetype(self.gruptree, self.smry)

        self.node_sumvecs, sumvecs_list = self.get_node_sumvecs()
        self.check_that_sumvecs_exists(
            sumvecs_list,
        )

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def create_grouptree_dataset(
        self,
        ensemble: str,
        tree_mode: str,
        real: int
        # smry: pd.DataFrame,
        # gruptrees: pd.DataFrame,
    ) -> Dict:
        """This function creates the dataset that is input to the GroupTree
        component the webviz_subsurface_components.

        Link to sample dataset

        """

        # Filter smry
        smry_ens = self.smry[self.smry["ENSEMBLE"] == ensemble]
        # smry_ens.dropna(how="all", axis=1, inplace=True)
        if tree_mode == "plot_mean":
            smry_ens = smry_ens.groupby("DATE").mean().reset_index()
        else:
            smry_ens = smry_ens[smry_ens["REAL"] == real]

        # Filter Gruptree
        gruptree_ens = self.gruptree[self.gruptree["ENSEMBLE"] == ensemble]
        if tree_mode == "single_real" and not self.tree_is_equivalent_in_all_real(
            ensemble
        ):
            # Trees are not equal. Filter on realization
            gruptree_ens[gruptree_ens["REAL"] == real]

        return create_dataset(smry_ens, gruptree_ens, self.node_sumvecs[ensemble])

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def get_ensemble_real_options(
        self, ensemble: str
    ) -> Tuple[List[Dict[str, int]], int]:
        """Descr"""
        smry_ens = self.smry[self.smry["ENSEMBLE"] == ensemble]
        unique_real = smry_ens["REAL"].unique()
        return [{"label": real, "value": real} for real in unique_real], min(
            unique_real
        )

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def tree_is_equivalent_in_all_real(self, ensemble: str) -> bool:
        """Descr"""
        gruptree_ens = self.gruptree[self.gruptree["ENSEMBLE"] == ensemble]
        return gruptree_ens["REAL"].nunique() == 1

    def get_node_sumvecs(
        self,
    ) -> Tuple[Dict[str, Dict[str, Dict[str, str]]], List[str]]:
        """
        {
            "ens": {
                "node": {
                    "oilrate": "GOPR:NODE"
                }
            }
        }
        """
        sumvecs_dict = {}
        sumvecs_list = []
        for ensemble in self.ensembles:
            sumvecs_dict[ensemble] = {}
            smry_ens = self.smry[self.smry["ENSEMBLE"] == ensemble]
            gruptree_ens = self.gruptree[self.gruptree["ENSEMBLE"] == ensemble]
            field_has_waterinj = smry_ens["FWIR"].sum() > 0
            field_has_gasinj = smry_ens["FGIR"].sum() > 0
            for _, noderow in gruptree_ens.iterrows():
                node_sumvecs = get_sumvecs_for_node(
                    noderow, field_has_waterinj, field_has_gasinj
                )
                sumvecs_dict[ensemble][noderow["CHILD"]] = node_sumvecs
                sumvecs_list += [sumvec for _, sumvec in node_sumvecs.items()]
        return sumvecs_dict, sumvecs_list

    def check_that_sumvecs_exists(self, sumvecs: list, error_message: str = ""):
        """Descr"""
        for sumvec in sumvecs:
            if sumvec not in self.smry.columns:
                raise ValueError(f"{sumvec} missing. {error_message}")


def create_dataset(
    smry: pd.DataFrame, gruptree: pd.DataFrame, sumvecs: Dict[str, str]
) -> List[Dict]:
    """Descr"""
    starttime = time.time()
    trees = []

    # loop trees
    for date, gruptree_date in gruptree.groupby("DATE"):
        next_date = gruptree[gruptree.DATE > date]["DATE"].min()
        if pd.isna(next_date):
            next_date = smry["DATE"].max()
        smry_in_datespan = smry[
            (smry["DATE"] >= date) & (smry["DATE"] < next_date)
        ].copy()
        dates = list(smry_in_datespan["DATE"].unique())
        trees.append(
            {
                "dates": [date.strftime("%Y-%m-%d") for date in dates],
                "tree": extract_tree(
                    gruptree_date, "FIELD", smry_in_datespan, dates, sumvecs
                ),
            }
        )
    with open("/private/olind/webviz/grouptree.json", "w") as handle:
        json.dump(trees, handle)
    print(f"create_grouptree_dataset used {round(time.time()-starttime, 2)} seconds.")
    return trees


def extract_tree(
    gruptree: pd.DataFrame,
    node: str,
    smry_in_datespan: pd.DataFrame,
    dates: list,
    sumvecs: Dict[str, str],
) -> dict:
    """Extract the tree part of the GroupTree component dataset. This functions
    works recursively and is initially called with the top node of the tree: FIELD."""
    nodedict = get_node_data(gruptree, node)
    node_sumvecs = sumvecs[node]

    result = {"name": node}
    for key, sumvec in node_sumvecs.items():
        # her er det optimaliseringsmuligheter
        result[key] = get_smry_in_datespan(smry_in_datespan, dates, sumvec)

    children = list(gruptree[gruptree["PARENT"] == node]["CHILD"].unique())
    if children:
        result["children"] = [
            extract_tree(gruptree, child_node, smry_in_datespan, dates, sumvecs)
            for child_node in gruptree[gruptree["PARENT"] == node]["CHILD"].unique()
        ]
    return result


def get_grupnet_info(nodedict: dict) -> str:
    """Returns the VFP table number for the edge if it exists"""
    if "VFP_TABLE" not in nodedict:
        return ""
    if nodedict["VFP_TABLE"] in [None, 9999]:
        return ""
    return "VFP " + str(int(nodedict["VFP_TABLE"]))


def get_node_data(df_gruptree: pd.DataFrame, node: str) -> dict:
    """Returns the data fields for a specific node as a dictionary"""
    if node not in list(df_gruptree.CHILD):
        raise ValueError(f"Node {node} not found in gruptree table.")
    df_node = df_gruptree[df_gruptree.CHILD == node]
    if df_node.shape[0] > 1:
        # df_gruptree.to_csv("/private/olind/webviz/debug.csv")
        raise ValueError(f"Multiple nodes found for {node} in gruptree table.")
    return df_node.to_dict("records")[0]


def get_smry_in_datespan(smry_in_datespan, dates, sumvec) -> List[int]:
    """Descr"""
    output = []
    for date in dates:
        smry_at_date = smry_in_datespan[smry_in_datespan.DATE == date]
        output.append(round(smry_at_date[sumvec].values[0], 2))
    return output


def get_sumvecs_for_node(
    noderow: pd.Series, field_has_waterinj: bool, field_has_gasinj: bool
) -> Dict[str, str]:
    """Returns the summary vectors for node as a dictionary"""
    node = noderow["CHILD"]
    node_type = noderow["KEYWORD"]
    is_prod = noderow["IS_PROD"]
    is_inj = noderow["IS_INJ"]
    output = {}
    if node == "FIELD":
        output["pressure"] = "GPR:FIELD"
        if is_prod:
            output["oilrate"] = "FOPR"
            output["gasrate"] = "FGPR"
            output["waterrate"] = "FWPR"
        if is_inj and field_has_waterinj:
            output["waterinjrate"] = "FWIR"
        if is_inj and field_has_gasinj:
            output["gasinjrate"] = "FGIR"
        return output

    if node_type in ["GRUPTREE", "BRANPROP"]:
        output["pressure"] = f"GPR:{node}"
        if is_prod:
            output["oilrate"] = f"GOPR:{node}"
            output["gasrate"] = f"GGPR:{node}"
            output["waterrate"] = f"GWPR:{node}"
        if is_inj and field_has_waterinj:
            output["waterinjrate"] = f"GWIR:{node}"
        if is_inj and field_has_gasinj:
            output["gasinjrate"] = f"GGIR:{node}"
        return output

    if node_type == "WELSPECS":
        output["pressure"] = f"WTHP:{node}"
        output["bhp"] = f"WBHP:{node}"
        output["wmctl"] = f"WMCTL:{node}"
        if is_prod:
            output["oilrate"] = f"WOPR:{node}"
            output["gasrate"] = f"WGPR:{node}"
            output["waterrate"] = f"WWPR:{node}"
        if is_inj and field_has_waterinj:
            output["waterinjrate"] = f"WWIR:{node}"
        if is_inj and field_has_gasinj:
            output["gasinjrate"] = f"WGIR:{node}"
        return output
    raise ValueError(f"Node type {node_type} not implemented")


def add_nodetype(gruptree: pd.DataFrame, smry: pd.DataFrame) -> pd.DataFrame:
    """Adds two columns to the gruptree dataframe: IS_PROD and IS_INJ. These has boolean
    values and all combinations are possible, f.ex both True or both False.

    Wells are classified as producers and injectors based on the WSTAT summary data.

    Group nodes are classified as producing if they have any producer wells upstream
    and as injecting if they have any injector wells downstream.
    """
    df = pd.DataFrame()
    for ensemble in gruptree["ENSEMBLE"].unique():
        gruptree_ens = gruptree[gruptree["ENSEMBLE"] == ensemble].copy()
        smry_ens = smry[smry["ENSEMBLE"] == ensemble].copy()
        df_ens = add_nodetype_for_ens(gruptree_ens, smry_ens)
        df = pd.concat([df, df_ens])
    return df


def add_nodetype_for_ens(gruptree: pd.DataFrame, smry: pd.DataFrame) -> pd.DataFrame:
    """Adds nodetype IS_PROD and IS_INJ for an ensemble."""
    nodes = gruptree.drop_duplicates(subset=["CHILD"], keep="first").copy()

    # Tag wells as producers and/or injector (or None)
    is_prod_map, is_inj_map = get_welltype_maps(
        nodes[nodes["KEYWORD"] == "WELSPECS"], smry
    )
    nodes["IS_PROD"] = nodes["CHILD"].map(is_prod_map)
    nodes["IS_INJ"] = nodes["CHILD"].map(is_inj_map)
    groupnodes = nodes[nodes["KEYWORD"] != "WELSPECS"]

    # Recursively find well types of all fields below a group node
    # Deduce group node type from well types
    for _, groupnode in groupnodes.iterrows():
        wells_are_prod, wells_are_inj = get_leaf_well_types(groupnode["CHILD"], nodes)
        is_prod_map[groupnode["CHILD"]] = any(wells_are_prod)
        is_inj_map[groupnode["CHILD"]] = any(wells_are_inj)

    # Tag all nodes as producing/injecing nodes
    gruptree["IS_PROD"] = gruptree["CHILD"].map(is_prod_map)
    gruptree["IS_INJ"] = gruptree["CHILD"].map(is_inj_map)
    return gruptree


def get_leaf_well_types(
    node_name: str, gruptree: pd.DataFrame
) -> Tuple[List[Any], List[Any]]:
    """This function finds the IS_PROD and IS_INJ values of all wells
    producing to or injecting to a group node.

    The function is using recursion to find all wells below the node
    int the three.
    """
    children = gruptree[gruptree["PARENT"] == node_name]
    wells_are_prod, wells_are_inj = [], []
    for _, childrow in children.iterrows():
        if childrow["KEYWORD"] == "WELSPECS":
            wells_are_prod.append(childrow["IS_PROD"])
            wells_are_inj.append(childrow["IS_INJ"])
        else:
            prod, inj = get_leaf_well_types(childrow["CHILD"], gruptree)
            wells_are_prod += prod
            wells_are_inj += inj
    return wells_are_prod, wells_are_inj


def get_welltype_maps(
    wellnodes: pd.DataFrame, smry: pd.DataFrame
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """This function creates two dictionaries that is classifying each
    well as producer and/or injector.
    """
    is_prod_map, is_inj_map = {}, {}
    for _, wellnode in wellnodes.iterrows():
        wellname = wellnode["CHILD"]
        wstat = smry[f"WSTAT:{wellname}"].unique()
        is_prod_map[wellname] = 1 in wstat
        is_inj_map[wellname] = 2 in wstat
    return is_prod_map, is_inj_map
