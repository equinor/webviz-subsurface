from fmu.sumo.explorer import Explorer  # type: ignore
from fmu.sumo.explorer import Case  # type: ignore


def create_explorer(access_token: str) -> Explorer:
    return Explorer(env="dev", token=access_token, interactive=False)


def create_interactive_explorer() -> Explorer:
    return Explorer(env="dev", interactive=True)
