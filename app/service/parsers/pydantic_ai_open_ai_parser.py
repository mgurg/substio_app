import json
import time
from typing import Literal

from loguru import logger
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import get_settings
from app.schemas.api.api_responses import ParseResponse, SubstitutionOffer, UsageDetails

settings = get_settings()

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


class PydanticAIOpenAIParser:
    """pydantic-ai parser using the OpenAI Responses API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.API_KEY_OPENAI
        self.model = settings.OPENAI_MODEL

        responses_model = OpenAIResponsesModel(self.model, provider=OpenAIProvider(api_key=self.api_key))

        self.agent = Agent[SubstitutionOffer](
            model=responses_model,
            system_prompt=SYSTEM_PROMPT,
            output_type=SubstitutionOffer,
        )

    async def parse_offer(self, raw_data: str) -> ParseResponse:
        try:
            start_time = time.process_time()

            result = await self.agent.run(raw_data)
            output_data = result.output

            if isinstance(output_data, SubstitutionOffer):
                validated = output_data
            elif isinstance(output_data, str):
                logger.warning('Received: JSON string, create the Pydantic V2 model instance from the dictionary')
                data_dict = json.loads(output_data)
                validated = SubstitutionOffer.model_validate(data_dict)
            else:
                logger.error('Unexpected output type: {}'.format(type(output_data)))
                validated = output_data

            elapsed_time = time.process_time() - start_time
            usage_info = None
            if result.usage():
                usage = result.usage()
                usage_info = UsageDetails(
                    prompt_tokens=usage.input_tokens,
                    completion_tokens=usage.output_tokens,
                    total_tokens=usage.total_tokens,
                    elapsed_time=elapsed_time,
                )
                logger.info(
                    f"Responses API parsing - Tokens: "
                    f"input={usage_info.prompt_tokens}, "
                    f"output={usage_info.completion_tokens}, "
                    f"total={usage_info.total_tokens}, "
                    f"time={usage_info.elapsed_time:.3f}s"
                )

            return ParseResponse(success=True, data=validated, usage=usage_info)

        except Exception as e:
            logger.error(f"Error in Responses API parsing: {e}")
            return ParseResponse(success=False, error=str(e), data=None)
