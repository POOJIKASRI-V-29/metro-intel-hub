"""Risk Assessment Agent for the KMRL platform.

Scope: Interfaces with the LLM to analyze text for potential safety 
hazards, operational risks, and compliance issues. It extracts a list 
of discrete risks, assigning a severity level and mitigation strategy 
(if mentioned) to each.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Any, List

from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RiskItem:
    """Represents a single identified risk or hazard."""
    description: str
    severity: str  # e.g., "LOW", "MEDIUM", "HIGH", "CRITICAL"
    mitigation_mentioned: str | None = None


@dataclass
class RiskAssessmentResult:
    """Structured output containing all risks identified in the text."""
    identified_risks: List[RiskItem] = field(default_factory=list)
    overall_risk_level: str = "UNKNOWN"


class RiskAgent:
    """Agent responsible for identifying and classifying risks in text.

    Uses a strict prompt to force the LLM to act as a safety and compliance 
    auditor, returning an array of evaluated hazards in JSON format.
    """

    def __init__(self, llm_generate_fn: Callable[[str, str], str]) -> None:
        """Initializes the RiskAgent.

        Args:
            llm_generate_fn: A callable that accepts a (system_prompt, user_prompt) 
                and returns a raw text string from the LLM.
        """
        self.llm_generate = llm_generate_fn
        
        self._system_prompt = (
            "You are an expert safety and compliance auditor for a mass transit system. "
            "Your task is to analyze the provided text and identify any operational risks, "
            "safety hazards, or compliance violations.\n\n"
            "RULES:\n"
            "1. Output your response in strictly valid JSON format.\n"
            "2. If no risks are found, return an empty array for 'identified_risks' and set 'overall_risk_level' to 'NONE'.\n"
            "3. The 'severity' field must be one of: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'.\n"
            "4. The 'overall_risk_level' should reflect the highest severity found, or 'NONE'.\n\n"
            "EXPECTED JSON SCHEMA:\n"
            "{\n"
            '  "identified_risks": [\n'
            '    {\n'
            '      "description": "string",\n'
            '      "severity": "string",\n'
            '      "mitigation_mentioned": "string or null"\n'
            '    }\n'
            '  ],\n'
            '  "overall_risk_level": "string"\n'
            "}"
        )
        logger.debug("RiskAgent initialized.")

    def analyze_risks(self, text: str) -> RiskAssessmentResult:
        """Analyzes the text to extract safety and operational risks.

        Args:
            text: The raw document text to evaluate.

        Returns:
            A RiskAssessmentResult dataclass containing the extracted hazards.
        """
        if not text or not text.strip():
            logger.warning("RiskAgent received empty text. Returning no risks.")
            return RiskAssessmentResult(identified_risks=[], overall_risk_level="NONE")

        user_prompt = f"--- DOCUMENT TEXT ---\n{text}\n\nIdentify any risks."
        
        try:
            logger.debug(f"Dispatching risk analysis request (Text length: {len(text)}).")
            raw_response = self.llm_generate(self._system_prompt, user_prompt)
            return self._parse_response(raw_response)
        except Exception as exc:
            logger.error(f"RiskAgent execution failed: {exc}")
            # Fail closed: return empty risks on error
            return RiskAssessmentResult(identified_risks=[], overall_risk_level="ERROR")

    def _parse_response(self, response_text: str) -> RiskAssessmentResult:
        """Extracts and validates the JSON payload from the LLM's response."""
        clean_text = response_text.strip()
        
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            parsed_data: dict[str, Any] = json.loads(clean_text.strip())
            
            risks_data = parsed_data.get("identified_risks", [])
            identified_risks: List[RiskItem] = []
            
            valid_severities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

            for r_data in risks_data:
                severity = str(r_data.get("severity", "UNKNOWN")).upper()
                if severity not in valid_severities:
                    severity = "UNKNOWN"
                    
                identified_risks.append(RiskItem(
                    description=str(r_data.get("description", "Unknown risk description")),
                    severity=severity,
                    mitigation_mentioned=r_data.get("mitigation_mentioned")
                ))

            overall_level = str(parsed_data.get("overall_risk_level", "UNKNOWN")).upper()

            return RiskAssessmentResult(
                identified_risks=identified_risks,
                overall_risk_level=overall_level
            )

        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.error(f"Failed to parse LLM risk analysis response: {exc}. Raw: {response_text}")
            return RiskAssessmentResult(identified_risks=[], overall_risk_level="ERROR")