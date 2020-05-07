import webviz_subsurface._private_plugins.tornado_plot as tornado_plot


def test_printable_int_list():
    assert (
        tornado_plot.printable_int_list([1, 2, 5, 6, 9, 8, 19]) == "1-2, 5-6, 8-9, 19"
    )
    assert tornado_plot.printable_int_list([5, 3, 4, 0]) == "0, 3-5"
    assert tornado_plot.printable_int_list([0, 1, 2, 3, 6]) == "0-3, 6"
    assert tornado_plot.printable_int_list([]) == "None"
    assert tornado_plot.printable_int_list(None) == "None"
    assert tornado_plot.printable_int_list([5]) == "5"
