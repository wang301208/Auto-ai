import pytest

from autogpt.models.command_parameter import CommandParameter, ParameterType
from autogpt.llm.providers.openai import OpenAIFunctionSpec


def test_invalid_command_parameter_type():
    with pytest.raises(ValueError):
        CommandParameter(name="arg", type="invalid", description="", required=False)


def test_invalid_openai_parameter_spec_type():
    with pytest.raises(ValueError):
        OpenAIFunctionSpec.ParameterSpec(
            name="arg", type="invalid", description="", required=False
        )
