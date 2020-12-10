# Nothing much to see here, just a example bare minimum config file.


class ExampleConfig:
    database_password: str


def load_config() -> ExampleConfig:
    return ExampleConfig()
