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
