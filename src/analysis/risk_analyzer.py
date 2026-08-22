"""Document risk analysis service.

Scope: Wraps the RiskAgent to process full documents. Handles chunk 
iteration, aggregates individual risk items, and determines the peak 
overall risk severity across the entire document.
"""

from __future__ import annotations

from typing import List

from config.logging_config import get_logger
from agents.risk_agent import RiskAgent, RiskAssessmentResult, RiskItem

logger = get_logger(__name__)


class DocumentRiskAnalyzerService:
    """Service to evaluate and aggregate risks across a full document."""

    # Define severity hierarchy for comparison (higher index = higher severity)
    SEVERITY_LEVELS = ["NONE", "UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

    def __init__(self, risk_agent: RiskAgent) -> None:
        """Initializes the service with the underlying agent."""
        self.agent = risk_agent

    def analyze_document_risks(self, text_chunks: List[str]) -> RiskAssessmentResult:
        """Evaluates all text chunks to aggregate a complete risk profile.

        Args:
            text_chunks: A list of text chunks representing the document.

        Returns:
            A RiskAssessmentResult containing all aggregated risks and the 
            highest severity level found.
        """
        if not text_chunks:
            logger.warning("No text chunks provided for risk analysis.")
            return RiskAssessmentResult(identified_risks=[], overall_risk_level="NONE")

        all_identified_risks: List[RiskItem] = []
        highest_severity = "NONE"

        for i, chunk in enumerate(text_chunks):
            try:
                logger.debug(f"Analyzing chunk {i+1}/{len(text_chunks)} for risks.")
                chunk_result = self.agent.analyze_risks(chunk)
                
                if chunk_result.identified_risks:
                    all_identified_risks.extend(chunk_result.identified_risks)

                # Update the overall document severity if the chunk's severity is higher
                highest_severity = self._get_higher_severity(highest_severity, chunk_result.overall_risk_level)

            except Exception as e:
                logger.error(f"Failed to analyze risks in chunk {i}: {e}")

        # Deduplicate risks (basic implementation based on description string)
        unique_risks = self._deduplicate_risks(all_identified_risks)

        logger.info(f"Risk analysis complete. Found {len(unique_risks)} unique risks. Max severity: {highest_severity}.")

        return RiskAssessmentResult(
            identified_risks=unique_risks,
            overall_risk_level=highest_severity
        )

    def _get_higher_severity(self, level_a: str, level_b: str) -> str:
        """Compares two severity levels and returns the higher one."""
        index_a = self.SEVERITY_LEVELS.index(level_a) if level_a in self.SEVERITY_LEVELS else 1
        index_b = self.SEVERITY_LEVELS.index(level_b) if level_b in self.SEVERITY_LEVELS else 1
        
        return level_a if index_a >= index_b else level_b

    def _deduplicate_risks(self, risks: List[RiskItem]) -> List[RiskItem]:
        """Removes duplicate risk items found across different chunks."""
        seen_descriptions = set()
        unique_risks = []
        
        for risk in risks:
            # Normalize description for comparison
            desc_norm = risk.description.strip().lower()
            if desc_norm not in seen_descriptions:
                seen_descriptions.add(desc_norm)
                unique_risks.append(risk)
                
        return unique_risks