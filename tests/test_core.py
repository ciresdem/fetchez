from fetchez.core import FetchModule


def test_fetchmodule_default_region():
    """If a module is initialized without a region, it should default to the whole globe."""

    mod = FetchModule(name="test_mod")
    assert mod.region == (-180, 180, -90, 90)


def test_fetchmodule_add_results():
    """Test that the helper method correctly populates the results list."""

    mod = FetchModule(name="test_mod")
    assert len(mod.results) == 0

    mod.add_entry_to_results(
        url="http://example.com/data.tif", dst_fn="data.tif", data_type="raster"
    )

    assert len(mod.results) == 1
    assert mod.results[0]["url"] == "http://example.com/data.tif"
    assert mod.results[0]["data_type"] == "raster"
