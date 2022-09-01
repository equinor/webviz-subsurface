from dash import html


def error(error_message: str) -> html.Div:
    return html.Div(error_message)
