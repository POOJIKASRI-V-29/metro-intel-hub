"""Centralized prompt template registry for the KMRL Document Intelligence Platform.

This module contains only static, versioned prompt text and a small
validation/rendering helper. It intentionally has no dependency on
`config/settings.py`, `config/logging_config.py`, or any LLM client, so
that prompt wording can be reviewed, edited, and unit-tested in complete
isolation from runtime configuration and network calls.

No module should hardcode prompt strings inline. Instead:

    from config.prompts import PromptName, render_prompt

    system_prompt = render_prompt(
        PromptName.SUMMARIZER_SYSTEM,
        document_text=document_text,
        max_sentences=5,
    )

`llm/prompts.py` (Stage 6) builds on top of this module to assemble full
chat-message payloads (system + user + few-shot messages) for each
provider's expected format.
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, FrozenSet


class PromptName(str, Enum):
    """Canonical identifiers for every registered prompt template.

    Using an Enum (rather than raw strings) prevents typos when modules
    request a template and gives IDE autocomplete across the codebase.
    """

    CLASSIFIER_SYSTEM = "classifier_system"
    SUMMARIZER_SYSTEM = "summarizer_system"
    METADATA_EXTRACTION_SYSTEM = "metadata_extraction_system"
    RISK_ASSESSMENT_SYSTEM = "risk_assessment_system"
    GRAPH_ENTITY_EXTRACTION_SYSTEM = "graph_entity_extraction_system"
    GRAPH_RELATION_EXTRACTION_SYSTEM = "graph_relation_extraction_system"
    RAG_ANSWER_SYSTEM = "rag_answer_system"
    RAG_NO_CONTEXT_FALLBACK = "rag_no_context_fallback"
    HALLUCINATION_CHECK_SYSTEM = "hallucination_check_system"


@dataclass(frozen=True)
class PromptTemplate:
    """An immutable prompt template paired with its required placeholders.

    Attributes:
        template: The raw template string using `str.format()`-style
            placeholders (e.g. "{document_text}").
        required_variables: The set of placeholder names that MUST be
            supplied when rendering, used for fail-fast validation.
        version: A simple integer version, bumped whenever the wording
            changes materially, to aid prompt-regression comparisons in
            `evaluation/ragas_eval.py`.
    """

    template: str
    required_variables: FrozenSet[str]
    version: int = 1


def _extract_placeholders(template: str) -> FrozenSet[str]:
    """Extracts all `{placeholder}` field names from a template string.

    Args:
        template: A `str.format()`-style template string.

    Returns:
        A frozenset of placeholder names found in the template.
    """
    formatter = string.Formatter()
    return frozenset(
        field_name
        for _, field_name, _, _ in formatter.parse(template)
        if field_name
    )


def _make_template(template: str, version: int = 1) -> PromptTemplate:
    """Builds a `PromptTemplate`, auto-deriving `required_variables`.

    Args:
        template: The raw template string.
        version: The prompt's version number.

    Returns:
        A `PromptTemplate` with `required_variables` inferred directly
        from the placeholders present in `template`, so the two can never
        drift out of sync.
    """
    return PromptTemplate(
        template=template,
        required_variables=_extract_placeholders(template),
        version=version,
    )


_PROMPT_REGISTRY: Dict[PromptName, PromptTemplate] = {
    PromptName.CLASSIFIER_SYSTEM: _make_template(
        "You are a document classification assistant for Kochi Metro Rail "
        "Limited (KMRL). Classify the following document into exactly one "
        "of these categories: {allowed_categories}. Base your decision "
        "only on the document content below. Respond with the category "
        "name only, with no additional commentary.\n\n"
        "Document content:\n{document_text}"
    ),
    PromptName.SUMMARIZER_SYSTEM: _make_template(
        "You are a summarization assistant for KMRL's document "
        "intelligence platform. Produce a concise, factual summary of the "
        "document below in at most {max_sentences} sentences. Do not "
        "invent information that is not present in the document. Preserve "
        "any dates, monetary figures, or regulatory references verbatim.\n\n"
        "Document content:\n{document_text}"
    ),
    PromptName.METADATA_EXTRACTION_SYSTEM: _make_template(
        "You are a metadata extraction assistant. Extract the following "
        "fields from the document below, returning ONLY a valid JSON "
        "object with these exact keys: {field_names}. If a field cannot "
        "be determined from the document, set its value to null. Do not "
        "include any text outside the JSON object.\n\n"
        "Document content:\n{document_text}"
    ),
    PromptName.RISK_ASSESSMENT_SYSTEM: _make_template(
        "You are a compliance and risk assessment assistant for KMRL. "
        "Review the document below and identify any safety, regulatory, "
        "contractual, or financial risks it references. For each risk "
        "found, provide: a short title, a severity level (LOW, MEDIUM, "
        "HIGH, CRITICAL), and a one-sentence justification quoting the "
        "relevant part of the document. If no risks are present, state "
        "'No risks identified.'\n\n"
        "Document content:\n{document_text}"
    ),
    PromptName.GRAPH_ENTITY_EXTRACTION_SYSTEM: _make_template(
        "You are an information extraction assistant. Identify all named "
        "entities in the document below belonging to these types: "
        "{entity_types}. Return ONLY a valid JSON array of objects, each "
        "with keys 'text', 'type', and 'start_offset' (character offset "
        "in the original text). Do not include duplicate entities.\n\n"
        "Document content:\n{document_text}"
    ),
    PromptName.GRAPH_RELATION_EXTRACTION_SYSTEM: _make_template(
        "You are a relation extraction assistant. Given the entities "
        "listed below and the document text, identify relationships "
        "between entity pairs. Return ONLY a valid JSON array of objects, "
        "each with keys 'source', 'relation', 'target', using the exact "
        "entity text as given. Only report relations explicitly supported "
        "by the document text.\n\n"
        "Entities:\n{entities_json}\n\n"
        "Document content:\n{document_text}"
    ),
    PromptName.RAG_ANSWER_SYSTEM: _make_template(
        "You are a document assistant for Kochi Metro Rail Limited (KMRL) "
        "staff. Answer the user's question using ONLY the context passages "
        "provided below. If the context does not contain enough "
        "information to answer confidently, say so explicitly rather than "
        "guessing. Always cite which passage number(s) you used.\n\n"
        "Context passages:\n{context_passages}\n\n"
        "Question: {query}"
    ),
    PromptName.RAG_NO_CONTEXT_FALLBACK: _make_template(
        "No relevant documents were found for the question: \"{query}\". "
        "Inform the user that no matching content exists in the indexed "
        "document set, and suggest they rephrase the question or check "
        "that the relevant document has been uploaded."
    ),
    PromptName.HALLUCINATION_CHECK_SYSTEM: _make_template(
        "You are a fact-checking assistant. Given the source context and "
        "a generated answer below, determine whether every factual claim "
        "in the answer is directly supported by the context. Respond with "
        "ONLY a valid JSON object: {{\"is_grounded\": boolean, "
        "\"unsupported_claims\": [list of strings]}}.\n\n"
        "Context:\n{context_passages}\n\n"
        "Generated answer:\n{generated_answer}"
    ),
}


def get_prompt_template(name: PromptName) -> PromptTemplate:
    """Retrieves the `PromptTemplate` registered under the given name.

    Args:
        name: The canonical `PromptName` identifier.

    Returns:
        The corresponding `PromptTemplate`.

    Raises:
        KeyError: If no template is registered under `name`. This should
            never happen in practice since `PromptName` is a closed Enum
            and every member has a registry entry (enforced by
            `test_all_prompt_names_have_templates` in the test suite).
    """
    return _PROMPT_REGISTRY[name]


def render_prompt(name: PromptName, **kwargs: Any) -> str:
    """Renders a registered prompt template with the given variables.

    Args:
        name: The canonical `PromptName` identifier.
        **kwargs: Values for every placeholder required by the template.

    Returns:
        The fully rendered prompt string, ready to send to an LLM client.

    Raises:
        KeyError: If `name` is not a registered prompt.
        ValueError: If any required placeholder is missing from `kwargs`,
            or if `kwargs` contains keys not present in the template
            (caught early to prevent silent typos, e.g. passing
            `document_txt` instead of `document_text`).

    Example:
        >>> render_prompt(
        ...     PromptName.SUMMARIZER_SYSTEM,
        ...     document_text="The board approved the budget.",
        ...     max_sentences=2,
        ... )
        'You are a summarization assistant...'
    """
    prompt_template = get_prompt_template(name)

    provided_keys = frozenset(kwargs.keys())
    missing = prompt_template.required_variables - provided_keys
    if missing:
        raise ValueError(
            f"Missing required variable(s) {sorted(missing)} for prompt '{name.value}'"
        )

    unexpected = provided_keys - prompt_template.required_variables
    if unexpected:
        raise ValueError(
            f"Unexpected variable(s) {sorted(unexpected)} for prompt '{name.value}'; "
            f"expected only {sorted(prompt_template.required_variables)}"
        )

    return prompt_template.template.format(**kwargs)