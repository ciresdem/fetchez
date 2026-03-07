# 🐄 Plugins & Extensions

Need to fetch data from a specialized local server? Or maybe run a custom script immediately after every download? You don't need to fork the repo!

There are two ways to extend `fetchez`: **Local Plugins** (for quick, personal scripts) and **Full Extensions** (for distributable Python packages).

##  Local Plugins (Quick & Easy)

Local plugins are standalone Python scripts that you drop into your local `fetchez` configuration folders. `fetchez` automatically scans these folders at runtime and registers any valid classes it finds.

### Data Modules (`~/.fetchez/plugins/`)
Data Modules tell `fetchez` how to talk to a specific API or data source.

To build one, create a Python script containing a class that inherits from `fetchez.core.FetchModule`.

**Example:**

Create `~/.fetchez/plugins/my_server.py`:
```python
from fetchez.core import FetchModule

class MyCustomServer(FetchModule):
    name = "my_server"
	meta_desc = "Fetches data from my local company server."

	def __init__(self, **kwargs):
		super().__init__(name="my_server", **kwargs)

    def run(self):
        # Your custom logic to query an API and yield URLs goes here.
        self.results.append({
            "url": "http://myserver.local/data.zip",
            "dst_fn": "data.zip"
        })
```

You can now run this instantly from the CLI: `fetchez my_server`

### Processing Hooks (~/.fetchez/hooks/)
Hooks intercept data before, during, or after the fetch process.

To build one, create a class that inherits from `fetchez.hooks.FetchHook`.

**Example:**

Create ~/.fetchez/hooks/zulip_notify.py:
```python
import logging
from fetchez.hooks import FetchHook

logger = logging.getLogger(__name__)

class ZulipNotifier(FetchHook):
    name = "zulip_notify"
    stage = "post"
    category = "comms"

    def __init__(self, chan="fetchez", **kwargs):
        super().__init__(**kwargs)
        self.chan = chan

    def run(self, entries):
        import zulip
        client = zulip.Client()
        mods = set()
        for mod, entry in entries:
            mods.add(mod)

        params = {
            "type": "stream",
            "to": self.chan,
            "topic": "Auto-Fetchez",
            "content": f"Downloaded {len(entries)} files from {len(mods)} modules."
        }
        result = client.send_message(params)
        logger.info(f"Zulip notification result: {result.get('result')}!")
        return entries
```

You can now use this in your presets, recipes and cli switches: `fetchez copernicus --hook zulip_notify`
