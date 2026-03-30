#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.modules.bluetopo
~~~~~~~~~~~~~~~~~~~~~~~~

Fetch NOAA BlueTopo bathymetric data directly from AWS S3.

BlueTopo is a compilation of the nation's best available bathymetric data,
created as part of the Office of Coast Survey's National Bathymetric Source project.

:copyright: (c) 2010 - 2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import logging
from typing import Optional

try:
    import boto3
    from botocore import UNSIGNED
    from botocore.client import Config
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False

try:
    import fiona
    HAS_FIONA = True
except ImportError:
    HAS_FIONA = False

from fetchez import core
from fetchez.modules import FetchModule
from fetchez import cli

logger = logging.getLogger(__name__)

BLUETOPO_BUCKET = "noaa-ocs-nationalbathymetry-pds"
BLUETOPO_PREFIX = "BlueTopo"

@cli.cli_opts(
    help_text="NOAA BlueTopo Bathymetry (AWS S3)",
    want_interpolation="Accept interpolated data (Downstream processing flag)",
    unc_weights="Use uncertainty weights (Downstream processing flag)",
    keep_index="Keep the downloaded tile index file after running",
)
class BlueTopo(FetchModule):
    name = "bluetopo"
    meta_category = "Bathymetry"
    meta_desc = "NOAA BlueTopo (National Bathymetric Source) via AWS S3"
    meta_agency = "NOAA OCS"
    meta_tags = ["bathymetry", "noaa", "bluetopo", "nbs", "ocean", "elevation"]
    meta_region = "USA"
    meta_resolution = "Variable"
    meta_license = "Public Domain"
    meta_urls = {"home": "https://nauticalcharts.noaa.gov/data/bluetopo.html"}

    def __init__(
        self,
        want_interpolation: bool = False,
        unc_weights: bool = False,
        keep_index: bool = False,
        **kwargs,
    ):
        super().__init__(name="bluetopo", **kwargs)
        self.want_interpolation = want_interpolation
        self.unc_weights = unc_weights
        self.keep_index = keep_index

        self._bluetopo_index_url = None
        self._bluetopo_index_fn = None

    def _get_s3_client(self):
        """Return an anonymous S3 client."""
        return boto3.client("s3", config=Config(signature_version=UNSIGNED))

    def _get_index_url(self, s3_client) -> Optional[str]:
        """Dynamically find the Tile Scheme index file URL from S3."""
        try:
            r = s3_client.list_objects(
                Bucket=BLUETOPO_BUCKET,
                Prefix=f"{BLUETOPO_PREFIX}/_BlueTopo_Tile_Scheme",
            )
            if "Contents" in r and len(r["Contents"]) > 0:
                key = r["Contents"][0]["Key"]
                return f"https://{BLUETOPO_BUCKET}.s3.amazonaws.com/{key}"
        except Exception as e:
            logger.error(f"Error finding BlueTopo index on S3: {e}")
        return None

    def run(self):
        """Run the BlueTopo fetch module."""
        if not HAS_BOTO:
            logger.error('This module requires "boto3". Please install it to proceed.')
            return self

        if not HAS_FIONA:
            logger.error('This module requires "fiona" to parse the spatial index. Please install it.')
            return self

        if self.region is None:
            return self

        s3 = self._get_s3_client()

        if self._bluetopo_index_url is None:
            logger.info("Locating BlueTopo Tile Scheme on S3...")
            self._bluetopo_index_url = self._get_index_url(s3)

        if not self._bluetopo_index_url:
            logger.error("Could not locate BlueTopo tile index.")
            return self

        self._bluetopo_index_fn = os.path.join(self._outdir, os.path.basename(self._bluetopo_index_url))

        try:
            if not os.path.exists(self._bluetopo_index_fn):
                logger.info(f"Downloading index: {os.path.basename(self._bluetopo_index_fn)}...")
                status = core.Fetch(self._bluetopo_index_url).fetch_file(self._bluetopo_index_fn)
                if status != 0:
                    raise IOError("Failed to download BlueTopo index.")

            logger.info("Querying tile index with Fiona...")

            w, e, s, n = self.region
            bbox = (w, s, e, n)

            feature_count = 0

            with fiona.open(self._bluetopo_index_fn) as src:
                intersecting_features = list(src.filter(bbox=bbox))
                feature_count = len(intersecting_features)

                if feature_count == 0:
                    logger.info("No BlueTopo tiles found in this region.")
                    return self

                logger.info(f"Found {feature_count} intersecting tiles.")

                for feature in intersecting_features:
                    tile_name = feature['properties'].get("tile")
                    if not tile_name:
                        continue

                    try:
                        r = s3.list_objects(
                            Bucket=BLUETOPO_BUCKET, Prefix=f"{BLUETOPO_PREFIX}/{tile_name}"
                        )
                        if "Contents" in r:
                            for obj in r["Contents"]:
                                key = obj["Key"]
                                if key.endswith(".tiff"):
                                    data_link = f"https://{BLUETOPO_BUCKET}.s3.amazonaws.com/{key}"
                                    self.add_entry_to_results(
                                        url=data_link,
                                        dst_fn=os.path.basename(key),
                                        data_type="bluetopo_tiff",
                                        agency="NOAA OCS",
                                        title=tile_name,
                                        license="Public Domain",
                                    )
                    except Exception as e:
                        logger.warning(f"Failed to resolve file for tile {tile_name}: {e}")

        except Exception as e:
            logger.error(f"BlueTopo Run Error: {e}")

        finally:
            if not self.keep_index and self._bluetopo_index_fn:
                if os.path.exists(self._bluetopo_index_fn):
                    try:
                        os.remove(self._bluetopo_index_fn)
                    except OSError:
                        pass

        return self
