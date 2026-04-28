from fetchez.spatial import parse_region


def test_parse_region_with_epsg():
    """Test parse_region with a region@epsg-code"""

    regions = parse_region("-R1/2/3/4@epsg:4326")
    assert len(regions) == 1
    assert regions[0].srs == "epsg:4326"
