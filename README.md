<!-- <p align="center"> -->
<!-- 	<a href="https://github.com/continuous-dems"> -->
<!-- 		<img src="https://github.com/continuous-dems/fetchez/blob/modules/docs/source/_static/continuous_dems_logo.svg" height="80" alt="Continuous DEMs Logo"> -->
<!-- 	</a> -->
<!-- </p> -->
<h1 align="center">Fetchez</h1>
<p align="center"><strong>Fetch geospatial data with ease.</strong></p>

<p align="center">
  <a href="https://github.com/continuous-dems/fetchez"><img src="https://img.shields.io/badge/version-0.7.0-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.12+-yellow.svg" alt="Python"></a>
  <a href="https://badge.fury.io/py/fetchez"><img src="https://badge.fury.io/py/fetchez.svg" alt="PyPI version"></a>
  <a href="https://anaconda.org/conda-forge/fetchez"><img src="https://img.shields.io/conda/vn/conda-forge/fetchez.svg" alt="Conda Version"></a>
  <a href="https://cudem.zulip.org"><img src="https://img.shields.io/badge/zulip-join_chat-brightgreen.svg" alt="Project Chat"></a>
</p>

**Fetchez** is a lightweight, modular, and highly extendable Python framework designed to orchestrate geospatial data engineering workflows.

Originally developed as the core fetching engine for the [CUDEM](https://github.com/ciresdem/cudem) project, Fetchez has evolved into a standalone ETL platform. It seamlessly retrieves Bathymetry, Topography, Imagery, and Oceanographic data from dozens of global repositories (NOAA, USGS, Copernicus, ESA) and processes it on the fly.

---

## 📦 Installation

```bash
pip install fetchez
```

**Optional Extensions:**
To enable module specific library dependencies, install with the desired extras:

```bash
pip install fetchez[full]
```

## 🐄 Quickstart
Fetch Copernicus topography and NOAA multibeam bathymetry for a specific bounding box in one command:

### CLI

```bash
fetchez run -R loc:"Miami, FL" --global-hook audit copernicus multibeam
```

Or run a full processing pipeline from a YAML recipe:

```bash
fetchez recipes run recipes/my_dem_project.yaml
```

### Python

```python
import fetchez

# Fetch Electronic Nautical Chart data from NOAA
files = fetchez.get("charts", region=[-120, -118, 33, 34], hooks=['unzip', 'filename_filter:match=.000', 'audit'])
```

### DEM Building with Globato
While Fetchez handles the data retrieval and point-streaming, its sister project **Globato** provides the `multi_stack` accumulators and multi-resolution interpolation engines needed to turn those streams into production-grade Digital Elevation Models. [Check it out!](https://github.com/continuous-dems/globato)

---

## 📚 Documentation
Would you like to know more? Check out our [Official Documentation](https://fetchez.readthedocs.io) to learn about:

* **Modules & Bundles:** Discover and learn about the over [80+ different modules](https://fetchez.readthedocs.io/en/latest/modules/index.html) availabel.

* **The Python API:** Build custom fetch modules and run full processing pipelines in your apps.

* **Recipes & YAML:** Build and run custom workflows from a simple YAML or JSON configuration.

* **Hooks & Presets:** Automate unzipping, filtering, and processing fetch modules.

* **Domain Schemas:** Enforce rigorous geospatial standards automatically.

* **Custom Plugins:** Write your own data fetch modules, processing hooks, extensions and recipes.

* **Execution Lifecycle:** Learn about the distinct phases (`manifest` -> `file` -> `stream` -> `collection`) of fetchez module hook processing.

---

## 🛠️ Used By

This project is used by the following open-source projects:

* **[globato](https://github.com/continuous-dems/globato)** - A full Fetchez extension, adding DEM optimized hooks, modules, streams and more.
* **[ivert](https://github.com/continuous-dems/ivert)** - Used to fetch IceSat2 Data.
* **[transformez](https://github.com/continuous-dems/transformez)** - Used to fetch vertical transformation data.

*Are you using this project? Open a Pull Request to add your project to the list!*

---

## ⚖ License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/continuous-dems/fetchez/blob/main/LICENSE) file for details.

Copyright (c) 2010-2026 Regents of the University of Colorado
