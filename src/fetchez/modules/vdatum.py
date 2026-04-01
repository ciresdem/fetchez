#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.modules.vdatum
~~~~~~~~~~~~~~~~~~~~~~

Fetch NOAA Tidal Grids (MLLW, MHHW) from vdatum.noaa.gov.

:copyright: (c) 2010 - 2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import re
import logging
import requests
from typing import Optional
from fetchez import core
from fetchez.modules import FetchModule
from fetchez import cli
from fetchez import fred
from fetchez import utils

logger = logging.getLogger(__name__)

VDATUM_DATA_URL = "https://vdatum.noaa.gov/download/data/"
VDATUM_REGIONS = [
    "TIDAL",
    "IGLD85",
    "XGEOID16B",
    "XGEOID17B",
    "XGEOID18B",
    "XGEOID19B",
    "XGEOID20B",
    "VERTCON",
]
TIDAL_DATUMS = ["mhw", "mhhw", "mlw", "mllw", "tss", "mtl"]


@cli.cli_opts(
    help_text="NOAA VDatum Tidal Grids",
    datatype='Filter by datum type (e.g., "mllw", "mhhw", "tidal").',
    update="Force a re-scrape of the NOAA website.",
)
class VDatum(FetchModule):
    name = "vdatum"
    meta_category = "Geodesy"
    meta_desc = "NOAA VDatum Tidal Grids (MLLW, MHHW)"
    meta_agency = "NOAA"
    meta_tags = [
        "vdatum",
        "tidal",
        "mllw",
        "mhhw",
        "noaa",
        "vertical-datum",
        "transformation",
    ]
    meta_region = "USA / Coastal"
    meta_resolution = "Varies (Regional Grids)"
    meta_license = "Public Domain"
    meta_urls = {"home": "https://vdatum.noaa.gov/"}
    meta_aliases = ["tidal_grids"]

    """Fetch NOAA VDatum grids, specifically Tidal Datums (MLLW, MHHW).

    Because these grids are not available in the PROJ CDN, this module
    performs a "heavy" discovery process:

    - Downloads regional ZIP files from NOAA.
    - Inspects internal .inf files to determine bounding boxes.
    - Builds a local spatial index (FRED) for future fast lookups.
    """

    def __init__(self, datatype: Optional[str] = None, update: bool = False, **kwargs):
        super().__init__(name="vdatum", **kwargs)
        self.datatype = datatype.lower() if datatype else None
        self.force_update = update

        self.fred = fred.FRED("vdatum", local=False)

    def _scrape_and_index(self):
        """Scrapes VDatum directory, keeping only the newest regional grids, and parses .met/.inf for bboxes."""

        import zipfile

        logger.info("Scraping VDatum directory for updated grid packages...")
        url = "https://vdatum.noaa.gov/download/data/"
        r = requests.get(url)
        r.raise_for_status()

        zip_links = re.findall(r'href="([^"]+\.zip)"', r.text)
        surveyed_regions = {}

        logger.info(f"Surveying {len(zip_links)} VDatum packages...")
        for zip_name in zip_links:
            zip_url = url + zip_name
            region_base = re.sub(r"_[0-9]+$", "", zip_name.replace(".zip", "").lower())

            if region_base not in surveyed_regions:
                surveyed_regions[region_base] = {
                    "url": zip_url,
                    "filename": zip_name,
                    "region": region_base,
                }

        features = []
        logger.info(
            f"Downloading and indexing {len(surveyed_regions)} latest regional grids..."
        )

        for region_data in surveyed_regions.values():
            zip_name = region_data["filename"]
            zip_url = region_data["url"]

            logger.info(f"Inspecting metadata for: {zip_name}")

            # Download the zip file to the cache using Fred's built-in downloader
            # zip_path = self._download_file(zip_url)
            zip_bn = os.path.basename(zip_url)
            zip_path = zip_bn  # todo: update to cache
            if (
                zip_bn.startswith("vdatum_all")
                or zip_bn.startswith("vdatum_regional")
                or zip_bn.startswith("vdatum_v")
            ):
                continue

            status = core.Fetch(zip_url).fetch_file(zip_bn)
            if status != 0:
                continue

            bbox = None

            if not zip_bn.startswith("vdatum"):
                region_data["type"] = "TIDAL"
            elif "GEOID" in zip_bn:
                region_data["type"] = "GEOID"
            elif "EGM" in zip_bn:
                region_data["type"] = "EGM"
            else:
                region_data["type"] = region_data["region"]

            try:
                with zipfile.ZipFile(zip_path, "r") as z:
                    # Search inside the zip for the metadata files
                    namelist = z.namelist()
                    for member in namelist:
                        if member.endswith(".met") or member.endswith(".inf"):
                            if member.startswith("geoid"):
                                continue
                            content = z.read(member).decode("utf-8", errors="ignore")
                            bbox = self._parse_bbox(content, member)

                            if 0.0 in bbox:
                                continue
                            if bbox:
                                break
                    if bbox:
                        min_x, max_x, min_y, max_y = bbox
                        geom = {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [min_x, min_y],
                                    [max_x, min_y],
                                    [max_x, max_y],
                                    [min_x, max_y],
                                    [min_x, min_y],
                                ]
                            ],
                        }

                        if region_data["type"] == "TIDAL":
                            for t in TIDAL_DATUMS:
                                self.fred.add_survey(
                                    geom,
                                    Name=os.path.basename(member).replace(
                                        ".met", ".gtx"
                                    ),
                                    ID=zip_bn.split(".")[0],
                                    Agency="NOAA",
                                    DataLink=zip_url,
                                    DataType=t,
                                    # ",".join(TIDAL_DATUMS)
                                    # if region_data["region"] == "TIDAL"
                                    # else "geoid",
                                    DataSource="vdatum",
                                )

            except zipfile.BadZipFile:
                logger.warning(f"Corrupted zip file downloaded: {zip_name}")
                continue

        self.fred.save()

        logger.info(f"Successfully indexed {len(features)} latest VDatum regions.")

    def _parse_bbox(self, text, filename):
        """Extracts bounding box coordinates from either .inf or new .met files."""

        # if filename.endswith('.inf'):
        meta = self._parse_inf(text)
        return (meta["w"], meta["e"], meta["s"], meta["n"])

    def _parse_release_date(self, text, filename):
        d = {}
        for line in text.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                d[k.strip().lower().split(".")[-1]] = v.strip()
        d.get("release", 0)

    def _parse_inf(self, text):
        """Helper to extract bounds from VDatum INF format."""

        d = {}
        for line in text.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                d[k.strip().lower().split(".")[-1]] = v.strip()
        try:
            return {
                "w": utils.x360(float(d.get("minlon", 0))),
                "e": utils.x360(float(d.get("maxlon", 0))),
                "s": float(d.get("minlat", 0)),
                "n": float(d.get("maxlat", 0)),
            }
        except Exception:
            return None

    def run(self):
        if self.force_update or not self.fred.features:
            self._scrape_and_index()

        if not self.fred.features:
            logger.error("VDatum index is empty. Scrape failed.")
            return self

        results = self.fred.search(region=self.region)

        for r in results:
            if self.datatype and self.datatype not in r.get("DataType", ""):
                continue

            self.add_entry_to_results(
                url=r["DataLink"],
                dst_fn=os.path.basename(r["DataLink"]),
                data_type=r["DataType"],
                agency="NOAA",
                title=f"VDatum Grid ({r['ID']})",
            )

        return self
