from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.ai.parsers.pydantic_ai_open_ai_parser import PydanticAIOpenAIParser
from app.schemas.domain.ai import SubstitutionOffer


@pytest.fixture
def parser():
    with patch("app.infrastructure.ai.parsers.pydantic_ai_open_ai_parser.get_settings") as mock_settings:
        mock_settings.return_value.API_KEY_OPENAI = "test-key"
        mock_settings.return_value.OPENAI_MODEL = "gpt-4o"
        mock_settings.return_value.SYSTEM_PROMPT = "Test prompt"
        return PydanticAIOpenAIParser(api_key="test-key")


@pytest.mark.asyncio
async def test_parse_offer_success(parser):
    mock_result = MagicMock()
    mock_output = SubstitutionOffer(
        offer_uid="123",
        author="Test Author",
        author_uid="author123",
        place_name="Test Place",
        city_name="Test City",
        email="test@example.com",
        url="http://example.com",
        date="2024-01-01",
        hour="10:00",
        price=100.0,
        description="Test Description",
        invoice=True,
        legal_roles=["ADW"]
    )
    mock_result.output = mock_output

    mock_usage = MagicMock()
    mock_usage.input_tokens = 10
    mock_usage.output_tokens = 20
    mock_usage.total_tokens = 30
    mock_result.usage.return_value = mock_usage

    parser.agent.run = AsyncMock(return_value=mock_result)

    response = await parser.parse_offer("raw data")

    assert response.success is True
    assert response.data == mock_output
    assert response.usage.total_tokens == 30
    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 20


@pytest.mark.asyncio
async def test_parse_offer_failure(parser):
    parser.agent.run = AsyncMock(side_effect=Exception("AI error"))

    response = await parser.parse_offer("raw data")

    assert response.success is False
    assert "AI error" in response.error


def test_validate_output_str(parser):
    output_str = '{"offer_uid": "123", "author": "Test Author"}'
    # SubstitutionOffer.model_validate will be called on the dict
    with patch.object(SubstitutionOffer, "model_validate") as mock_validate:
        parser._validate_output(output_str)
        mock_validate.assert_called_once_with({"offer_uid": "123", "author": "Test Author"})


def test_validate_output_dict(parser):
    output_dict = {"offer_uid": "123", "author": "Test Author"}
    with patch.object(SubstitutionOffer, "model_validate") as mock_validate:
        parser._validate_output(output_dict)
        mock_validate.assert_called_once_with(output_dict)


def test_validate_output_unsupported(parser):
    with pytest.raises(TypeError):
        parser._validate_output(123)


def test_extract_usage_none(parser):
    mock_result = MagicMock()
    mock_result.usage.return_value = None
    assert parser._extract_usage(mock_result, 0.0) is None
