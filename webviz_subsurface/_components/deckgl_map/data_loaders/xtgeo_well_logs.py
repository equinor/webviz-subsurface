from typing import Dict, Optional, Any
from dataclasses import dataclass

from xtgeo import Well


@dataclass
class DeckGLLogsContext:
    well: str
    log: str
    logrun: str

class XtgeoLogsJson:
    def __init__(
        self,
        well: Well,
        log: str,
        logrun: str = "log",
    ):
        self._well = well

        self._logrun = logrun
        self._initial_log = log
        if well.mdlogname is None:
            well.geometrics()

    @property
    def _log_names(self):
        return (
            [
                logname
                for logname in self._well.lognames
                if logname not in ["Q_MDEPTH", "Q_AZI", "Q_INCL", "R_HLEN"]
            ]
            if not self._initial_log
            else [self._initial_log]
        )

    def _generate_curves(self):
        curves = []

        # Add MD and TVD curves
        curves.append(self._generate_curve(log_name="MD"))
        curves.append(self._generate_curve(log_name="TVD"))
        # Add additonal logs, skipping geometrical logs if calculated

        for logname in self._log_names:
            curves.append(self._generate_curve(log_name=logname))
        return curves

    def _generate_data(self):
        # Filter dataframe to only include relevant logs
        curve_names = [self._well.mdlogname, "Z_TVDSS"] + self._log_names

        dframe = self._well.dataframe[curve_names]
        dframe = dframe.reindex(curve_names, axis=1)
        return dframe.values.tolist()

    def _generate_header(self) -> Dict[str, Any]:
        return {
            "name": self._logrun,
            "well": self._well.name,
            "wellbore": None,
            "field": None,
            "country": None,
            "date": None,
            "operator": None,
            "serviceCompany": None,
            "runNumber": None,
            "elevation": None,
            "source": None,
            "startIndex": None,
            "endIndex": None,
            "step": None,
            "dataUri": None,
        }

    @staticmethod
    def _generate_curve(
        log_name: str,
        description: Optional[str] = "continuous",
        value_type: str = "float",
    ) -> Dict[str, Any]:
        return {
            "name": log_name,
            "description": description,
            "valueType": value_type,
            "dimensions": 1,
            "unit": "m",
            "quantity": None,
            "axis": None,
            "maxSize": 20,
        }

    @property
    def data(self):
        return {
            "header": self._generate_header(),
            "curves": self._generate_curves(),
            "data": self._generate_data(),
            "metadata_discrete": {},
        }
