# Testing Command Guide

Auto-GPT provides commands for creating and running tests during development.

## Installation

Install the test dependencies:

```bash
pip install -e .[test]
# or
pip install pytest
```

## Usage

Run tests with either the built-in command or directly with pytest:

```bash
agpt run_tests <path>
# or
pytest
```

## create_test_file

Create a new test file inside the `tests/` directory. The filename must begin with `test_`.

**Parameters**

- `file_path` (required): Path where the test file will be created. Must reside inside `tests/` and start with `test_`.
- `content` (required): Text content to write into the new test file.

## run_tests

Execute tests located at a given path using `pytest`.

**Parameters**

- `path` (required): Path to the tests to run.

