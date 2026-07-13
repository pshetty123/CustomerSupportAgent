from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from src.schemas import AnalysisResult, ExecutiveSummary

PROMPT_TEMPLATE = """You are a customer support analyst. Analyze the following customer \
review and extract structured information about it.

Priority guidance:
- Critical: an angry or churn-risk customer, or a broken core feature
- High: strong negative sentiment or a blocking issue
- Medium: negative or neutral feedback with moderate impact
- Low: positive or minor feedback

Also write a short summary and a draft support reply the team could send as-is or lightly edit.

Review:
\"\"\"{review_text}\"\"\"
"""

EXECUTIVE_SUMMARY_PROMPT_TEMPLATE = """You are a product analyst preparing a briefing for a product \
team based on a set of already-triaged customer feedback.

Write a short executive summary (2-4 sentences) describing the overall patterns in this data: \
what customers are saying, which issues are most common, and how urgent they are. Then suggest \
3-5 concrete, specific next steps for the product team, grounded in the actual categories and \
priorities present in the data below — not generic advice.

Feedback data:
{digest}
"""


class GeminiClient:
    def __init__(self, api_key: str, model: str):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    def analyze_review(self, review_text: str) -> AnalysisResult:
        response = self._client.models.generate_content(
            model=self._model,
            contents=PROMPT_TEMPLATE.format(review_text=review_text),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AnalysisResult,
            ),
        )
        return AnalysisResult.model_validate_json(response.text)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    def generate_executive_summary(self, digest_text: str) -> ExecutiveSummary:
        response = self._client.models.generate_content(
            model=self._model,
            contents=EXECUTIVE_SUMMARY_PROMPT_TEMPLATE.format(digest=digest_text),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ExecutiveSummary,
            ),
        )
        return ExecutiveSummary.model_validate_json(response.text)
