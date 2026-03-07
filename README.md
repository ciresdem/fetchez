<p align="center">
  <img src="https://github.com/continuous-dems/fetchez/blob/modules/docs/source/_static/cudem_logo.svg" width="200" alt="Fetchez Logo">
</p>
<h1 align="center">Fetchez</h1>
<p align="center"><strong>Fetch geospatial data with ease.</strong></p>

*Fetchez Les Données*

[![Version](https://img.shields.io/badge/version-0.4.2-blue.svg)](https://github.com/continuous-dems/fetchez)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://www.python.org/)
[![PyPI version](https://badge.fury.io/py/fetchez.svg)](https://badge.fury.io/py/fetchez)
[![project chat](https://img.shields.io/badge/zulip-join_chat-brightgreen.svg)](https://cudem.zulip.org)

**Fetchez** is a lightweight, modular and highly extendable Python library and command-line tool designed to discover and retrieve geospatial data from a wide variety of public repositories. Originally part of the [CUDEM](https://github.com/continuous-dems/cudem) project, Fetchez is now a standalone tool capable of retrieving Bathymetry, Topography, Imagery, and Oceanographic data (and more!) from sources like NOAA, USGS, NASA, and the European Space Agency.

---

### ❓ Why Fetchez?

Geospatial data access is fragmented. You often need one script to scrape a website for tide stations, another to download LiDAR from an S3 bucket, and a third to parse a local directory of shapefiles.

**Fetchez unifies it all.**

* **Unified Interface**: Access [50+ different modules](https://fetchez.readthedocs.io/en/latest/modules/index.html) using the exact same syntax.

* **Parallel Fetching**: High-performance, multi-threaded downloading with automatic retry, timeout handling, and partial-download resumption.

* **Infrastructure as Code:** Define complex data pipelines, cropping, and gridding workflows using CLI switches or simple YAML "Recipes".

* **Pipeline Hooks**: Transparently stream, filter, and process data (via globato and transformez) as it is being downloaded.

* **Extendable Design**: Through hooks, presets, recipes, schemas and extensions, `fetchez` can be endlessly expanded to perform specific tasks.

---

## 📦 Installation

```bash
pip install fetchez
```

## 🐄 Quickstart
Fetch Copernicus topography and NOAA multibeam bathymetry for a specific bounding box in one command:

### CLI

```bash
fetchez -R loc:"Miami, FL" copernicus multibeam --audit:file=miami_audit.json
```

Or run a full processing pipeline from a YAML recipe:

```bash
fetchez recipes/my_dem_project.yaml
```

### Python

```python
import fetchez

# Fetch Electronic Nautical Chart data from NOAA
files = fetchez.get(region=[-120, -118, 33, 34], "charts", hooks=['unzip', 'fn_filter:match=.000', 'audit'])
```

---

## 📚 Documentation
Would you like to know more? Check out our [Official Documentation](https://fetchez.readthedocs.io) to learn about:

* **The Python API:** Build custom fetchers into your apps.

* **Recipes & YAML:** Run custom workflows from a simple YAML configuration.

* **Hooks & Presets:** Automate unzipping, filtering, and processing.

* **Domain Schemas:** Enforce rigorous geospatial standards automatically.

* **Custom Plugins:** Write your own data fetchers, processing hooks and extensions.

---

## ⚖ License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/continuous-dems/fetchez/blob/main/LICENSE) file for details.

Copyright (c) 2010-2026 Regents of the University of Colorado
