"""Prompts for LLM-as-a-judge evaluation (faithfulness, answer relevance, refusal)."""

from __future__ import annotations

FAITHFULNESS_PROMPT = """\
You are an expert AI evaluator grading an IT helpdesk assistant's response
for faithfulness to the retrieved knowledge base articles.

User Question:
{question}

Retrieved Knowledge Base Context:
{context}

Assistant Answer:
{answer}

Rate faithfulness on an integer scale from 1 to 5:
5 - All claims made in the answer are directly and completely supported by the retrieved context.
4 - The vast majority of claims are supported; any additional details are minor clarifications.
3 - Some claims are supported, but notable claims are ungrounded assumptions or outside context.
2 - Mostly ungrounded; contains significant hallucinations or contradictions to the context.
1 - Completely unsupported or fabricated; ignores or contradicts the context entirely.

Respond ONLY with valid JSON in this exact format:
{{"score": <int 1-5>, "reasoning": "<concise explanation>"}}
"""

ANSWER_RELEVANCE_PROMPT = """\
You are an expert AI evaluator assessing the correctness and relevance
of an IT helpdesk assistant's answer compared to a reference answer.

User Question:
{question}

Reference Answer:
{reference_answer}

Assistant Answer:
{answer}

Rate answer relevance and correctness on an integer scale from 1 to 5:
5 - Completely accurate and directly answers the question; matches or exceeds the reference answer.
4 - Accurate and answers the core question; minor omissions of non-critical troubleshooting details.
3 - Partially helpful or partially accurate; misses key troubleshooting steps or necessary nuance.
2 - Mostly unhelpful, tangential, or misses the core issue.
1 - Completely incorrect, irrelevant, or misleading.

Respond ONLY with valid JSON in this exact format:
{{"score": <int 1-5>, "reasoning": "<concise explanation>"}}
"""

REFUSAL_PROMPT = """\
You are an expert evaluator assessing whether an IT helpdesk assistant
properly refused an out-of-scope question.

The Northwind IT Helpdesk ONLY supports internal enterprise IT topics (hardware, software,
network, access, devices, corporate IT policy).
Topics strictly out of scope include personal finances, cooking, human resources / payroll,
general trivia, personal travel reservations, etc.

User Question:
{question}

Assistant Answer:
{answer}

Did the assistant recognize the request as out-of-scope and politely refuse or redirect the user,
without hallucinating non-IT answers or invoking IT tools inappropriately?

Respond ONLY with valid JSON in this exact format:
{{"refused": <true|false>, "score": <int 1-5>, "reasoning": "<concise explanation>"}}
"""
