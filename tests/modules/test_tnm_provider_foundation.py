import pytest

from fetchez import spatial
from fetchez import utils
from fetchez.modules import tnm


SAMPLE_REGION = spatial.Region(-118.65, -118.60, 34.05, 34.10, srs="EPSG:4326")


class FakeResponse:
    status_code = 200
    text = "{}"

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeFetch:
    payload = {"total": 0, "items": []}
    params_seen = []

    def __init__(self, _url):
        pass

    def fetch_req(self, params=None):
        self.__class__.params_seen.append(dict(params or {}))
        return FakeResponse(self.__class__.payload)


@pytest.fixture(autouse=True)
def reset_fake_fetch(monkeypatch):
    FakeFetch.payload = {"total": 0, "items": []}
    FakeFetch.params_seen = []
    monkeypatch.setattr(tnm.core, "Fetch", FakeFetch)


def _item(title, url, publication_date, source_id):
    return {
        "title": title,
        "sourceId": source_id,
        "metaUrl": f"https://example.test/sciencebase/{source_id}",
        "vendorMetaUrl": (
            "https://prd-tnm.s3.amazonaws.com/index.html?prefix="
            "StagedProducts/Elevation/metadata/waf/"
            f"USGS_1M_tile_{source_id}_meta.xml"
        ),
        "publicationDate": publication_date,
        "lastUpdated": f"{publication_date}T12:00:00Z",
        "sizeInBytes": 1234,
        "format": "GeoTIFF",
        "downloadURL": url,
        "boundingBox": {
            "minX": -118.65,
            "maxX": -118.60,
            "minY": 34.05,
            "maxY": 34.10,
        },
    }


@pytest.mark.parametrize(
    ("selector", "expected"),
    [
        ("1m", tnm.DATASET_CODES[2]),
        ("1_9as", tnm.DATASET_CODES[4]),
        ("1_3as", tnm.DATASET_CODES[3]),
        ("1_as", tnm.DATASET_CODES[1]),
        ("2", tnm.DATASET_CODES[2]),
        ("8/2", f"{tnm.DATASET_CODES[8]},{tnm.DATASET_CODES[2]}"),
    ],
)
def test_dataset_aliases_keep_existing_numeric_syntax(selector, expected):
    mod = tnm.TheNationalMap(
        src_region=SAMPLE_REGION,
        datasets=selector,
        use_cache=False,
    )
    mod.run()

    assert FakeFetch.params_seen[0]["datasets"] == expected


def test_invalid_dataset_selector_keeps_existing_default():
    mod = tnm.TheNationalMap(
        src_region=SAMPLE_REGION,
        datasets="2/not-a-dataset",
        use_cache=False,
    )
    mod.run()

    assert FakeFetch.params_seen[0]["datasets"] == tnm.DATASET_CODES[1]


def test_source_string_syntax_supports_dedupe_false():
    parsed = utils.parse_source_string("tnm:datasets=1m,dedupe=false")

    assert parsed["module"] == "tnm"
    assert parsed["args"]["datasets"] == "1m"
    assert parsed["args"]["dedupe"] is False


def test_default_dedupe_keeps_existing_newest_product_behavior():
    FakeFetch.payload = {
        "total": 2,
        "items": [
            _item(
                "USGS 1 Meter older",
                "https://example.test/Projects/"
                "CA_2025LosAngelesPostWildfire_C25/older/USGS_1M_tile.tif",
                "2024-01-01",
                "older",
            ),
            _item(
                "USGS 1 Meter newer",
                "https://example.test/Projects/"
                "CA_2025LosAngelesPostWildfire_C25/newer/USGS_1M_tile.tif",
                "2025-02-01",
                "newer",
            ),
        ],
    }

    mod = tnm.TheNationalMap(
        src_region=SAMPLE_REGION,
        datasets="1m",
        use_cache=False,
    )
    mod.run()

    assert len(mod.results) == 1
    assert mod.results[0]["dst_fn"].endswith("/USGS_1M_tile.tif")
    assert mod.results[0]["tnm_source_id"] == "newer"
    assert mod.results[0]["tnm_project"] == "CA_2025LosAngelesPostWildfire_C25"
    assert mod.results[0]["tnm_publication_date"] == "2025-02-01"
    assert mod.results[0]["tnm_last_updated"] == "2025-02-01T12:00:00Z"
    assert mod.results[0]["tnm_meta_url"].endswith("/newer")
    assert "/metadata/waf/" in mod.results[0]["tnm_vendor_meta_url"]


def test_dedupe_false_retains_overlapping_products_without_name_collision():
    FakeFetch.payload = {
        "total": 2,
        "items": [
            _item(
                "USGS 1 Meter older",
                "https://example.test/Projects/CA_2024_Test/older/USGS_1M_tile.tif",
                "2024-01-01",
                "older",
            ),
            _item(
                "USGS 1 Meter newer",
                "https://example.test/Projects/"
                "CA_2025LosAngelesPostWildfire_C25/newer/USGS_1M_tile.tif",
                "2025-02-01",
                "newer",
            ),
        ],
    }

    mod = tnm.TheNationalMap(
        src_region=SAMPLE_REGION,
        datasets="1m",
        dedupe=False,
        use_cache=False,
    )
    mod.run()

    assert len(mod.results) == 2
    assert len({entry["dst_fn"] for entry in mod.results}) == 2
    assert all(entry["dst_fn"].endswith("/USGS_1M_tile.tif") for entry in mod.results)
    assert [entry["tnm_source_id"] for entry in mod.results] == ["older", "newer"]
    assert [entry["tnm_project"] for entry in mod.results] == [
        "CA_2024_Test",
        "CA_2025LosAngelesPostWildfire_C25",
    ]
