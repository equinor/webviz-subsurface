from webviz_subsurface._utils.formatting import printable_int_list


def test_printable_int_list() -> None:
    assert printable_int_list([1, 2, 5, 6, 9, 8, 19]) == "1-2, 5-6, 8-9, 19"
    assert printable_int_list([5, 3, 4, 0]) == "0, 3-5"
    assert printable_int_list([0, 1, 2, 3, 6]) == "0-3, 6"
    assert printable_int_list([]) == "None"
    assert printable_int_list(None) == "None"
    assert printable_int_list([5]) == "5"
