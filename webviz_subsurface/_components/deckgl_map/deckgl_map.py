import json
from typing import Any, Dict, List, Union

import pydeck
from typing_extensions import Literal
from webviz_subsurface_components import DeckGLMap as DeckGLMapBase

from .types.deckgl_props import DeckGLMapProps


class DeckGLMap(DeckGLMapBase):
    """Wrapper for the wsc.DeckGLMap with default props."""

    def __init__(
        self,
        id: Union[str, Dict[str, str]],
        layers: List[pydeck.Layer],
        bounds: List[float] = DeckGLMapProps.bounds,
        edited_data: Dict[str, Any] = DeckGLMapProps.edited_data,
        resources: Dict[str, Any] = {},
        **kwargs: Any,
    ) -> None:
        """Args:
        id: Unique id
        layers: A list of pydeck.Layers
        bounds: ...
        """  # Possible to get super docstring using e.g. @wraps?
        super().__init__(
            id=id,
            layers=[json.loads(layer.to_json()) for layer in layers],
            bounds=bounds,
            editedData=edited_data,
            resources=resources,
            **kwargs,
        )
