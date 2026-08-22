"""
Response Formatter and Structured Output Schema Engine for the KMRL LLM Layer.

Generates strict validation parameters and parameter definitions to force 
downstream language models to output structurally sound JSON data frames.
"""

import logging
from typing import Any, Dict, Type
from pydantic import BaseModel

logger = logging.getLogger("document_intelligence.llm.response_formatter")


class LLMResponseFormatter:
    """
    Utility suite compiling Pydantic model configurations into structural API targets.
    """

    @staticmethod
    def get_structured_output_config(pydantic_model: Type[BaseModel]) -> Dict[str, Any]:
        """
        Translates a target validation model class into an OpenAI-compatible 
        Strict Structured Output dictionary specification.

        Args:
            pydantic_model: The Pydantic model class defining the targeted schema.

        Returns:
            A parameter configuration dictionary suitable for injection into 
            the LLMClient's chat completions payload wrapper.
        """
        if not issubclass(pydantic_model, BaseModel):
            logger.error("Provided schema object does not inherit from Pydantic BaseModel.")
            raise TypeError("Target model configuration must be a valid Pydantic BaseModel class.")

        model_name = pydantic_model.__name__
        logger.debug(f"Compiling strict JSON validation frame for model class: {model_name}")

        # Extract standard structural json schema configuration out of Pydantic metadata tracking trees
        raw_schema = pydantic_model.model_json_schema()

        # Build the formal payload configuration wrapper forcing strict schema compliance
        return {
            "type": "json_schema",
            "json_schema": {
                "name": f"{model_name}_schema",
                "strict": True,
                "schema": raw_schema
            }
        }

    @staticmethod
    def get_basic_json_mode_config() -> Dict[str, Any]:
        """
        Generates a standard configuration blueprint enabling loose JSON mode execution.
        Use this when strict structural constraints aren't completely necessary, 
        but valid structural brackets are required.
        """
        logger.debug("Compiling standard JSON mode target parameter override.")
        return {"type": "json_object"}