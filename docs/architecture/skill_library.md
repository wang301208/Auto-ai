# Skill Library

## Directory Layout

Auto-GPT stores reusable skills in the `skill_library/` directory. Each skill is
kept in a dedicated folder named `<skill>_<version>` containing:

- `main.py` – executable entry point for the skill
- `test_main.py` – placeholder for unit tests
- `requirements.txt` – optional dependencies
- `skill.json` – metadata describing the skill

## Example

A minimal sample skill `hello_world_1.0` is available in the repository's
`skill_library/` directory. Its `run` function simply returns the string
`"Hello, world!"` and `skill.json` shows the required metadata layout. Run its
unit test with:

```bash
pytest skill_library/hello_world_1.0/test_main.py
```

Use this folder as a template when creating your own skills.

## Metadata Schema

`skill.json` provides structured information used when loading and searching
skills:

```json
{
  "skill_name": "web_search",
  "version": "1.0",
  "description": "Search the web for information",
  "tags": ["search", "web"],
  "parameters": {"query": "The query string"}
}
```

`tags` categorise the skill and `parameters` document the expected inputs.

## Semantic Search Workflow

`SkillLibrary` indexes skills for discovery via semantic search:

1. On load, each skill's `description` and `tags` are concatenated and embedded
   using the configured embedding model.
2. The resulting vectors are stored in a pluggable `VectorDBProvider`.
3. Queries are embedded the same way and compared against the stored vectors.
4. The vector database returns the most similar skills, enabling lookup by
description or tag rather than exact file names.

This workflow lets agents locate relevant skills using natural language rather
than hard‑coded identifiers.
