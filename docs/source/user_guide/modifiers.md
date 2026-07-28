# 🛠️ Domain Modifiers

While standard Recipes are great for chaining commands, sometimes you need to inject on-the-fly runtime changes to a recipe across an entire project.

Fetchez includes a **Modifier Engine** that can automatically mutate your YAML recipes as they are loaded, allowing for complete control of the pipeline.

## Using a Modifier

We'll take a usage example from `globato` here to show how to use modifiers.

Add a `modifiers` argument to the top of your YAML recipe:

```yaml
---
project:
  name: "My_Project"

modifier: "cudem" # Loads the CUDEM modifier
region: [-120.0, -119.75, 33.0, 33.25] # Your exact delivery tile
```

*What happens under the hood?*

By specifying modifier: "cudem", the engine intercepts your recipe. It automatically calculates that a CUDEM delivery tile requires a 6-cell overlap at 1/9th arc-second resolution. It expands your fetching bounding box, injects the correct EPSG codes into your gridding hooks, and appends a final `raster_crop` hook to snap the finished DEM back to your requested tile extents.

## Extending Modifiers (Plugins and Extensions)
Fetchez is generic. If you are building a custom tool (like a specialized DEM engine), you can register your own modifiers in Python. Make a directory called 'my_project/recipes/modifiers' and put all your modifier python files within it:

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
