import logging
from typing import Any, Dict, List, Set, Tuple

import numpy as np
import pandas as pd
from webviz_config.common_cache import CACHE


class GroupTreeData:
    """This class holds the summary and gruptree datasets and functionality
    to combine the data and calculate the GroupTree component input dataset.
    """

    def __init__(self, smry: pd.DataFrame, gruptree: pd.DataFrame):
        self.smry = smry
        self.gruptree = gruptree
        self.ensembles: Set[str] = gruptree["ENSEMBLE"].unique()
        self.wells: Set[str] = gruptree[gruptree["KEYWORD"] == "WELSPECS"][
            "CHILD"
        ].unique()

        # Check that all field rate summary vectors exist
        self.check_that_sumvecs_exists(["FOPR", "FGPR", "FWPR", "FWIR", "FGIR"])

        # Check that WSTAT exists for all wells
        self.check_that_sumvecs_exists([f"WSTAT:{well}" for well in self.wells])

        # Check if the ensembles have waterinj and/or gasinj
        self.has_waterinj, self.has_gasinj = {}, {}
        for ensemble in self.ensembles:
            smry_ens = self.smry[self.smry["ENSEMBLE"] == ensemble]
            self.has_waterinj[ensemble] = smry_ens["FWIR"].sum() > 0
            self.has_gasinj[ensemble] = smry_ens["FGIR"].sum() > 0

        # Add nodetypes IS_PROD, IS_INJ and IS_OTHER to gruptree
        self.gruptree = add_nodetype(self.gruptree, self.smry)

        # Add edge label
        self.gruptree["EDGE_LABEL"] = self.gruptree.apply(get_edge_label, axis=1)

        # Get summary data with metadata (ensemble, nodename, datatype, edge_or_node)
        self.sumvecs: pd.DataFrame = self.get_sumvecs_with_metadata()

        # Check that all summary vectors exist
        self.check_that_sumvecs_exists(list(self.sumvecs["SUMVEC"]))

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def create_grouptree_dataset(
        self,
        ensemble: str,
        tree_mode: str,
        stat_option: str,
        real: int,
        prod_inj_other: List[str],
    ) -> Tuple[List[Dict[Any, Any]], List[Dict[str, str]], List[Dict[str, str]]]:
        """This method is called when an event is triggered to create a new dataset
        to the GroupTree plugin. First there is a lot of filtering of the smry and
        grouptree data, before the filtered data is sent to the function that is
        actually creating the dataset.

        Returns the group tree data and two lists with dropdown options for what
        to display on the edges and nodes.

        A sample data set can be found here:
        https://github.com/equinor/webviz-subsurface-components/blob/master/react/src/demo/example-data/group-tree.json
        """  # noqa

        # Filter smry
        smry_ens = self.smry[self.smry["ENSEMBLE"] == ensemble]

        if tree_mode == "statistics":
            if stat_option == "mean":
                smry_ens = smry_ens.groupby("DATE").mean().reset_index()
            elif stat_option in ["p50", "p10", "p90"]:
                quantile = {"p50": 0.5, "p10": 0.9, "p90": 0.1}[stat_option]
                smry_ens = smry_ens.groupby("DATE").quantile(quantile).reset_index()
            elif stat_option == "max":
                smry_ens = smry_ens.groupby("DATE").max().reset_index()
            elif stat_option == "min":
                smry_ens = smry_ens.groupby("DATE").min().reset_index()
            else:
                raise ValueError(f"Statistical option: {stat_option} not implemented")
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

        return (
            create_dataset(smry_ens, gruptree_ens, ens_sumvecs),
            self.get_edge_options(ensemble, prod_inj_other),
            [
                {"name": option, "label": get_label(option)}
                for option in ["pressure", "bhp", "wmctl"]
            ],
        )

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def get_ensemble_unique_real(self, ensemble: str) -> List[int]:
        """Returns a list of runique realizations for an ensemble"""
        smry_ens = self.smry[self.smry["ENSEMBLE"] == ensemble]
        return sorted(smry_ens["REAL"].unique())

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def tree_is_equivalent_in_all_real(self, ensemble: str) -> bool:
        """Checks if the group tree is equivalent in all realizations,
        in which case there is only one REAL number in the dataframe
        """
        gruptree_ens = self.gruptree[self.gruptree["ENSEMBLE"] == ensemble]
        return gruptree_ens["REAL"].nunique() == 1

    def get_sumvecs_with_metadata(
        self,
    ) -> pd.DataFrame:
        """Returns a dataframe with the summary vectors that is needed to
        put together the group tree dataset. The other columns are metadata:

        * ensemble
        * nodename: name in eclipse network
        * datatype: oilrate, gasrate, pressure etc
        * edge_node: whether the datatype is edge (f.ex rates) or node (f.ex pressure)
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

    def check_that_sumvecs_exists(self, sumvecs: List[str]) -> None:
        """Takes in a list of summary vectors and checks if they are
        present in the summary dataset. If any are missing, a ValueError
        is raised with the list of all missing summary vectors.
        """
        missing_sumvecs = [
            sumvec for sumvec in sumvecs if sumvec not in self.smry.columns
        ]
        if missing_sumvecs:
            str_missing_sumvecs = ", ".join(missing_sumvecs)
            raise ValueError(
                "Missing summary vectors for the GroupTree plugin: "
                f"{str_missing_sumvecs}."
            )

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def get_edge_options(
        self, ensemble: str, prod_inj_other: list
    ) -> List[Dict[str, str]]:
        """Returns a list with edge node options for the dropdown
        menu in the GroupTree component. The output list has the format:
        [
            {"name": "oilrate", "label": "Oil Rate"},
            {"name": "gasrate", "label": "Gas Rate"},
        ]
        """
        options = []
        if "prod" in prod_inj_other:
            for rate in ["oilrate", "gasrate", "waterrate"]:
                options.append({"name": rate, "label": get_label(rate)})
        if "inj" in prod_inj_other and self.has_waterinj[ensemble]:
            options.append({"name": "waterinjrate", "label": get_label("waterinjrate")})
        if "inj" in prod_inj_other and self.has_gasinj[ensemble]:
            options.append({"name": "gasinjrate", "label": get_label("gasinjrate")})
        if options:
            return options
        return [{"name": "oilrate", "label": get_label("oilrate")}]


def get_edge_label(row: pd.Series) -> str:
    """Returns the edge label for a row in the grouptree dataframe"""
    if (
        "VFP_TABLE" not in row
        or row["VFP_TABLE"] in [None, 9999]
        or np.isnan(row["VFP_TABLE"])
    ):
        return ""
    vfp_nb = int(row["VFP_TABLE"])
    return f"VFP {vfp_nb}"


def get_label(datatype: str) -> str:
    """Returns a more readable label for the summary datatypes"""
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
    """Returns the correct summary vector for a given
    * datatype: oilrate, gasrate etc
    * nodename: FIELD, well name or group name in Eclipse network
    * keyword: GRUPTREE, BRANPROP or WELSPECS
    """
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
    """Returns if a given datatype is edge (typically rates) or node (f.ex pressures)"""
    if datatype in ["oilrate", "gasrate", "waterrate", "waterinjrate", "gasinjrate"]:
        return "edge"
    if datatype in ["pressure", "bhp", "wmctl"]:
        return "node"
    raise ValueError(f"Data type {datatype} not implemented.")


def create_dataset(
    smry: pd.DataFrame, gruptree: pd.DataFrame, sumvecs: pd.DataFrame
) -> List[dict]:
    """The function puts together the GroupTree component input dataset.

    The gruptree dataframe includes complete networks for every time
    the tree changes (f.ex if a new well is defined). The function loops
    through the trees and puts together all the summary data that is valid for
    the time span where the tree is valid, along with the tree structure itself.
    """
    trees = []
    # loop trees
    for date, gruptree_date in gruptree.groupby("DATE"):
        next_date = gruptree[gruptree.DATE > date]["DATE"].min()
        if pd.isna(next_date):
            next_date = smry["DATE"].max()
        smry_in_datespan = smry[
            (smry["DATE"] >= date) & (smry["DATE"] < next_date)
        ].groupby("DATE")
        dates = list(smry_in_datespan.groups)
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
            logging.getLogger(__name__).warning(
                f"""No summary data found for gruptree between {date} and {next_date}"""
            )
    return trees


def extract_tree(
    gruptree: pd.DataFrame,
    nodename: str,
    smry_in_datespan: Dict[Any, pd.DataFrame],
    dates: list,
    sumvecs: pd.DataFrame,
) -> dict:
    # pylint: disable=too-many-locals
    """Extract the tree part of the GroupTree component dataset. This functions
    works recursively and is initially called with the top node of the tree: FIELD."""
    node_sumvecs = sumvecs[sumvecs["NODENAME"] == nodename]
    nodedict = get_nodedict(gruptree, nodename)

    result: dict = {
        "node_label": nodename,
        "node_type": "Well" if nodedict["KEYWORD"] == "WELSPECS" else "Group",
        "edge_label": nodedict["EDGE_LABEL"],
    }

    edges = node_sumvecs[node_sumvecs["EDGE_NODE"] == "edge"].to_dict("records")
    nodes = node_sumvecs[node_sumvecs["EDGE_NODE"] == "node"].to_dict("records")

    edge_data: Dict[str, List[float]] = {item["DATATYPE"]: [] for item in edges}
    node_data: Dict[str, List[float]] = {item["DATATYPE"]: [] for item in nodes}

    # Looping the dates only once is very important for the speed of this function
    for _, smry_at_date in smry_in_datespan:
        for item in edges:
            edge_data[item["DATATYPE"]].append(
                round(smry_at_date[item["SUMVEC"]].values[0], 2)
            )
        for item in nodes:
            node_data[item["DATATYPE"]].append(
                round(smry_at_date[item["SUMVEC"]].values[0], 2)
            )

    result["edge_data"] = edge_data
    result["node_data"] = node_data

    children = list(gruptree[gruptree["PARENT"] == nodename]["CHILD"].unique())
    if children:
        result["children"] = [
            extract_tree(gruptree, child, smry_in_datespan, dates, sumvecs)
            for child in children
        ]
    return result


def get_nodedict(gruptree: pd.DataFrame, nodename: str) -> Dict[str, Any]:
    """Returns the node data from a row in the gruptree dataframe as a dictionary.
    This function also checks that there is exactly one element with the given name.
    """
    df = gruptree[gruptree["CHILD"] == nodename]
    if df.empty:
        raise ValueError(f"No gruptree row found for node {nodename}")
    if df.shape[0] > 1:
        raise ValueError(f"Multiple gruptree rows found for node {nodename}. {df}")
    return df.to_dict("records")[0]


def add_nodetype(gruptree: pd.DataFrame, smry: pd.DataFrame) -> pd.DataFrame:
    """Adds three columns to the gruptree dataframe: IS_PROD, IS_INJ and IS_OTHER.

    Wells are classified as producers,  injectors or other based on the WSTAT summary data.

    Group nodes are classified as producing if it has any producing wells upstream and
    correspondingly for injection and other.
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

    # Recursively find well types of all wells connected to the group node
    # Deduce group node type from well types
    groupnodes = nodes[nodes["KEYWORD"] != "WELSPECS"]
    for _, groupnode in groupnodes.iterrows():
        wells_are_prod, wells_are_inj, wells_are_other = get_leaf_well_types(
            groupnode["CHILD"], nodes
        )
        is_prod_map[groupnode["CHILD"]] = any(wells_are_prod)
        is_inj_map[groupnode["CHILD"]] = any(wells_are_inj)
        is_other_map[groupnode["CHILD"]] = any(wells_are_other)

    # FIELD node must not be filtered out, so it is set True for all categories
    is_prod_map["FIELD"] = True
    is_inj_map["FIELD"] = True
    is_other_map["FIELD"] = True

    # Tag all nodes as IS_PROD, IS_INJ and IS_OTHER
    gruptree["IS_PROD"] = gruptree["CHILD"].map(is_prod_map)
    gruptree["IS_INJ"] = gruptree["CHILD"].map(is_inj_map)
    gruptree["IS_OTHER"] = gruptree["CHILD"].map(is_other_map)
    return gruptree


def get_leaf_well_types(
    node_name: str, gruptree: pd.DataFrame
) -> Tuple[List[Any], List[Any], List[Any]]:
    """This function finds the IS_PROD, IS_INJ and IS_OTHER values of all
    connected to a group node.

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
    """Returns three dictionaries that is classifying wells as producer,
    injector and/or other (f.ex observation well).
    """
    is_prod_map, is_inj_map, is_other_map = {}, {}, {}
    for _, wellnode in wellnodes.iterrows():
        wellname = wellnode["CHILD"]
        wstat = smry[f"WSTAT:{wellname}"].unique()
        is_prod_map[wellname] = 1 in wstat
        is_inj_map[wellname] = 2 in wstat
        is_other_map[wellname] = (1 not in wstat) and (2 not in wstat)
    return is_prod_map, is_inj_map, is_other_map
