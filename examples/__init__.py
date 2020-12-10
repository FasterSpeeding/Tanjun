import tanjun
from examples import basic_component
from examples import example_config


# Here we define a loader which can be used to easily load all the example
# components into a bot from a mere-link (assuming the environment has all the
# right configurations setup.)
@tanjun.as_loader
def load_examples(client: tanjun.traits.Client) -> None:
    config = example_config.load_config()
    client.add_component(basic_component.BasicComponent(config=config))
