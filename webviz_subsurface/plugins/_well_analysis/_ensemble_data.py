import logging
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from webviz_config.common_cache import CACHE

from webviz_subsurface._providers import EnsembleSummaryProvider


class EnsembleData:
    """This class holds the summary data provider."""

    def __init__(self, provider: EnsembleSummaryProvider):

        self._provider = provider
