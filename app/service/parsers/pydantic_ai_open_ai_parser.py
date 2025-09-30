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
    """pydantic-ai parser using the OpenAI Responses API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.API_KEY_OPENAI
        self.model = settings.OPENAI_MODEL
        self.system_prompt = settings.SYSTEM_PROMPT

        responses_model = OpenAIResponsesModel(self.model, provider=OpenAIProvider(api_key=self.api_key))

        self.agent = Agent[SubstitutionOffer](
            model=responses_model,
            system_prompt=self.system_prompt,
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
