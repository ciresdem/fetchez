# 🌎 Modules and Bundles

Fetchez comes builtin with [70+ different modules](https://fetchez.readthedocs.io/en/latest/modules/index.html) to access geospatial data from various remote apis and local file-systems.

## Data Modules

Fetchez includes a **Module System** in its `ModuleRegistry` that allows you to access various geospatial data sources locally or from around the world.

Modules come with their own arguments to set different data types, modify outputs, set credentials, etc. Hooks can be used to modify or manage modules before, during or after fetching; allowing for full ETL processing workflows using disparate sets of data modules.

Modules define a specific dataset, either a full data collection from a government API, a simple REST service that distributes daily tides or a single file located on your hard-drive.

## Module Bundles

Bundles are YAML configuration files that define a group of Modules, possibly with preset arguments and hooks and can be used in the same ways as standard modules.
You can make your own, or use a pre-configured Bundle from Fetchez or it's extensions.

### Example

**Define your bundle**

Put this in your `~/.fetchez/modules/bundles/` plugin folder

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

* **Run it:** Your new `grav_and_bath` bundle is now registrered in the `BundleRegistry` and available in the fetchez cli:

```bash
fetchez run -R loc:"portland, me" grav_and_bath
```

* **Add it:** You can also use the bundle as a module in `recipes` or can be referenced by other Bundles.

```yaml
project:
  name: "my_harbor"
  region: loc:"portland, me"
  modules:
  - bundle: grav_and_bath
    args: {weight: 1.0}
```

### Extending Bunldes (Plugins and Extensions)
Fetchez is generic. If you are building a custom tool and want to bundle your own modules, you can register your own bundles either in your project or in the `.fetchez` configuration directory and they will be discoverable with the `fetchez.registry.BundleRegistry`

To create an extension where your bundles can be installed and used by `fetchez`, make a directory called 'bundles' in your project; add any YAML module bundles to that directory and register them with `fetchez` in your `pyproject.toml`:

```toml
[project.entry-points."fetchez.modules.bundles"]
my_project_bundles = "my_project.hooks.bundles"
```
