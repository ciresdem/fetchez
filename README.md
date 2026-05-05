<!-- <p align="center"> -->
<!-- 	<a href="https://github.com/continuous-dems"> -->
<!-- 		<img src="https://github.com/continuous-dems/fetchez/blob/modules/docs/source/_static/continuous_dems_logo.svg" height="80" alt="Continuous DEMs Logo"> -->
<!-- 	</a> -->
<!-- </p> -->
<h1 align="center">Fetchez</h1>
<p align="center"><strong>Fetch geospatial data with ease.</strong></p>

<p align="center">
  <a href="https://github.com/continuous-dems/fetchez"><img src="https://img.shields.io/badge/version-0.6.2-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.12+-yellow.svg" alt="Python"></a>
  <a href="https://badge.fury.io/py/fetchez"><img src="https://badge.fury.io/py/fetchez.svg" alt="PyPI version"></a>
  <a href="https://cudem.zulip.org"><img src="https://img.shields.io/badge/zulip-join_chat-brightgreen.svg" alt="Project Chat"></a>
</p>

**Fetchez** is a lightweight, modular, and highly extendable Python framework designed to orchestrate geospatial data engineering workflows.

Originally developed as the core fetching engine for the [CUDEM](https://github.com/ciresdem/cudem) project, Fetchez has evolved into a standalone ETL platform. It seamlessly retrieves Bathymetry, Topography, Imagery, and Oceanographic data from dozens of global repositories (NOAA, USGS, Copernicus, ESA) and processes it on the fly.

---

### ❓ Why Fetchez?

Geospatial data engineering is traditionally fragmented. You often need one script to query an API, another tool to download the files, a GIS application to clip the data, and complex shell scripts to tie it all together.

**Fetchez unifies the entire pipeline.**

* **Unified Interface**: Access [50+ different modules](https://fetchez.readthedocs.io/en/latest/modules/index.html) using the exact same syntax.

* **Parallel Fetching**: High-performance, multi-threaded downloading with automatic retry, timeout handling, and partial-download resumption.

* **Infrastructure as Code:** Define complex data pipelines, cropping, and gridding workflows using CLI switches or simple YAML "Recipes".

* **Pipeline Hooks**: Transparently stream, filter, and process data (via globato and transformez) as it is being downloaded.

* **Infinite Extensibility:** Built on a modern plugin architecture. Drop custom Python scripts into a local folder, or install community extensions via `pip` to add your own data sources, domain schemas, processing hooks, etc.

---

## 📦 Installation

```bash
pip install fetchez
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

---

## 📚 Documentation
Would you like to know more? Check out our [Official Documentation](https://fetchez.readthedocs.io) to learn about:

* **Modules & Bundles:** Discover and learn about data fetchers.

* **The Python API:** Build custom fetchers into your apps.

* **Recipes & YAML:** Run custom workflows from a simple YAML configuration.

* **Hooks & Presets:** Automate unzipping, filtering, and processing.

* **Domain Schemas:** Enforce rigorous geospatial standards automatically.

* **Custom Plugins:** Write your own data fetchers, processing hooks and extensions.

---

## ⚖ License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/continuous-dems/fetchez/blob/main/LICENSE) file for details.

Copyright (c) 2010-2026 Regents of the University of Colorado
