import json
import time

from loguru import logger
from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas.api.api_responses import ParseResponse, SubstitutionOffer, UsageDetails

settings = get_settings()


class OpenAIParser:
    """OpenAI-based implementation of offer parsing."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.API_KEY_OPENAI
        self.model = settings.OPENAI_MODEL
        self.system_prompt = settings.SYSTEM_PROMPT
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
                    {"role": "system", "content": self.system_prompt},
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
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                elapsed_time=elapsed_time
            )

            logger.info(
                f"OpenAI parsing - Tokens: prompt={usage_info.input_tokens}, "
                f"completion={usage_info.output_tokens}, "
                f"total={usage_info.total_tokens}, "
                f"time={usage_info.elapsed_time:.3f}s"
            )

            return ParseResponse(success=True, data=validated, usage=usage_info)

        except Exception as e:
            logger.error(f"Error in OpenAI parsing: {e}")
            return ParseResponse(success=False, error=str(e), data=None)
