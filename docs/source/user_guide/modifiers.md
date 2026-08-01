# 🛠️ Domain Modifiers

Fetchez includes a **Modifier Engine** in its `ModifierRegistry` that can automatically mutate your YAML recipes as they are loaded, allowing for complete runtime control of the pipeline.

## Using a Modifier

Add a `modifiers` argument to the top of your YAML recipe:

```yaml
---
project:
  name: "My_Project"

modifiers:
  - name: exclude_module
    args:
      modules: margrav/charts
region: [-120.0, -119.75, 33.0, 33.25]
modules:
  - bundle: my-bathymetry-bundle
```

*What happens under the hood?*

By specifying the modifier: `exclude_module`, the engine intercepts your recipe and removes the named `margrav` and `charts` modules from the module Bundle `my-bathymetry-bundle`. Modifiers take an input recipe config and do something to or with it and return the possibly mutated bundle, right before sending to the core Fetchez engine for processing.

## Extending Modifiers (Plugins and Extensions)
Fetchez is generic. If you are building a custom tool (like a specialized DEM engine), you can register your own recipe modifiers in Python. Make a directory called 'my_project/recipes/modifiers' and put all your modifier python files within it:

```python
from fetchez.recipes.modifiers import BaseModifier

class WeatherModifier(BaseModifier):
    name = "wrf_weather"

    @classmethod
    def apply(cls, config):
        config["region"] = [-180, 180, -90, 90] # Force global fetch
        return config
```

Then register your project with fetchez in your `pyproject.toml`:

```toml
[project.entry-points."fetchez.recipes.modifiers"]
my_project_modifiers = "my_project.recipes.modifiers"
```
