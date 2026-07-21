# 🐄 Developing User Plugins

One of the most powerful features of `fetchez` is its plugin architecture. You can write your own modules to fetch data from custom sources and use them immediately with the full power of the `fetchez` CLI (smart regions, threading, retries, etc.).

## How it Works
1.  `fetchez` scans `~/.fetchez/plugins/` at runtime.
2.  It loads any `.py` file it finds.
3.  It registers any class that inherits from `fetchez.modules.FetchModule`.

## Example Plugin
Create a file named `~/.fetchez/plugins/usgs_checkpoints.py`:

```python
from fetchez import core, cli
from fetchez.modules import FetchModule

checkpoints_base_url = 'https://www.sciencebase.gov/catalog/file/get/'
checkpoints_link = '67075e6bd34e969edc59c3e7?f=__disk__80%2F12%2F9e%2F80129e86d18461ed921b288f13e08c62e8590ffb'

@cli.cli_opts(help_text="USGS Elevation Checkpoints")
class CheckPoints3DEP(FetchModule):
    name = "3dep_cp"
    meta_category = "Reference"
    meta_desc = "USGS 3DEP Elevation Validation Checkpoints"
    meta_agency = "USGS"
    meta_tags = ["usgs", "3dep", "checkpoints", "validation", "accuracy", "control-points"]
    meta_region = "USA"
    meta_resolution = "Point Data"
    meta_license = "Public Domain"
    meta_urls = {
        "home": "https://www.usgs.gov/3d-elevation-program",
        "source": "https://www.sciencebase.gov/catalog/item/67075e6bd34e969edc59c3e7",
    }

    def __init__(self, **kwargs):
    	# `name` here becomes the name of fetchez module in the cli
        super().__init__(name='my_checkpoints', **kwargs)

    def run(self):
        # Use self.wgs_region if spatial filtering is needed (EPSG:4326)
        if self.wgs_region:
             print(f"Searching in geographic bounds: {self.wgs_region}"

	    # Use self.region if you need to do local spatial math in the user's native CRS
        if self.region:
             print(f"Native project bounds: {self.region}")

    	# This is where you'd normally hit an API, or parse some
        # data, etc.

        self.add_entry_to_results(
            url=f'{checkpoints_base_url}{checkpoints_link}',
            dst_fn='USGS_CheckPoints.zip',
            data_type='checkpoints',
        )
```

### Testing Your Plugin
Once you save the file, simply run:

```bash

# Check if it loaded
fetchez --search my_checkpoints

# or see all plugins
fetchez --search plugin

# Run it
fetchez my_checkpoints
```
