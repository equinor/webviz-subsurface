from typing import List, Dict, Tuple, Any
import time

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
        # Check if the ensembles have waterinj or gasinj
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
        prod_inj_other: List[str],
    ) -> Tuple[List[Dict[Any, Any]], List[Dict[str, str]]]:
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

        # Filter Gruptree ensemble and realization
        gruptree_ens = self.gruptree[self.gruptree["ENSEMBLE"] == ensemble]
        if tree_mode == "single_real" and not self.tree_is_equivalent_in_all_real(
            ensemble
        ):
            # Trees are not equal. Filter on realization
            gruptree_ens = gruptree_ens[gruptree_ens["REAL"] == real]

        # Filter nodetype prod, inj and/or other
        df = pd.DataFrame()
        for tpe in ["prod", "inj", "other"]:
            if tpe in prod_inj_other:
                df = pd.concat([df, gruptree_ens[gruptree_ens[f"IS_{tpe}".upper()]]])
        gruptree_ens = df.drop_duplicates()

        ens_sumvecs = self.sumvecs[self.sumvecs["ENSEMBLE"] == ensemble]
        ens_dataset = create_dataset(smry_ens, gruptree_ens, ens_sumvecs)
        # with open("/private/olind/webviz/gruptree_testdataset.json", "r") as handle:
        #     ex_dataset = json.load(handle)

        return (
            ens_dataset,
            get_options(ens_sumvecs, "edge"),
            get_options(ens_sumvecs, "node"),
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

        unique_nodes = self.gruptree.drop_duplicates(
            subset=["ENSEMBLE", "CHILD", "KEYWORD"]
        )
        for _, noderow in unique_nodes.iterrows():
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
        missing_sumvecs = [
            sumvec for sumvec in sumvecs if sumvec not in self.smry.columns
        ]
        if missing_sumvecs:
            str_missing_sumvecs = ", ".join(missing_sumvecs)
            raise ValueError(
                "Missing summary vectors for the GroupTree plugin: "
                f"{str_missing_sumvecs}. {error_message}."
            )


def get_options(
    sumvecs: pd.DataFrame, edge_node: str
) -> Dict[str, List[Dict[str, str]]]:
    """
    [
        {"name": "oilrate", "label": "Oil Rate"},
        {"name": "gasrate", "label": "Gas Rate"},
    ]
    """
    options = sumvecs[sumvecs["EDGE_NODE"] == edge_node]["DATATYPE"].unique()
    return [{"name": option, "label": get_label(option)} for option in options]


def get_label(datatype: str) -> str:
    """Descr"""
    labels = {
        "oilrate": "Oil Rate",
        "gasrate": "Gas Rate",
        "waterrate": "Water Rate",
        "waterinjrate": "Water Inj Rate",
        "gasinjrate": "Gas Inj Rate",
        "pressure": "Pressure",
        "bhp": "BHP",
        "wmctl": "WMCTL",
    }
    if datatype in labels:
        return labels[datatype]
    raise ValueError(f"Label for dataype {datatype} not implemented.")


def get_sumvec(
    datatype: str,
    nodename: str,
    keyword: str,
) -> str:
    """Descr"""
    datatype_map = {
        "FIELD": {
            "oilrate": "FOPR",
            "gasrate": "FGPR",
            "waterrate": "FWPR",
            "waterinjrate": "FWIR",
            "gasinjrate": "FGIR",
            "pressure": "GPR",
        },
        "GRUPTREE": {
            "oilrate": "GOPR",
            "gasrate": "GGPR",
            "waterrate": "GWPR",
            "waterinjrate": "GWIR",
            "gasinjrate": "GGIR",
            "pressure": "GPR",
        },
        "BRANPROP": {
            "oilrate": "GOPRNB",
            "gasrate": "GGPRNB",
            "waterrate": "GWPRNB",
            "pressure": "GPR",
        },
        "WELSPECS": {
            "oilrate": "WOPR",
            "gasrate": "WGPR",
            "waterrate": "WWPR",
            "waterinjrate": "WWIR",
            "gasinjrate": "WGIR",
            "pressure": "WTHP",
            "bhp": "WBHP",
            "wmctl": "WMCTL",
        },
    }

    if nodename == "FIELD":
        datatype_ecl = datatype_map["FIELD"][datatype]
        if datatype == "pressure":
            return f"{datatype_ecl}:{nodename}"
        return datatype_ecl
    datatype_ecl = datatype_map[keyword][datatype]
    return f"{datatype_ecl}:{nodename}"


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
        if dates:
            trees.append(
                {
                    "dates": [date.strftime("%Y-%m-%d") for date in dates],
                    "tree": extract_tree(
                        gruptree_date, "FIELD", smry_in_datespan, dates, sumvecs
                    ),
                }
            )
        else:
            print("warning here")
            # warning: no summary vectors for tree

    # with open("/private/olind/webviz/grouptree.json", "w") as handle:
    #     json.dump(trees, handle)
    print(f"create_grouptree_dataset used {round(time.time()-starttime, 2)} seconds.")
    return trees


def extract_tree(
    gruptree: pd.DataFrame,
    nodename: str,
    smry_in_datespan: pd.DataFrame,
    dates: list,
    sumvecs: pd.DataFrame,
) -> dict:
    """Extract the tree part of the GroupTree component dataset. This functions
    works recursively and is initially called with the top node of the tree: FIELD."""
    node_sumvecs = sumvecs[sumvecs["NODENAME"] == nodename]
    nodedict = gruptree[gruptree["CHILD"] == nodename].to_dict("records")[0]
    result: dict = {
        "node_label": nodename,
        "node_type": "Well" if nodedict["KEYWORD"] == "WELSPECS" else "Group",
        "edge_label": get_edge_label(nodedict),
    }

    edges = node_sumvecs[node_sumvecs["EDGE_NODE"] == "edge"].to_dict("records")
    nodes = node_sumvecs[node_sumvecs["EDGE_NODE"] == "node"].to_dict("records")

    edge_data: Dict[str, List[float]] = {edgedict["DATATYPE"]: [] for edgedict in edges}
    node_data: Dict[str, List[float]] = {nodedict["DATATYPE"]: [] for nodedict in nodes}

    for _, smry_at_date in smry_in_datespan.groupby(
        "DATE"
    ):  # er man sikre pa at datoene er i rett rekkefolge?
        for edgedict in edges:
            edge_data[edgedict["DATATYPE"]].append(
                round(smry_at_date[edgedict["SUMVEC"]].values[0], 2)
            )
        for nodedict in nodes:
            node_data[nodedict["DATATYPE"]].append(
                round(smry_at_date[nodedict["SUMVEC"]].values[0], 2)
            )

    result["edge_data"] = edge_data
    result["node_data"] = node_data

    children = list(gruptree[gruptree["PARENT"] == nodename]["CHILD"].unique())
    if children:
        result["children"] = [
            extract_tree(gruptree, child_node, smry_in_datespan, dates, sumvecs)
            for child_node in gruptree[gruptree["PARENT"] == nodename]["CHILD"].unique()
        ]
    return result


def get_edge_label(nodedict: dict) -> str:
    """Returns the VFP table number for the edge if it exists"""
    if "VFP_TABLE" not in nodedict:
        return ""
    if nodedict["VFP_TABLE"] in [None, 9999]:
        return ""
    return "VFP " + str(int(nodedict["VFP_TABLE"]))


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
    """Adds nodetype IS_PROD, IS_INJ and IS_OTHER for an ensemble."""

    nodes = gruptree.drop_duplicates(subset=["CHILD"], keep="first").copy()
    # Tag wells as producers, injector or other well
    is_prod_map, is_inj_map, is_other_map = get_welltype_maps(
        nodes[nodes["KEYWORD"] == "WELSPECS"], smry
    )
    nodes["IS_PROD"] = nodes["CHILD"].map(is_prod_map)
    nodes["IS_INJ"] = nodes["CHILD"].map(is_inj_map)
    nodes["IS_OTHER"] = nodes["CHILD"].map(is_other_map)
    groupnodes = nodes[nodes["KEYWORD"] != "WELSPECS"]

    # Recursively find well types of all fields below a group node
    # Deduce group node type from well types
    for _, groupnode in groupnodes.iterrows():
        wells_are_prod, wells_are_inj, wells_are_other = get_leaf_well_types(
            groupnode["CHILD"], nodes
        )
        is_prod_map[groupnode["CHILD"]] = any(wells_are_prod)
        is_inj_map[groupnode["CHILD"]] = any(wells_are_inj)
        is_other_map[groupnode["CHILD"]] = any(wells_are_other)

    # Tag all nodes as producing/injecing nodes
    gruptree["IS_PROD"] = gruptree["CHILD"].map(is_prod_map)
    gruptree["IS_INJ"] = gruptree["CHILD"].map(is_inj_map)
    gruptree["IS_OTHER"] = gruptree["CHILD"].map(is_other_map)
    return gruptree


def get_leaf_well_types(
    node_name: str, gruptree: pd.DataFrame
) -> Tuple[List[Any], List[Any], List[Any]]:
    """This function finds the IS_PROD and IS_INJ values of all wells
    producing to or injecting to a group node.

    The function is using recursion to find all wells below the node
    int the three.
    """
    children = gruptree[gruptree["PARENT"] == node_name]
    wells_are_prod, wells_are_inj, wells_are_other = [], [], []
    for _, childrow in children.iterrows():
        if childrow["KEYWORD"] == "WELSPECS":
            wells_are_prod.append(childrow["IS_PROD"])
            wells_are_inj.append(childrow["IS_INJ"])
            wells_are_other.append(childrow["IS_OTHER"])
        else:
            prod, inj, other = get_leaf_well_types(childrow["CHILD"], gruptree)
            wells_are_prod += prod
            wells_are_inj += inj
            wells_are_other += other
    return wells_are_prod, wells_are_inj, wells_are_other


def get_welltype_maps(
    wellnodes: pd.DataFrame, smry: pd.DataFrame
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """This function creates two dictionaries that is classifying each
    well as producer, injector and/or other (f.ex observation well).
    """
    is_prod_map, is_inj_map, is_other_map = {}, {}, {}
    for _, wellnode in wellnodes.iterrows():
        wellname = wellnode["CHILD"]
        wstat = smry[f"WSTAT:{wellname}"].unique()
        is_prod_map[wellname] = 1 in wstat
        is_inj_map[wellname] = 2 in wstat
        is_other_map[wellname] = (1 not in wstat) and (2 not in wstat)
    return is_prod_map, is_inj_map, is_other_map
