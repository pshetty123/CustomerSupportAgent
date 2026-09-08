from enum import Enum

from pydantic import BaseModel, Field


class Sentiment(str, Enum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"


class Emotion(str, Enum):
    HAPPY = "Happy"
    SATISFIED = "Satisfied"
    NEUTRAL = "Neutral"
    CONFUSED = "Confused"
    DISAPPOINTED = "Disappointed"
    FRUSTRATED = "Frustrated"
    ANGRY = "Angry"


class Category(str, Enum):
    BUG = "Bug"
    FEATURE_REQUEST = "Feature Request"
    BILLING = "Billing"
    UX_USABILITY = "UX/Usability"
    CUSTOMER_SUPPORT = "Customer Support"
    PERFORMANCE = "Performance"
    OTHER = "Other"


class Priority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class AnalysisResult(BaseModel):
    sentiment: Sentiment
    emotion: Emotion
    category: Category
    priority: Priority
    summary: str = Field(..., description="1-2 sentence summary of the review")
    suggested_reply: str = Field(..., description="Draft support reply, ready to send or edit")


class ExecutiveSummary(BaseModel):
    summary: str = Field(..., description="2-4 sentence narrative summary of patterns in the feedback")
    next_steps: list[str] = Field(..., description="3-5 concrete next steps for the product team")


class OpportunityProposal(BaseModel):
    theme: str = Field(..., description="The recurring feedback pattern observed")
    evidence_count: int = Field(..., description="Number of reviews supporting this theme")
    matched_pillar: str | None = Field(
        ..., description="Name of the strategy pillar this relates to, or null if none"
    )
    rationale: str = Field(..., description="Why this theme is or isn't aligned with strategy")
    title: str = Field(..., description="Proposed opportunity title")
    description: str = Field(..., description="1-3 sentence proposed opportunity description")


class OpportunityProposals(BaseModel):
    proposals: list[OpportunityProposal]
