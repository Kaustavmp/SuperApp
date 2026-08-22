"""Prompts for coverage diffing."""

COVERAGE_CHECK_SYSTEM_PROMPT = """You are an expert document coverage analyst.
Your task is to determine whether a given document corpus adequately addresses a specific required schema topic.
You must return your assessment as a valid JSON object.
"""

COVERAGE_CHECK_USER_PROMPT = """Schema Topic: {schema_topic}
Schema Description: {schema_description}

Document Content:
{document_content}

Assess whether the document content adequately addresses the schema topic.
Your response must be a JSON object with the following fields:
- "status": A string value of either "covered", "partially_covered", or "missing".
- "confidence": A float between 0.0 and 1.0 indicating your confidence.
- "reasoning": A detailed explanation for your assessment.
- "evidence": A list of relevant string quotes from the document (if found), or an empty list if none.
"""
