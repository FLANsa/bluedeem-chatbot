"""Pydantic schemas for Structured Outputs."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Entity(BaseModel):
    """Entity extracted from user message."""
    type: str = Field(..., description="Entity type: doctor_name, service_name, branch_id, phone, date, time")
    value: str = Field(..., description="Entity value")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class IntentSchema(BaseModel):
    """Structured output for intent classification."""
    intent: str = Field(
        ...,
        description="Intent: greeting, doctor, branch, service, booking, hours, contact, faq, thanks, goodbye, unclear, general"
    )
    entities: List[Entity] = Field(default_factory=list, description="Extracted entities")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    next_action: str = Field(
        ...,
        description="Next action: respond_directly, ask_clarification, use_llm, start_booking"
    )


class AgentResponseSchema(BaseModel):
    """Structured output for agent responses."""
    response_text: str = Field(..., description="Response text in Najdi dialect")
    needs_clarification: bool = Field(..., description="Whether clarification is needed")
    suggested_questions: List[str] = Field(..., description="Suggested follow-up questions")


class BookingStateSchema(BaseModel):
    """Booking state schema."""
    state: str = Field(..., description="Current state: name, phone, service, branch, date_time, done")
    collected_data: Dict[str, Any] = Field(default_factory=dict, description="Collected booking data")

