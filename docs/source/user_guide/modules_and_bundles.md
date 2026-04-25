# 🌎 Modules and Bundles

Fetchez comes builtin with [70+ different modules](https://fetchez.readthedocs.io/en/latest/modules/index.html) to access geospatial data from various remote apis and local file-systems.

## Data Modules

Fetchez includes a powerful **Module System** that allows you to access various geospatial data sources locally or from around the world.

Modules come with their own arguments to set different data types, modify outputs, set credentials, etc. Hooks can be used to modify modules before, during or after fetching; allowing for full ETL processing workflows.

## Module Bundles


**Define your bundle**

Put this in your `~/.fetchez/bundles/` plugin folder

```yaml
name: grav_and_bath
description: >
  Some fast bathymetry data sources.
modules:
  - module: margrav
    args:
      weight: .01
  - module: nos_hydro
    args:
      datatype: "xyz"
      weight: .35
    hooks:
      - name: unzip
      - name: set_datatype
        args:
          data_type: "nos_xyz"
  - module: charts
    args:
      weight: .15
    hooks:
      - name: unzip
      - name: filename_filter
        args:
          match: ".000"
          stage: "file"
      - name: set_datatype
        args:
          data_type: "charts_000"
```

**Use the bundle in a recipe**

Add the bundle to your recipe!

```yaml
project:
  name: "my_harbor"
  region: [-120.5, -120.0, 34.0, 34.5]
  modules:
  - bundle: grav_and_bath
    args: {weight: 1.0}
    """
```

### Extending Bunldes (Plugins and Extensions)
Fetchez is generic. If you are building a custom tool and want to bundle your own modules, you can register your own bundles either in your project or in the .fetchez configuration directory and they will be discoverable with the `fetchez.registry.BundleRegistry`

In your project, make a directory called 'bundles'; add any YAML module bundles to that directory and register them with `fetchez` in your `pyproject.toml`:

```toml
[project.entry-points."fetchez.bundles"]
my_project_recipes = "my_project.bundles"
```
