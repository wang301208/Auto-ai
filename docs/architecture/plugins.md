# Plugins

Auto-GPT plugins are described by JSON metadata files. These files declare
what a plugin does and where its code can be found. Each metadata file must
include the following fields:

- **name** – human readable plugin name.
- **description** – short explanation of the plugin's purpose.
- **instructions** – high level guidance on how the plugin should behave.
- **developer** – individual or organisation that implemented the plugin.
- **policy_maker** – party responsible for setting usage policies for the plugin.
- **underlying_library** – object describing the dependency the plugin wraps;
  requires `name`, `version`, `repo_url` and `local_source_path` (which must
  point to an existing path on the local filesystem).
- **source_code_access_policy** – one of `ALLOWED_FOR_READ_ONLY` or
  `RESTRICTED`, describing whether the plugin's source may be inspected.

Missing any of these fields will cause the plugin loader to raise a
`PluginMetaValidationError` when parsing the metadata file.

In addition to validating required fields, the loader verifies that the
`local_source_path` referenced in the `underlying_library` actually exists.
