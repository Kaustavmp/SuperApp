SCHEMA_INDUCTION_SYSTEM_PROMPT = """You are an expert document completeness analyzer.
Your task is to analyze documents and infer a comprehensive schema (taxonomy of topics/sections) that a complete document of this type should cover.
You must return your response as a JSON array of objects.
"""

SCHEMA_INDUCTION_USER_PROMPT = """Domain: {domain}

Document Content:
{document_content}

Infer a comprehensive schema of all topics and sections that a complete document of this domain should cover based on the provided document.
Output a JSON array of objects, where each object has the following fields:
- category: (string) The broad category or section name.
- topic: (string) The specific topic within the category.
- description: (string) A brief description of what should be covered.
- importance: (string) The importance level: "low", "medium", "high", or "critical".

Output only the JSON array.
"""

SCHEMA_MERGE_PROMPT = """You are given multiple schemas (JSON arrays) induced from different documents in the same domain.
Merge and deduplicate them into a single, comprehensive schema.
Output a single JSON array of objects with fields: category, topic, description, importance (low/medium/high/critical).
Resolve duplicates and unify similar topics.

Schemas to merge:
{schemas}

Output only the merged JSON array.
"""
