# Fetchez Documentation

**Fetch geospatial data with ease.**

*Fetchez Les Données*

**Fetchez** is a robust, highly modular and extendable Python framework designed to orchestrate complex geospatial data engineering workflows.

Originally developed as the core fetching engine for the [CUDEM](https://github.com/continuous-dems/cudem) project, Fetchez has evolved into a standalone ETL platform. It seamlessly retrieves Bathymetry, Topography, Imagery, and Oceanographic data from dozens of global repositories (NOAA, USGS, Copernicus, ESA) and processes it on the fly.

## Quickstart

**Installation:**

```bash
pip install fetchez
```

### Command Line Interface:

Fetch Copernicus topography and NOAA multibeam bathymetry for a specific bounding box in one command:

```bash
fetchez run -R loc:"Miami, FL" --global-hook audit copernicus multibeam
```

### Python API:

```python
import fetchez

# Search
bathy_mods = fetchez.search("bathymetry")

# Get Data (Returns list of local file paths)
files = fetchez.get("nos_hydro", region=[-120, -118, 33, 34], min_year=2020)

# Fetch Electronic Nautical Chart data from NOAA
files = fetchez.get("charts", region=[-120, -118, 33, 34], hooks=['unzip', 'filename_filter:match=.000,stage="pre"', 'audit'])
```

## Key Features

* **Unified Interface**: Access [80+ different modules](https://fetchez.readthedocs.io/en/latest/modules/index.html) using the exact same syntax.

* **Parallel Fetching**: High-performance, multi-threaded downloading with automatic retry, timeout handling, and partial-download resumption.

* **Infrastructure as Code:** Define complex data pipelines, cropping, and gridding workflows using CLI switches or simple YAML "Recipes".

* **Pipeline Hooks**: Transparently stream, filter, and process data as it is being downloaded.

* **Infinite Extensibility:** Built on a modern plugin architecture. Drop custom Python scripts into a local folder, or install community extensions via `pip` to add your own data sources, domain schemas, processing hooks and more.


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
