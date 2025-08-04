# Testing Command Guide

Auto-GPT provides commands for creating and running tests during development.

## create_test_file

Create a new test file inside the `tests/` directory. The filename must begin with `test_`.

**Parameters**

- `file_path` (required): Path where the test file will be created. Must reside inside `tests/` and start with `test_`.
- `content` (required): Text content to write into the new test file.

## run_tests

Execute tests located at a given path using `pytest`.

**Parameters**

- `path` (required): Path to the tests to run.

