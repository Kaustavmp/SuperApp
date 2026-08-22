CLAIM_EXTRACTION_SYSTEM_PROMPT = """
You are an expert at extracting atomic factual and policy claims from text.
Your task is to identify discrete, self-contained factual claims or policy statements from the given text.
Output the claims as a JSON array of objects.
"""

CLAIM_EXTRACTION_USER_PROMPT = """
Extract discrete, self-contained factual or policy claims from the following text chunk:

{chunk_content}

Output the result as a JSON array of objects, where each object has a single field "claim_text" containing the atomic claim as a standalone statement.
"""

CONTRADICTION_CHECK_SYSTEM_PROMPT = """
You are a logical contradiction analyst.
Your task is to analyze two claims and determine if they contradict each other, support each other, or are unrelated.
Output the result as a JSON object.
"""

CONTRADICTION_CHECK_USER_PROMPT = """
Analyze the following two claims:

Claim A: {claim_a}
Claim B: {claim_b}

Determine the relationship between them. The relationship must be one of: "supports", "contradicts", "silent_on", or "unrelated".
Output a JSON object with the following fields:
- "relation": string (one of 'supports', 'contradicts', 'silent_on', 'unrelated')
- "confidence": float (between 0.0 and 1.0)
- "reasoning": string (explanation of why the relationship holds)
"""
