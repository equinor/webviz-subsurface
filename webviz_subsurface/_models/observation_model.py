from pathlib import Path
import yaml

from fmu.ensemble import Observations


class ObservationModel:
    def __init__(self, observation_file: Path) -> None:
        self.observations = self.load_yaml(observation_file)
        print(self.observations)

    @staticmethod
    def load_yaml(yaml_file):
        with open(Path(yaml_file), "r") as stream:
            return yaml.safe_load(stream)
