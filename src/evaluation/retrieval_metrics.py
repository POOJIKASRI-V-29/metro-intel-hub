"""Retrieval evaluation metrics for the KMRL platform.

Scope: Information Retrieval (IR) metrics to evaluate the performance of 
the vector database and hybrid search pipelines. Includes Hit Rate (Recall@K), 
Mean Reciprocal Rank (MRR), and Precision@K. 
"""

from __future__ import annotations

import math
from typing import Sequence

from config.logging_config import get_logger

logger = get_logger(__name__)


def calculate_hit_rate_at_k(
    relevant_doc_ids: Sequence[str], 
    retrieved_doc_ids: Sequence[str], 
    k: int = 5
) -> float:
    """Calculates the Hit Rate (Recall) at K.

    Hit Rate is a binary metric (1.0 or 0.0) per query indicating whether 
    AT LEAST ONE relevant document appeared in the top K retrieved results.

    Args:
        relevant_doc_ids: A sequence of ground-truth document IDs relevant to the query.
        retrieved_doc_ids: A sequence of document IDs returned by the search pipeline.
        k: The rank cutoff limit.

    Returns:
        1.0 if a relevant document is found in the top K, otherwise 0.0.
    """
    if not relevant_doc_ids or not retrieved_doc_ids:
        return 0.0

    top_k_retrieved = retrieved_doc_ids[:k]
    relevant_set = set(relevant_doc_ids)

    for doc_id in top_k_retrieved:
        if doc_id in relevant_set:
            return 1.0

    return 0.0


def calculate_mrr(
    relevant_doc_ids: Sequence[str], 
    retrieved_doc_ids: Sequence[str]
) -> float:
    """Calculates the Mean Reciprocal Rank (MRR) for a single query.

    MRR evaluates how high the FIRST relevant document was placed in the 
    search results. A score of 1.0 means it was the top result; 0.5 means 
    it was second, etc.

    Args:
        relevant_doc_ids: A sequence of ground-truth document IDs.
        retrieved_doc_ids: A sequence of ranked document IDs returned by search.

    Returns:
        The reciprocal rank as a float between 0.0 and 1.0.
    """
    if not relevant_doc_ids or not retrieved_doc_ids:
        return 0.0

    relevant_set = set(relevant_doc_ids)

    for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
        if doc_id in relevant_set:
            return 1.0 / rank

    return 0.0


def calculate_precision_at_k(
    relevant_doc_ids: Sequence[str], 
    retrieved_doc_ids: Sequence[str], 
    k: int = 5
) -> float:
    """Calculates Precision at K.

    Measures the proportion of the top K retrieved documents that are 
    actually relevant.

    Args:
        relevant_doc_ids: A sequence of ground-truth document IDs.
        retrieved_doc_ids: A sequence of ranked document IDs returned by search.
        k: The rank cutoff limit.

    Returns:
        The ratio of relevant documents within the top K (0.0 to 1.0).
    """
    if not relevant_doc_ids or not retrieved_doc_ids or k <= 0:
        return 0.0

    top_k_retrieved = retrieved_doc_ids[:k]
    relevant_set = set(relevant_doc_ids)

    relevant_count = sum(1 for doc_id in top_k_retrieved if doc_id in relevant_set)
    
    # K might be larger than the total retrieved documents
    denominator = min(k, len(retrieved_doc_ids))
    if denominator == 0:
        return 0.0
        
    return relevant_count / denominator


def calculate_ndcg_at_k(
    relevant_doc_ids: Sequence[str], 
    retrieved_doc_ids: Sequence[str], 
    k: int = 5
) -> float:
    """Calculates Normalized Discounted Cumulative Gain (NDCG) at K.

    A metric that accounts for both the relevance of the retrieved documents 
    and their position (rank). Highly ranked relevant documents contribute 
    more to the score than lower-ranked ones.

    Args:
        relevant_doc_ids: A sequence of ground-truth document IDs.
        retrieved_doc_ids: A sequence of ranked document IDs returned by search.
        k: The rank cutoff limit.

    Returns:
        The NDCG score as a float between 0.0 and 1.0.
    """
    if not relevant_doc_ids or not retrieved_doc_ids or k <= 0:
        return 0.0

    top_k_retrieved = retrieved_doc_ids[:k]
    relevant_set = set(relevant_doc_ids)

    dcg = 0.0
    for i, doc_id in enumerate(top_k_retrieved):
        if doc_id in relevant_set:
            # relevance score is binary (1) in this implementation
            dcg += 1.0 / math.log2(i + 2)  # i+2 because index is 0-based and log2(1) = 0

    # Calculate Ideal DCG (IDCG) - assuming all top K results could be relevant
    idcg = 0.0
    ideal_relevant_count = min(len(relevant_doc_ids), k)
    for i in range(ideal_relevant_count):
        idcg += 1.0 / math.log2(i + 2)

    if idcg == 0.0:
        return 0.0

    return dcg / idcg