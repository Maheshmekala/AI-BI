"""
RAG Engine — Natural Language → SQL via Retrieval-Augmented Generation.

Pipeline:
1. User asks a question in natural language
2. Router determines intent (chart, data query, general chat)
3. Schema index retrieves relevant table/column context
4. Few-shot store retrieves similar Q→SQL examples
5. LLM generates SQL with the augmented context
6. SQL is executed against DuckDB → results returned
7. Semantic cache stores Q→SQL pair for future reuse
"""
from __future__ import annotations
