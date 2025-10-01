import json
import time

from loguru import logger
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import get_settings
from app.schemas.api.api_responses import ParseResponse, SubstitutionOffer, UsageDetails

settings = get_settings()


class PydanticAIOpenAIParser:
    """Parser using the pydantic-ai library with OpenAI backend."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.API_KEY_OPENAI
        self.model_name = settings.OPENAI_MODEL
        self.system_prompt = settings.SYSTEM_PROMPT

        self.agent = self._initialize_agent()

    def _initialize_agent(self) -> Agent[SubstitutionOffer]:
        model = OpenAIResponsesModel(model_name=self.model_name, provider=OpenAIProvider(api_key=self.api_key))

        return Agent[SubstitutionOffer](
            model=model,
            system_prompt=self.system_prompt,
            output_type=SubstitutionOffer,
        )

    async def parse_offer(self, raw_data: str) -> ParseResponse:
        start_time = time.process_time()

        try:
            result = await self.agent.run(raw_data)
            validated = self._validate_output(result.output)

            usage_info = self._extract_usage(result, start_time)

            return ParseResponse(success=True, data=validated, usage=usage_info)

        except Exception as e:
            logger.exception("Error in Responses API parsing")
            return ParseResponse(success=False, error=str(e), data=None)

    def _validate_output(self, output: SubstitutionOffer | str | dict) -> SubstitutionOffer:
        if isinstance(output, SubstitutionOffer):
            return output

        if isinstance(output, str):
            logger.warning("Received JSON string, attempting to parse")
            output = json.loads(output)

        if isinstance(output, dict):
            return SubstitutionOffer.model_validate(output)

        raise TypeError(f"Unsupported output type: {type(output)}")

    def _extract_usage(self, result, start_time: float) -> UsageDetails | None:
        usage = result.usage()
        if not usage:
            return None

        elapsed_time = time.process_time() - start_time
        usage_info = UsageDetails(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            elapsed_time=elapsed_time,
        )

        logger.info(
            f"Responses API parsing - Tokens: input={usage_info.input_tokens}, "
            f"output={usage_info.output_tokens}, total={usage_info.total_tokens}, "
            f"time={usage_info.elapsed_time:.3f}s"
        )

        return usage_info
