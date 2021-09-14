from typing import List, Dict, Tuple, Any
import time
import json
import io

import pandas as pd

from webviz_config.common_cache import CACHE


class GroupTreeData:
    """Description"""

    def __init__(self, smry: pd.DataFrame, gruptree: pd.DataFrame):

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

        # Checks if the ensembles have waterinj or gasinj
        self.has_waterinj, self.has_gasinj = {}, {}
        for ensemble in self.ensembles:
            smry_ens = self.smry[self.smry["ENSEMBLE"] == ensemble]
            self.has_waterinj[ensemble] = smry_ens["FWIR"].sum() > 0
            self.has_gasinj[ensemble] = smry_ens["FGIR"].sum() > 0

        self.gruptree = add_nodetype(self.gruptree, self.smry)
        self.sumvecs = self.get_sumvecs()

        self.check_that_sumvecs_exists(
            list(self.sumvecs["SUMVEC"]),
        )

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def create_grouptree_dataset(
        self,
        ensemble: str,
        tree_mode: str,
        real: int,
        prodinj: List[str],
    ) -> io.BytesIO:
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
            gruptree_ens = gruptree_ens[gruptree_ens["REAL"] == real]

        # Filter production, injection or other
        if prodinj == ["other"]:
            # Filter out rows where both IS_PROD and IS_INJ is True
            gruptree_ens = gruptree_ens[
                ~((gruptree_ens["IS_PROD"] is True) & (gruptree_ens["IS_INJ"] is True))
            ]
        if "prod" not in prodinj:
            # Filter out rows where IS_PROD=True and IS_INJ=False
            gruptree_ens = gruptree_ens[
                ~((gruptree_ens["IS_PROD"] is True) & (gruptree_ens["IS_INJ"] is False))
            ]
        if "inj" not in prodinj:
            # Filter out rows where IS_PROD=False and IS_INJ=True
            gruptree_ens = gruptree_ens[
                ~((gruptree_ens["IS_PROD"] is False) & (gruptree_ens["IS_INJ"] is True))
            ]
        if "other" not in prodinj:
            # Filter out rows where both IS_PROD=False and IS_INJ=False
            gruptree_ens = gruptree_ens[
                ~(
                    (gruptree_ens["IS_PROD"] is False)
                    & (gruptree_ens["IS_INJ"] is False)
                )
            ]

        ens_sumvecs = self.sumvecs[self.sumvecs["ENSEMBLE"] == ensemble]
        # ens_dataset = create_dataset(smry_ens, gruptree_ens, ens_sumvecs)

        # with open(
        #     "/private/olind/webviz/webviz-subsurface-components/react/src/demo/example-data/grouptree_suggested_format_drogon.json",
        #     "r",
        # ) as handle:
        #     ex_dataset = json.load(handle)
        return io.BytesIO(
            # json.dumps(ex_dataset).encode()
            json.dumps(create_dataset(smry_ens, gruptree_ens, ens_sumvecs)).encode()
        )

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def get_ensemble_real_options(
        self, ensemble: str
    ) -> Tuple[List[Dict[str, int]], int]:
        """Descr"""
        smry_ens = self.smry[self.smry["ENSEMBLE"] == ensemble]
        unique_real = sorted(smry_ens["REAL"].unique())
        return [{"label": real, "value": real} for real in unique_real], min(
            unique_real
        )

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def tree_is_equivalent_in_all_real(self, ensemble: str) -> bool:
        """Descr"""
        gruptree_ens = self.gruptree[self.gruptree["ENSEMBLE"] == ensemble]
        return gruptree_ens["REAL"].nunique() == 1

    def get_sumvecs(
        self,
    ) -> pd.DataFrame:
        """
        ensemble
        node_name
        datatype
        edge_node
        sumvec
        """
        records = []
        for _, noderow in self.gruptree.iterrows():
            ensemble = noderow["ENSEMBLE"]
            nodename = noderow["CHILD"]
            keyword = noderow["KEYWORD"]

            datatypes = ["pressure"]
            if noderow["IS_PROD"]:
                datatypes += ["oilrate", "gasrate", "waterrate"]
            if noderow["IS_INJ"] and self.has_waterinj[ensemble]:
                datatypes.append("waterinjrate")
            if noderow["IS_INJ"] and self.has_gasinj[ensemble]:
                datatypes.append("gasinjrate")
            if keyword == "WELSPECS":
                datatypes += ["bhp", "wmctl"]

            for datatype in datatypes:
                records.append(
                    {
                        "ENSEMBLE": ensemble,
                        "NODENAME": nodename,
                        "DATATYPE": datatype,
                        "EDGE_NODE": get_edge_node(datatype),
                        "SUMVEC": get_sumvec(datatype, nodename, keyword),
                    }
                )

        return pd.DataFrame(records)

    def check_that_sumvecs_exists(self, sumvecs: list, error_message: str = "") -> None:
        """Descr"""
        for sumvec in sumvecs:
            if sumvec not in self.smry.columns:
                raise ValueError(f"{sumvec} missing. {error_message}")


def get_sumvec(
    datatype: str,
    nodename: str,
    keyword: str,
) -> str:
    """Descr"""
    datatype_map = {
        "oilrate": "OPR",
        "gasrate": "GPR",
        "waterrate": "WPR",
        "waterinjrate": "WIR",
        "gasinjrate": "GIR",
        "pressure": "PR",
    }
    datatype_ecl = datatype_map[datatype] if datatype in datatype_map else ""
    if nodename == "FIELD" and datatype != "pressure":
        return f"F{datatype_ecl}"
    if keyword == "WELSPECS":
        if datatype == "pressure":
            return f"WTHP:{nodename}"
        if datatype == "bhp":
            return f"WBHP:{nodename}"
        if datatype == "wmctl":
            return f"WMCTL:{nodename}"
        return f"W{datatype_ecl}:{nodename}"
    return f"G{datatype_ecl}:{nodename}"


def get_edge_node(datatype: str) -> str:
    """Description"""
    if datatype in ["oilrate", "gasrate", "waterrate", "waterinjrate", "gasinjrate"]:
        return "edge"
    if datatype in ["pressure", "bhp", "wmctl"]:
        return "node"
    raise ValueError(f"Data type {datatype} not implemented.")


def create_dataset(
    smry: pd.DataFrame, gruptree: pd.DataFrame, sumvecs: pd.DataFrame
) -> List[dict]:
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
    sumvecs: pd.DataFrame,
) -> dict:
    """Extract the tree part of the GroupTree component dataset. This functions
    works recursively and is initially called with the top node of the tree: FIELD."""
    node_sumvecs = sumvecs[sumvecs["NODENAME"] == node]
    nodedict = gruptree[gruptree["CHILD"] == node].to_dict("records")[0]
    result: dict = {
        "node_label": node,
        "node_type": "Well" if nodedict["KEYWORD"] == "WELSPECS" else "Group",
        "edge_label": get_edge_label(nodedict),
    }
    edge_data, node_data = {}, {}

    for _, sumvec_row in node_sumvecs[node_sumvecs["EDGE_NODE"] == "edge"].iterrows():
        # her er det optimaliseringsmuligheter
        edge_data[sumvec_row["DATATYPE"]] = get_smry_in_datespan(
            smry_in_datespan, dates, sumvec_row["SUMVEC"]
        )

    for _, sumvec_row in node_sumvecs[node_sumvecs["EDGE_NODE"] == "node"].iterrows():
        # her er det optimaliseringsmuligheter
        node_data[sumvec_row["DATATYPE"]] = get_smry_in_datespan(
            smry_in_datespan, dates, sumvec_row["SUMVEC"]
        )

    result["edge_data"] = edge_data
    result["node_data"] = node_data

    children = list(gruptree[gruptree["PARENT"] == node]["CHILD"].unique())
    if children:
        result["children"] = [
            extract_tree(gruptree, child_node, smry_in_datespan, dates, sumvecs)
            for child_node in gruptree[gruptree["PARENT"] == node]["CHILD"].unique()
        ]
    return result


def get_edge_label(nodedict: dict) -> str:
    """Returns the VFP table number for the edge if it exists"""
    if "VFP_TABLE" not in nodedict:
        return ""
    if nodedict["VFP_TABLE"] in [None, 9999]:
        return ""
    return "VFP " + str(int(nodedict["VFP_TABLE"]))


def get_smry_in_datespan(
    smry_in_datespan: pd.DataFrame, dates: list, sumvec: str
) -> list:
    """Descr"""
    output = []
    for date in dates:
        smry_at_date = smry_in_datespan[smry_in_datespan.DATE == date]
        output.append(round(smry_at_date[sumvec].values[0], 2))
    return output


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
