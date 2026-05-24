You are processing a saved web article for a personal knowledge base.

Extract:
- title: the article title (infer from content if not explicit)
- summary: 2-3 sentences capturing the core idea. Be specific — specific enough
  to remind the user why they saved this article months from now.
- key_concepts: 3-8 lowercase keywords including both the explicit terms used
  in the article AND semantically related concepts useful for future search
  (e.g. if the article discusses "RLHF", also include "reinforcement learning",
  "alignment", "fine-tuning").

If the content is low-quality, paywalled, empty, or contains only navigation/ads:
{ "error": "insufficient_content" }

Respond ONLY with valid JSON matching this schema — no markdown fences, no explanation:
{
  "title": "string",
  "summary": "string",
  "key_concepts": ["string", ...]
}
