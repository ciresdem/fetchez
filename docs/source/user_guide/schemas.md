# 🏛️ Domain Schemas

While standard Recipes are great for chaining commands, sometimes you need to enforce rigorous geospatial standards across an entire project—like exact arc-second resolutions, cell overlaps, and grid-node vs. pixel-node registration.

Fetchez includes a **Schema Engine** that can automatically scan your YAML recipes to enforce these rules.

## Using a Schema

Add a `schemas` argument to the top of your YAML recipe, in this example we'll use a theoretical `schema` that would make sure the `region` parameter is a strit 1/4 degree tile:

```yaml
project:
  name: "My_Strict_Project"

schemas: "cudem-tile" # Loads the CUDEM-tile ruleset
region: [-120.0, -119.75, 33.0, 33.25] # Your exact delivery tile
```

*What happens under the hood?*

By specifying schema: "cudem", the engine intercepts your recipe and checks your region to make sure it snaps directly to a quarter degree tile in WGS84. It will return the validity of the recipe based on that schema along with any errors it found.

## Extending Schemas (Plugins and Extensions)
Fetchez is generic. If you are building a custom tool (like a specialized DEM engine), you can register your own schemas in Python. Make a directory called 'my_project/recipes/schemas' and put all your schema python files within it:

```python
from fetchez.schema import BaseSchema

class WeatherSchema(BaseSchema):
    name = "wrf_global_weather"

    @classmethod
    def validate(cls, config):
        from fetchez.spatial import Region
        local_region = Region(*config.get("region"))
        global_region = Region(-180, 180, -90, 90])
        if local_region != global_region:
            return False, ["local_region is not global"]
        return True, []

```

Then register your project with fetchez in your `pyproject.toml`:

```toml
[project.entry-points."fetchez.recipes.schemas"]
my_project_schemas = "my_project.recipes.schemas"
```
