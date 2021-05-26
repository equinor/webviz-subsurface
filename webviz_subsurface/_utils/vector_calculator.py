from typing import List, Dict
import numpy as np
import pandas as pd
from py_expression_eval import Parser


def get_vector_calculator_parser() -> Parser:
    parser = Parser()
    parser.ops2["^"] = np.power
    return parser


def get_variable_vector_map_as_dict(var_vec_map: List[Dict[str, List[str]]]) -> dict:
    res: dict = {}
    for elm in var_vec_map:
        # TODO verify that elm["variableName"] and elm["vectorName"][0] exists
        res[elm["variableName"]] = elm["vectorName"][0]
    return res


def get_parser_eval_dict(var_vec_dict: Dict[str, str], smry: pd.DataFrame) -> dict:
    res: dict = {}
    for var_name in var_vec_dict:
        res[var_name] = smry[var_vec_dict[var_name]]
    return res
