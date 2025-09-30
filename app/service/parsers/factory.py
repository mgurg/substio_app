"""
app/services/parsers/factory.py

Factory for getting AI parser implementations.
"""


from app.service.parsers.base import AIParser
from app.service.parsers.openai_parser import OpenAIParser
from app.service.parsers.pydantic_ai_open_ai_parser import PydanticAIOpenAIParser


def get_ai_parser() -> AIParser:
    """
    Factory function to get the current AI parser implementation.

    This makes it easy to swap implementations by changing just this function.

    Returns:
        AIParser implementation instance
    """
    return OpenAIParser()
    # return PydanticAIOpenAIParser()