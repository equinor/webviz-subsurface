from dash import html

def error(error_message: str) -> html.Div:
    return html.Div(children=error_message, style={"color": "red"})