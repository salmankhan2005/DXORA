"""Tests for input validation rules according to task specification:
- Message length <= 200 characters
- Exactly one CTA link in message
- Valid URL format and scheme
- Internal platform selection (no external selection allowed)
- Appropriate validation error responses (HTTP 422)
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas import PostingRequest

client = TestClient(app)


class TestInputValidationUnit:
    """Unit tests on the Pydantic PostingRequest model directly."""

    def test_valid_message_with_single_cta(self):
        msg = "Check out our latest business platform and grow your online visibility. https://example.com"
        req = PostingRequest(message=msg)
        assert req.message == msg
        assert req.cta_url == "https://example.com"

    def test_valid_message_with_trailing_period(self):
        msg = "Check out our platform at https://example.com/growth."
        req = PostingRequest(message=msg)
        assert req.cta_url == "https://example.com/growth"

    def test_valid_message_with_query_params_and_fragment(self):
        msg = "Visit our site https://example.com/features?source=twitter&ref=123#overview today!"
        req = PostingRequest(message=msg)
        assert req.cta_url == "https://example.com/features?source=twitter&ref=123#overview"

    def test_valid_message_with_www_prefix(self):
        msg = "Explore the new update at www.dxora.com now."
        req = PostingRequest(message=msg)
        assert req.cta_url == "https://www.dxora.com"

    def test_message_exceeding_200_chars_raises_error(self):
        long_message = "A" * 180 + " https://example.com"  # 180 + 20 = 200 (ok)
        assert len(long_message) == 200
        req = PostingRequest(message=long_message)
        assert req.message == long_message

        too_long = "A" * 181 + " https://example.com"  # 201 chars
        assert len(too_long) == 201
        with pytest.raises(ValidationError) as exc_info:
            PostingRequest(message=too_long)
        assert "exceeds the maximum limit of 200 characters" in str(exc_info.value)

    def test_message_without_cta_link_raises_error(self):
        msg = "Check out our latest business platform and grow your online visibility."
        with pytest.raises(ValidationError) as exc_info:
            PostingRequest(message=msg)
        assert "Message must contain exactly one CTA link, but none was found" in str(exc_info.value)

    def test_message_with_multiple_cta_links_raises_error(self):
        msg = "Check out https://first.com and also https://second.com for more info."
        with pytest.raises(ValidationError) as exc_info:
            PostingRequest(message=msg)
        assert "Message must contain exactly one CTA link, but found 2 links" in str(exc_info.value)

    def test_message_with_invalid_protocol_raises_error(self):
        msg = "Download files from ftp://files.example.com/data today."
        with pytest.raises(ValidationError) as exc_info:
            PostingRequest(message=msg)
        assert "must use HTTP or HTTPS protocol" in str(exc_info.value)

    def test_message_with_invalid_domain_raises_error(self):
        msg = "Check out https://.com/test for updates."
        with pytest.raises(ValidationError) as exc_info:
            PostingRequest(message=msg)
        assert "invalid domain or hostname" in str(exc_info.value)

    def test_empty_message_raises_error(self):
        with pytest.raises(ValidationError):
            PostingRequest(message="")
        with pytest.raises(ValidationError):
            PostingRequest(message="    ")


class TestInputValidationApi:
    """API endpoint tests checking HTTP status codes and response bodies."""

    def test_api_valid_request(self):
        payload = {
            "message": "Check out our latest business platform. https://example.com"
        }
        response = client.post("/posting", json=payload)
        # Even with unconfigured credentials, the input validation succeeds (HTTP 200)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_api_rejection_when_message_exceeds_200_chars(self):
        payload = {"message": "X" * 185 + " https://example.com"}
        response = client.post("/posting", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert any("200 characters" in d["message"] for d in data["details"])

    def test_api_rejection_when_no_link_present(self):
        payload = {"message": "Here is an announcement with no link at all."}
        response = client.post("/posting", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert any("none was found" in d["message"] for d in data["details"])

    def test_api_rejection_when_multiple_links_present(self):
        payload = {
            "message": "Visit https://dxora.com and https://google.com now!"
        }
        response = client.post("/posting", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert any("found 2 links" in d["message"] for d in data["details"])

    def test_api_rejection_on_extra_fields(self):
        # Platform selection must be handled internally, external platform field forbidden
        payload = {
            "message": "Visit https://dxora.com",
            "platforms": ["twitter", "telegram"],
        }
        response = client.post("/posting", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert any("Extra inputs are not permitted" in d["message"] for d in data["details"])
