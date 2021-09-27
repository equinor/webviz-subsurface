from typing import Optional, Union

from webviz_config._theme_class import WebvizConfigTheme


def unique_colors(
    elements: Union[list, set], theme: Optional[Union[WebvizConfigTheme, dict]] = None
) -> dict:
    """Returns a dict with discrete colors from your theme if that is defined,
    otherwise from the list below. If len(elements) > available unique colors
    the colors will be looped (and therefore not unique...)
    """
    if isinstance(elements, set):
        elements = list(elements)
    elif not isinstance(elements, list):
        raise TypeError("'elements' has to be a list or a set")

    if isinstance(theme, WebvizConfigTheme):
        theme = theme.plotly_theme
    elif theme is None:
        theme = {}
    # otherwise we assume that it is either a dict, a plotly layout object or some other
    # class with a similar .get() method.

    # The try-except is to handle plotly layout dicts as well as plotly themes
    try:
        colors = theme["layout"]["colorway"]
    except KeyError:
        colors = theme.get(
            "colorway",
            [
                "#243746",
                "#eb0036",
                "#919ba2",
                "#7d0023",
                "#66737d",
                "#4c9ba1",
                "#a44c65",
                "#80b7bc",
                "#ff1243",
                "#919ba2",
                "#be8091",
                "#b2d4d7",
                "#ff597b",
                "#bdc3c7",
                "#d8b2bd",
                "#ffe7d6",
                "#d5eaf4",
                "#ff88a1",
            ],
        )
    return {elements[i]: colors[i % len(colors)] for i in range(len(elements))}
