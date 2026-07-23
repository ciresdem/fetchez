# test_spatial.py

import pytest
from fetchez.spatial import parse_region
from fetchez.spatial import Region, HAS_PYPROJ


def test_parse_region_with_epsg():
    """Test parse_region with a region@epsg-code"""

    regions = parse_region("-R1/2/3/4@epsg:4326")
    assert len(regions) == 1
    assert regions[0].srs == "epsg:4326"


@pytest.mark.skipif(not HAS_PYPROJ, reason="Requires pyproj for warping")
def test_region_warp_utm_to_wgs84():
    """Test that a projected region correctly transforms to WGS84 (EPSG:4326)."""

    # Approximate bounding box for Suva, Fiji in UTM Zone 60S (EPSG:32760)
    utm_region = Region(648000, 659000, 7987000, 7998000, srs="EPSG:32760")

    # Warp it in place
    utm_region.warp(dst_srs="EPSG:4326")

    assert utm_region.srs.upper() == "EPSG:4326"
    # Verify the coordinates shifted from meters to geographic degrees
    assert 177.0 < utm_region.xmin < 179.0
    assert -19.0 < utm_region.ymin < -17.0
