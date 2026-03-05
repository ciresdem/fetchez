# Fetchez Documentation

**Fetch geospatial data with ease.**

*Fetchez Les Données*

**Fetchez** is a lightweight, modular and highly extendable Python library and command-line tool designed to discover, retrieve and process geospatial data from a wide variety of public repositories.

## Quickstart

**Installation:**

```bash
pip install fetchez
```

### Command Line Interface:

Fetch Copernicus topography and NOAA multibeam bathymetry for a specific bounding box in one command:

```bash
fetchez -R loc:"Miami, FL" copernicus multibeam --audit-log miami_audit.json
```

### Python API:

```python
import fetchez

# Search
bathy_mods = fetchez.search("bathymetry")

# Get Data (Returns list of local file paths)
files = fetchez.get("nos_hydro", region=[-120, -118, 33, 34], min_year=2020)

# Fetch Electronic Nautical Chart data from NOAA
files = fetchez.get(region=[-120, -118, 33, 34], "charts", hooks=['unzip', 'fn_filter:match=.000', 'audit'])
```

## Key Features

* **Unified Interface**: Access [50+ different modules](https://fetchez.readthedocs.io/en/latest/modules/index.html) using the exact same syntax.

* **Parallel Fetching**: High-performance, multi-threaded downloading with automatic retry, timeout handling, and partial-download resumption.

* **Infrastructure as Code:** Define complex data pipelines, cropping, and gridding workflows using CLI switches or simple YAML "Recipes".

* **Pipeline Hooks**: Transparently stream, filter, and process data (via globato and transformez) as it is being downloaded.

* **Extendable Design**: Through hooks, presets, recipes, schemas and extensions, `fetchez` can be endlessly expanded to perform specific tasks.

```{toctree}
:maxdepth: 2
:hidden:
:caption: User Guide:

user_guide/index
api/index
contribute/index
modules/index
```

Indices and tables
==================

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
