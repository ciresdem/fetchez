#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.modules.copernicus_marine
~~~~~~~~~~~~~~~~~~~~

Fetch data from the copernicus marine store, using
the copernincusmarine api.

:copyright: (c) 2025 - 2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import logging
from fetchez.modules import FetchModule
from fetchez import cli
from fetchez.core import get_raw_credentials

try:
    import copernicusmarine

    HAS_COPMARINE = True
except ImportError:
    HAS_COPMARINE = False

logger = logging.getLogger(__name__)


@cli.cli_opts(
    help_text="Copernicus Marine SDB Fetcher",
    dataset_id="The Copernicus Marine dataset ID (e.g., cmems_obs-mob_glo_bathy_sdb_multi_15m_pt15s)",
    username="Copernicus Marine Username (or set in netrc)",
    password="Copernicus Marine Password (or set in netrc)",
)
class CopernicusMarineSDB(FetchModule):
    """Fetches Satellite Derived Bathymetry from the Copernicus Marine Service."""

    name = "copernicus_marine"
    meta_category = "Bathymetry"
    meta_desc = "Copernicus Marine SDB (15m)"
    meta_agency = "ESA"
    meta_tags = ["cdse", "copernicus", "esa", "satellite", "odata", "imagery"]
    meta_region = "Global"
    meta_resolution = "Varies"
    meta_license = "TBD"

    def __init__(self, dataset_id=None, username=None, password=None, **kwargs):
        super().__init__(**kwargs)
        self.dataset_id = (
            dataset_id or "cmems_obs-sdb_glo_phy_comp_my_100m-l4-s2_static"
        )

        self.username, self.password = get_raw_credentials("https://data.marine.copernicus.eu", "https://data.marine.copernicus.eu")
        if not self.username or not self.password:
            logger.warning("No credentials found in .netrc for CDSE.")
            return None

    def run(self):
        if not HAS_COPMARINE:
            logger.error("Missing libraries. Run: `pip install copernicusmarine`")
            return self

        if not self.username or not self.password:
            logger.error(
                "Copernicus Marine credentials required. Pass them or set env vars."
            )
            return self

        logger.info(
            f"[{self.name}] Querying Copernicus Marine for {self.dataset_id}..."
        )

        try:
            # output_folder = os.path.join(self._outdir, self.name)
            # os.makedirs(output_folder, exist_ok=True)

            out_fn = f"{self.dataset_id}_{self.region.xmin}_{self.region.ymin}_{self.region.xmax}_{self.region.ymax}.nc"
            out_path = os.path.join(self._outdir, out_fn)
            copernicusmarine.subset(
                dataset_id=self.dataset_id,
                username=self.username,
                password=self.password,
                minimum_longitude=self.region.xmin,
                maximum_longitude=self.region.xmax,
                minimum_latitude=self.region.ymin,
                maximum_latitude=self.region.ymax,
                output_directory=self._outdir,
                output_filename=out_fn,
                # overwrite_output_data=True,
            )
            if os.path.exists(out_path):
                self.add_entry_to_results(
                    url=f"file://{out_path}",
                    dst_fn=out_fn,
                    data_type="copernicus_sdb",
                )

        except Exception as e:
            logger.exception(f"[{self.name}] Official toolkit failed: {e}")

        return self
