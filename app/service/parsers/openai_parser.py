import json
import time

from loguru import logger
from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas.api.api_responses import ParseResponse, SubstitutionOffer, UsageDetails

settings = get_settings()


class OpenAIParser:
    """OpenAI-based implementation of offer parsing."""

    SYSTEM_PROMPT = """
    Z podanego opisu zastępstwa procesowego wyodrębnij następujące informacje:

    - `location`: Typ instytucji – wybierz jedną z: "sąd", "policja", "prokuratura". Ustaw `null`, jeśli nie można określić.
    - `location_full_name`: Pełna nazwa instytucji, np. "Sąd Rejonowy dla Warszawy-Mokotowa", lub `null`.
    - `date`: Lista dat zastępstwa w formacie **RRRR-MM-DD (np. 2025-07-30)**. Jeśli podana jest tylko jedna, zwróć listę z jednym elementem. Jeśli brak – `null`.
    - `time`: Lista godzin zastępstwa w formacie  **HH:MM** (24-godzinny format, np. 13:45). Jeśli brak – `null`.
    - `description`: Krótkie streszczenie charakteru sprawy lub kontekstu. **Usuń email** jeżeli występuje.
    - `legal_roles`: Lista grup docelowych – wybierz spośród: "adwokat", "radca prawny", "aplikant adwokacki", "aplikant radcowski". Jeśli brak informacji – `null`.
    - `email`: Adres e-mail, jeśli występuje w opisie. Jeśli nie ma – `null`.

    Zwróć dane w formacie JSON zgodnym ze schematem.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.API_KEY_OPENAI
        self.model = model or settings.OPENAI_MODEL
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def parse_offer(self, raw_data: str) -> ParseResponse:
        """
        Parse raw offer data using OpenAI.

        Args:
            raw_data: Raw text content to parse

        Returns:
            ParseResponse with structured data or error
        """
        try:
            start_time = time.process_time()

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": raw_data},
                ],
                functions=[
                    {
                        "name": "generate_response",
                        "description": "Wygeneruj dane na podstawie opisu w języku polskim",
                        "parameters": SubstitutionOffer.model_json_schema(),
                    }
                ],
                function_call={"name": "generate_response"},
                temperature=1,
            )

            function_args = response.choices[0].message.function_call.arguments
            args_dict = json.loads(function_args)
            validated = SubstitutionOffer.model_validate(args_dict)

            elapsed_time = time.process_time() - start_time
            usage_info = UsageDetails(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                elapsed_time=elapsed_time
            )

            logger.info(
                f"OpenAI parsing - Tokens: prompt={usage_info.prompt_tokens}, "
                f"completion={usage_info.completion_tokens}, "
                f"total={usage_info.total_tokens}, "
                f"time={usage_info.elapsed_time:.3f}s"
            )

            return ParseResponse(success=True, data=validated, usage=usage_info)

        except Exception as e:
            logger.error(f"Error in OpenAI parsing: {e}")
            return ParseResponse(success=False, error=str(e), data=None)
