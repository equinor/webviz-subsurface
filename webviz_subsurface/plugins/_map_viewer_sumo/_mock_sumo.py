from typing import List, Dict

data = {
    "Drogon": {
        "cases": [
            {
                "name": "case1",
                "iterations": [
                    {
                        "name": "iter-0",
                        "realizations": [0, 1, 2, 3, 4],
                        "attributes": [
                            {
                                "name": "attr1",
                                "surface_names": ["top", "base"],
                                "surface_dates": [20010101, 20020101],
                            },
                            {
                                "name": "attr2",
                                "surface_names": ["top", "middle", "base"],
                                "surface_dates": [],
                            },
                        ],
                    },
                    {
                        "name": "iter-1",
                        "realizations": [0, 1, 2, 3, 4],
                        "attributes": [
                            {
                                "name": "attr1",
                                "surface_names": ["top", "base"],
                                "surface_dates": [20010101, 20020101],
                            },
                            {
                                "name": "attr2",
                                "surface_names": ["top", "middle", "base"],
                                "surface_dates": [],
                            },
                        ],
                    },
                ],
            },
            {
                "name": "case2",
                "iterations": [
                    {
                        "name": "pred",
                        "realizations": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                        "attributes": [
                            {
                                "name": "attr3",
                                "surface_names": ["above", "within", "below"],
                                "surface_dates": [20030101, 20100101],
                            }
                        ],
                    },
                    {
                        "name": "pred2",
                        "realizations": [
                            0,
                            1,
                            2,
                            3,
                            4,
                            5,
                            6,
                            7,
                        ],
                        "attributes": [
                            {
                                "name": "attr1",
                                "surface_names": ["above", "within", "below"],
                                "surface_dates": [20030101, 20100101],
                            }
                        ],
                    },
                    {
                        "name": "iter-0",
                        "realizations": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                        "attributes": [
                            {
                                "name": "attr1",
                                "surface_names": ["above", "within", "below"],
                                "surface_dates": [20030101, 20100101],
                            }
                        ],
                    },
                ],
            },
        ]
    }
}


def get_case_names(field_name: str = "Drogon") -> List[str]:
    cases = []
    for case in data[field_name]["cases"]:
        cases.append(case["name"])
    return cases


def _get_case(case_name, field_name: str = "Drogon") -> Dict:
    case = None
    for caseobj in data[field_name]["cases"]:
        if caseobj["name"] == case_name:
            return caseobj
    return case


def _get_iteration(
    case_name: str, iteration_name: str, field_name: str = "Drogon"
) -> Dict:
    iteration = None
    case = _get_case(case_name, field_name=field_name)
    if case is not None:
        for iterationobj in case["iterations"]:
            if iterationobj["name"] == iteration_name:
                return iterationobj
    return iteration


def _get_surface_attribute(
    case_name: str, iteration_name: str, attribute_name: str, field_name: str = "Drogon"
) -> Dict:
    attribute = None
    iteration = _get_iteration(
        case_name=case_name, iteration_name=iteration_name, field_name=field_name
    )
    if iteration is None:
        return []
    for attributeobj in iteration["attributes"]:
        if attributeobj["name"] == attribute_name:
            return attributeobj
    return attribute


def get_iteration_names(case_name: str, field_name: str = "Drogon") -> List[str]:
    iterations = []
    case = _get_case(case_name, field_name)
    if case is None:
        return []
    for iteration in case["iterations"]:
        iterations.append(iteration["name"])
    return iterations


def get_realizations(
    case_name: str, iteration_name: str, field_name: str = "Drogon"
) -> List[int]:

    iteration = _get_iteration(
        case_name=case_name, iteration_name=iteration_name, field_name=field_name
    )
    return iteration["realizations"]


def get_surface_attribute_names(
    case_name: str, iteration_name: str, field_name: str = "Drogon"
) -> List[str]:
    attribute_names = []
    iteration = _get_iteration(
        case_name=case_name, iteration_name=iteration_name, field_name=field_name
    )
    if iteration is None:
        return []
    for attribute in iteration["attributes"]:
        attribute_names.append(attribute["name"])
    return attribute_names


def get_surface_names(
    case_name: str, iteration_name: str, attribute_name: str, field_name: str = "Drogon"
) -> List[str]:
    attr = _get_surface_attribute(
        case_name=case_name,
        iteration_name=iteration_name,
        attribute_name=attribute_name,
        field_name=field_name,
    )
    return attr["surface_names"]


def get_surface_dates(
    case_name: str, iteration_name: str, attribute_name: str, field_name: str = "Drogon"
) -> List[str]:
    attr = _get_surface_attribute(
        case_name=case_name,
        iteration_name=iteration_name,
        attribute_name=attribute_name,
        field_name=field_name,
    )
    return attr["surface_dates"]
