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
import json
import logging
import requests
from datetime import datetime
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
TIDAL_DATUMS = ['mhw', 'mhhw', 'mlw', 'mllw', 'tss', 'mtl']

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

        # Find all zip file links
        zip_links = re.findall(r'href="([^"]+\.zip)"', r.text)

        surveyed_regions = {}

        # =========================================================
        # PHASE 1: HTTP HEAD Survey (Find the newest versions)
        # =========================================================
        logger.info(f"Surveying {len(zip_links)} VDatum packages...")
        for zip_name in zip_links:
            zip_url = url + zip_name

            # try:
            #     head_r = requests.head(zip_url, timeout=5)
            #     last_mod_str = head_r.headers.get('Last-Modified', '')

            #     # Use standard datetime parsing for the HTTP format
            #     dt = datetime.strptime(last_mod_str, "%a, %d %b %Y %H:%M:%S %Z")
            #     date_str = dt.isoformat()
            # except Exception as e:
            #     logger.debug(f"Could not parse date for {zip_name}: {e}")
            #     # Fallback to epoch so it gets overwritten by any successful date
            #     date_str = "1970-01-01T00:00:00"
            # # Use a HEAD request (extremely fast, downloads no grid data)
            # try:
            #     head_r = requests.head(zip_url, timeout=5)
            #     last_mod_str = head_r.headers.get('Last-Modified', '')
            #     dt = email.utils.parsedate_to_datetime(last_mod_str)
            #     date_str = dt.isoformat()
            # except Exception:
            #     date_str = "1970-01-01T00:00:00+00:00"

            # Extract base region (e.g. 'chesapeake_bay_8301' -> 'chesapeake_bay')
            # Strips the trailing underscore and digits often used for versions/dates
            region_base = re.sub(r'_[0-9]+$', '', zip_name.replace('.zip', '').lower())
            # print(region_base)
            # Only keep the newest package for this region
            if region_base not in surveyed_regions:# or date_str > surveyed_regions[region_base]['date']:
                surveyed_regions[region_base] = {
                    #"date": date_str,
                    "url": zip_url,
                    "filename": zip_name,
                    "region": region_base
                }

        # =========================================================
        # PHASE 2: Download & Extract Bounding Boxes
        # =========================================================
        features = []
        logger.info(f"Downloading and indexing {len(surveyed_regions)} latest regional grids...")

        for region_data in surveyed_regions.values():
            zip_name = region_data["filename"]
            zip_url = region_data["url"]

            logger.info(f"Inspecting metadata for: {zip_name}")

            # Download the zip file to the cache using Fred's built-in downloader
            #zip_path = self._download_file(zip_url)
            zip_bn = os.path.basename(zip_url)
            zip_path = zip_bn # todo: update to cache
            if zip_bn.startswith("vdatum_all") or zip_bn.startswith("vdatum_regional") or zip_bn.startswith("vdatum_v"):
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

            print(region_data)
            try:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    # Search inside the zip for the metadata files
                    namelist = z.namelist()
                    for member in namelist:
                        if member.endswith(".met") or member.endswith(".inf"):
                            if member.startswith("geoid"):
                                continue
                            content = z.read(member).decode('utf-8', errors='ignore')
                            bbox = self._parse_bbox(content, member)

                            if 0.0 in bbox:
                                continue
                            if bbox:
                                break
                    if bbox:
                        min_x, max_x, min_y, max_y = bbox
                        geom = {
                            "type": "Polygon",
                            "coordinates": [[
                                [min_x, min_y],
                                [max_x, min_y],
                                [max_x, max_y],
                                [min_x, max_y],
                                [min_x, min_y]
                            ]]
                        }

                        if region_data["type"] == "TIDAL":
                            for t in TIDAL_DATUMS:
                                self.fred.add_survey(
                                    geom,
                                    Name=os.path.basename(member).replace(".met", ".gtx"),
                                    ID=zip_bn.split(".")[0],
                                    Agency="NOAA",
                                    DataLink=zip_url,
                                    DataType=t,
                                    #",".join(TIDAL_DATUMS)
                                    #if region_data["region"] == "TIDAL"
                                    #else "geoid",
                                    DataSource="vdatum",
                                )



            except zipfile.BadZipFile:
                logger.warning(f"Corrupted zip file downloaded: {zip_name}")
                continue

            # if bbox:
            #     min_x, max_x, min_y, max_y = bbox
            #     geom = {
            #         "type": "Polygon",
            #         "coordinates": [[
            #             [min_x, min_y],
            #             [max_x, min_y],
            #             [max_x, max_y],
            #             [min_x, max_y],
            #             [min_x, min_y]
            #         ]]
            #     }
            #     props = {
            #         "filename": zip_name,
            #         "url": zip_url,
            #         "last_modified": region_data["date"],
            #         "region": region_data["region"]
            #     }
            #     #features.append({"type": "Feature", "geometry": geom, "properties": props})

            #     self.fred.add_survey(
            #         geom,
            #         Name=zip_name,
            #         ID=region_data["region"],
            #         Agency="NOAA",
            #         DataLink=zip_url,
            #         DataType="tidal"
            #         if region_data["region"] == "TIDAL"
            #         else "geoid",
            #         DataSource="vdatum",
            #     )

        # Save to Fred's RTree / GeoJSON index
        #geojson = {
        #    "type": "FeatureCollection",
        #    "features": features
        #}

        self.fred.save()
        # with open(self.index_file, 'w') as f:
        #     json.dump(geojson, f)

        logger.info(f"Successfully indexed {len(features)} latest VDatum regions.")

    def _parse_bbox(self, text, filename):
        """Extracts bounding box coordinates from either .inf or new .met files."""

        #if filename.endswith('.inf'):
        meta = self._parse_inf(text)
        return(meta['w'], meta['e'], meta['s'], meta['n'])

    def _parse_release_date(self, text, filename):
        d = {}
        for line in text.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                d[k.strip().lower().split(".")[-1]] = v.strip()
        d.get("release", 0)

    # min_x = re.search(r'MIN_X\s*=\s*([-0-9.]+)', text)
    # max_x = re.search(r'MAX_X\s*=\s*([-0-9.]+)', text)
    # min_y = re.search(r'MIN_Y\s*=\s*([-0-9.]+)', text)
    # max_y = re.search(r'MAX_Y\s*=\s*([-0-9.]+)', text)
    # if min_x and max_x and min_y and max_y:
    #     return float(min_x.group(1)), float(max_x.group(1)), float(min_y.group(1)), float(max_y.group(1))

    # elif filename.endswith('.met'):
    #     # NOAA .met files are standard FGDC XML
    #     min_x = re.search(r'<westbc>\s*([-0-9.]+)', text)
    #     max_x = re.search(r'<eastbc>\s*([-0-9.]+)', text)
    #     min_y = re.search(r'<southbc>\s*([-0-9.]+)', text)
    #     max_y = re.search(r'<northbc>\s*([-0-9.]+)', text)
    #     if min_x and max_x and min_y and max_y:
    #         return float(min_x.group(1)), float(max_x.group(1)), float(min_y.group(1)), float(max_y.group(1))

    # return None

    # def _scrape_and_index(self):
    #     """Download zips, parse .inf, update index."""

    #     logger.info("Initializing VDatum Index (This may take a moment)...")

    #     temp_dir = os.path.join(self._outdir, "temp_idx")
    #     if not os.path.exists(temp_dir):
    #         os.makedirs(temp_dir)

    #     vdatum_data = core.Fetch(VDATUM_DATA_URL).fetch_html()
    #     rows = vdatum_data.xpath('//a[contains(@href, ".zip")]/@href')
    #     tidals = [x for x in rows if not x.startswith('vdatum')]

    #     VDATUM_REGIONS.extend(tidals)

    #     for region in VDATUM_REGIONS:
    #         fname = f"{region}.zip"
    #         #if region == "TIDAL":
    #         #    fname = "DEVAemb12_8301.zip"
    #         if "XGEOID" in region or "VERTCON" in region:
    #             fname = f"vdatum_{region}.zip"
    #         else:
    #             fname = region

    #         url = f"{VDATUM_DATA_URL}{fname}"
    #         local_zip = os.path.join(temp_dir, fname)

    #         logger.info(f"Indexing {region}...")
    #         if core.Fetch(url).fetch_file(local_zip) != 0:
    #             continue

    #         try:
    #             import zipfile

    #             with zipfile.ZipFile(local_zip, "r") as z:
    #                 for zf in z.namelist():
    #                     if zf.endswith(".inf"):
    #                         with z.open(zf) as inf:
    #                             content = inf.read().decode("utf-8", errors="ignore")
    #                             meta = self._parse_inf(content)

    #                             if meta:
    #                                 geom = {
    #                                     "type": "Polygon",
    #                                     "coordinates": [
    #                                         [
    #                                             [meta["w"], meta["s"]],
    #                                             [meta["e"], meta["s"]],
    #                                             [meta["e"], meta["n"]],
    #                                             [meta["w"], meta["n"]],
    #                                             [meta["w"], meta["s"]],
    #                                         ]
    #                                     ],
    #                                 }

    #                                 self.fred.add_survey(
    #                                     geom,
    #                                     Name=zf,
    #                                     ID=region,
    #                                     Agency="NOAA",
    #                                     DataLink=url,
    #                                     DataType="tidal"
    #                                     if region == "TIDAL"
    #                                     else "geoid",
    #                                     DataSource="vdatum",
    #                                 )
    #         except Exception as e:
    #             logger.warning(f"Failed to parse {fname}: {e}")

    #         if os.path.exists(local_zip):
    #             os.remove(local_zip)

    #     self.fred.save()
    #     logger.info("VDatum Indexing Complete.")

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
