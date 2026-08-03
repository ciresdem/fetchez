# 🗃️ Streams

## Data Streams

## Format Readers

## Reader Profiles

### Extending Streams (Plugins and Extensions)
Fetchez is generic. If you are building a custom tool and want to create your own format readers or profiles, you can register them either in your project or in the `~/.fetchez` configuration directory and they will be discoverable with the `fetchez.registry.ReaderRegistry` and `fetchez.registry.ProfileRegistry`.
xs
In your project, make a directory called 'streams/readers' and/or 'streams/profiles'; add any python readers and YAML profiles to the appropriate directory and register them with Fetchez in your `pyproject.toml`:

**Readers**

```toml
[project.entry-points."fetchez.streams.readers"]
my_project_readers = "my_project.streams.readers"
```

**Profiles**

```toml
	[project.entry-points."fetchez.streams.profiles"]
my_project_presetes = "my_project.streams.profiles"
```
