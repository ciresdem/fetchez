#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.modules.gebco
~~~~~~~~~~~~~~~~~~~~~

Fetch General Bathymetric Chart of the Oceans (GEBCO) data.
Supports regional subsetting via Cloud Optimized GeoTIFF (COG)
or full global downloads from BODC.

:copyright: (c) 2010 - 2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import math
import logging
import urllib.parse
from fetchez.modules import FetchModule

logger = logging.getLogger(__name__)

# Base NCSS endpoints for GEBCO 2026
GEBCO_NCSS_URLS = {
    "grid": "https://dap.ceda.ac.uk/thredds/ncss/bodc/gebco/global/gebco_2026/ice_surface_elevation/netcdf/GEBCO_2026.nc",
    "tid": "https://dap.ceda.ac.uk/thredds/ncss/bodc/gebco/global/gebco_2026/type_identifier_grid/netcdf/gebco_2026_tid.nc",
    "sub_ice": "https://dap.ceda.ac.uk/thredds/ncss/bodc/gebco/global/gebco_2026/sub_ice_topo/netcdf/GEBCO_2026_sub_ice_topo.nc",
}

# Base OpenDAP (DODS) endpoints for GEBCO 2026
GEBCO_DAP_URLS = {
    "grid": "https://dap.ceda.ac.uk/thredds/dodsC/bodc/gebco/global/gebco_2026/ice_surface_elevation/netcdf/GEBCO_2026.nc",
    "tid": "https://dap.ceda.ac.uk/thredds/dodsC/bodc/gebco/global/gebco_2026/type_identifier_grid/netcdf/gebco_2026_tid.nc",
    "sub_ice": "https://dap.ceda.ac.uk/thredds/dodsC/bodc/gebco/global/gebco_2026/sub_ice_topo/netcdf/GEBCO_2026_sub_ice_topo.nc",
}

class GEBCO(FetchModule):
    """Fetch GEBCO 2026 bathymetry dynamically via THREDDS NCSS.
    Requires ZERO external dependencies (No GDAL required).
    Downloads true, mathematically cropped .nc files!
    """

    name = "gebco"
    meta_category = "Bathymetry"
    meta_desc = "GEBCO 2026 via NCSS Bounding Box Subsetting"

    def __init__(self, layer="grid", include_tid=False, **kwargs):
        super().__init__(name="gebco_opendap", **kwargs)
        self.layer = layer.lower()
        self.include_tid = str(include_tid).lower() in ["true", "1", "yes"]

    def run(self):
        if not getattr(self, "region", None) or self.region.to_list() == [-180, 180, -90, 90]:
            logger.error("You must provide a strict bounding region (-R) to use the NCSS subsetter!")
            return

        w, e, s, n = self.region.xmin, self.region.xmax, self.region.ymin, self.region.ymax

        base_query = {
            "north": n,
            "south": s,
            "west": w,
            "east": e,
            "horizStride": 1,
            "addLatLon": "true",
            "accept": "netcdf"
        }

        grid_base = GEBCO_NCSS_URLS.get(self.layer, GEBCO_NCSS_URLS["grid"])
        grid_query = base_query.copy()
        grid_query["var"] = "elevation"

        grid_url = f"{grid_base}?{urllib.parse.urlencode(grid_query)}"
        grid_fn = f"gebco_2026_{self.layer}_{w}_{e}_{s}_{n}.nc"

        self.add_entry_to_results(url=grid_url, dst_fn=grid_fn, data_type="netcdf")

        if self.include_tid:
            tid_base = GEBCO_NCSS_URLS["tid"]
            tid_query = base_query.copy()
            tid_query["var"] = "tid"

            tid_url = f"{tid_base}?{urllib.parse.urlencode(tid_query)}"
            tid_fn = f"gebco_2026_tid_{w}_{e}_{s}_{n}.nc"

            self.add_entry_to_results(url=tid_url, dst_fn=tid_fn, data_type="netcdf")


class GEBCO_OpenDAP(FetchModule):
    """Fetch GEBCO 2026 bathymetry dynamically via OpenDAP HTTP Subsetting.
    Requires ZERO external dependencies (No GDAL required).
    """

    name = "gebco_opendap"
    meta_category = "Bathymetry"
    meta_desc = "GEBCO 2026 via OpenDAP Array Subsetting"

    def __init__(self, layer="grid", include_tid=False, **kwargs):
        super().__init__(name="gebco_opendap", **kwargs)
        self.layer = layer.lower()
        # Ensure boolean parsing from YAML
        self.include_tid = str(include_tid).lower() in ["true", "1", "yes"]

    def run(self):
        if not getattr(self, "region", None) or self.region.to_list() == [-180, 180, -90, 90]:
            logger.error("You must provide a strict bounding region (-R) to use the OpenDAP subsetter!")
            return

        w, e, s, n = self.region.xmin, self.region.xmax, self.region.ymin, self.region.ymax

        # GEBCO is 15 arc-seconds (240 pixels per degree)
        # Grid Extents: -180 to 180 (X), -90 to 90 (Y)

        x1 = max(0, int(math.floor((w + 180) * 240)))
        x2 = min(86400, int(math.ceil((e + 180) * 240)))

        y1 = max(0, int(math.floor((s + 90) * 240)))
        y2 = min(43200, int(math.ceil((n + 90) * 240)))

        # Query format: ?variable[y1:1:y2][x1:1:x2],lat[y1:1:y2],lon[x1:1:x2]
        grid_base = GEBCO_DAP_URLS.get(self.layer, GEBCO_DAP_URLS["grid"])
        z_var = "elevation"

        grid_query = f"?{z_var}[{y1}:1:{y2}][{x1}:1:{x2}],lat[{y1}:1:{y2}],lon[{x1}:1:{x2}]"
        # grid_query = f"?{z_var}[0:1:0][0:1:0],lat[{y1}:1:{y2}],lon[{x1}:1:{x2}]"
        grid_url = f"{grid_base}.dods{grid_query}"

        grid_fn = f"gebco_2026_{self.layer}_{w}_{e}_{s}_{n}.nc"

        self.add_entry_to_results(url=grid_url, dst_fn=grid_fn, data_type="netcdf")

        if self.include_tid:
            tid_base = GEBCO_DAP_URLS["tid"]
            tid_query = f"?tid[{y1}:1:{y2}][{x1}:1:{x2}],lat[{y1}:1:{y2}],lon[{x1}:1:{x2}]"
            tid_url = f"{tid_base}.nc{tid_query}"
            tid_fn = f"gebco_2026_tid_{w}_{e}_{s}_{n}.nc"
            self.add_entry_to_results(url=tid_url, dst_fn=tid_fn, data_type="netcdf")
