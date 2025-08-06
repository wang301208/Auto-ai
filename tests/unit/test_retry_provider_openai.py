import pytest
import httpx
from openai import APITimeoutError, APIStatusError, RateLimitError
try:
    from openai import ServiceUnavailableError
except ImportError:  # openai>=1 does not expose this error
    from openai import InternalServerError as ServiceUnavailableError

from autogpt.llm.providers import openai


@pytest.fixture(
    params=[RateLimitError, ServiceUnavailableError, APIStatusError, APITimeoutError]
)
def error(request):
    if request.param == RateLimitError:
        res = httpx.Response(429, request=httpx.Request("GET", "http://example.com"))
        err = request.param("Error", response=res, body={})
        err.http_status = res.status_code
        return err
    if request.param == ServiceUnavailableError:
        res = httpx.Response(503, request=httpx.Request("GET", "http://example.com"))
        err = request.param("Error", response=res, body={})
        err.http_status = res.status_code
        return err
    if request.param == APIStatusError:
        res = httpx.Response(502, request=httpx.Request("GET", "http://example.com"))
        err = request.param("Error", response=res, body={})
        err.http_status = res.status_code
        return err
    if request.param == APITimeoutError:
        return request.param(httpx.Request("GET", "http://example.com"))


def error_factory(error_instance, error_count, retry_count, warn_user=True):
    """Creates errors"""

    class RaisesError:
        def __init__(self):
            self.count = 0

        @openai.retry_api(
            max_retries=retry_count, backoff_base=0.001, warn_user=warn_user
        )
        def __call__(self):
            self.count += 1
            if self.count <= error_count:
                raise error_instance
            return self.count

    return RaisesError()


def test_retry_open_api_no_error(capsys):
    """Tests the retry functionality with no errors expected"""

    @openai.retry_api()
    def f():
        return 1

    result = f()
    assert result == 1

    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == ""


@pytest.mark.parametrize(
    "error_count, retry_count, failure",
    [(2, 10, False), (2, 2, False), (10, 2, True), (3, 2, True), (1, 0, True)],
    ids=["passing", "passing_edge", "failing", "failing_edge", "failing_no_retries"],
)
def test_retry_open_api_passing(capsys, error, error_count, retry_count, failure):
    """Tests the retry with simulated errors [RateLimitError, ServiceUnavailableError, APIStatusError, APITimeoutError], but should ultimately pass"""
    call_count = min(error_count, retry_count) + 1

    raises = error_factory(error, error_count, retry_count)
    if failure:
        with pytest.raises(type(error)):
            raises()
    else:
        result = raises()
        assert result == call_count

    assert raises.count == call_count

    output = capsys.readouterr()

    if error_count and retry_count:
        if isinstance(error, RateLimitError):
            assert "Reached rate limit" in output.out
            assert "Please double check" in output.out
        elif isinstance(error, ServiceUnavailableError):
            assert "The OpenAI API engine is currently overloaded" in output.out
            assert "Please double check" in output.out
        else:
            assert output.out == ""
    else:
        assert output.out == ""


def test_retry_open_api_rate_limit_no_warn(capsys):
    """Tests the retry logic with a rate limit error"""
    error_count = 2
    retry_count = 10

    res = httpx.Response(429, request=httpx.Request("GET", "http://example.com"))
    err = RateLimitError("Error", response=res, body={})
    err.http_status = res.status_code
    raises = error_factory(err, error_count, retry_count, warn_user=False)
    result = raises()
    call_count = min(error_count, retry_count) + 1
    assert result == call_count
    assert raises.count == call_count

    output = capsys.readouterr()

    assert "Reached rate limit" in output.out
    assert "Please double check" not in output.out


def test_retry_open_api_service_unavairable_no_warn(capsys):
    """Tests the retry logic with a service unavairable error"""
    error_count = 2
    retry_count = 10

    res = httpx.Response(503, request=httpx.Request("GET", "http://example.com"))
    err = ServiceUnavailableError("Error", response=res, body={})
    err.http_status = res.status_code
    raises = error_factory(err, error_count, retry_count, warn_user=False)
    result = raises()
    call_count = min(error_count, retry_count) + 1
    assert result == call_count
    assert raises.count == call_count

    output = capsys.readouterr()

    assert "The OpenAI API engine is currently overloaded" in output.out
    assert "Please double check" not in output.out


def test_retry_openapi_other_api_error(capsys):
    """Tests the Retry logic with a non rate limit error such as HTTP500"""
    error_count = 2
    retry_count = 10

    res = httpx.Response(500, request=httpx.Request("GET", "http://example.com"))
    err = APIStatusError("Error", response=res, body={})
    err.http_status = res.status_code
    raises = error_factory(err, error_count, retry_count)

    with pytest.raises(APIStatusError):
        raises()
    call_count = 1
    assert raises.count == call_count

    output = capsys.readouterr()
    assert output.out == ""
