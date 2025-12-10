"""Pydantic schemas for Structured Outputs."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


def make_schema_strict(schema: dict) -> dict:
    """Recursively enforce OpenAI Structured Outputs strictness."""
    if isinstance(schema, dict):
        t = schema.get("type")
        if t == "object":
            schema["additionalProperties"] = False
            props = schema.get("properties", {})
            schema["required"] = list(props.keys())
            for k, v in props.items():
                props[k] = make_schema_strict(v)
        elif t == "array":
            if "items" in schema:
                schema["items"] = make_schema_strict(schema["items"])
        else:
            for key in ("anyOf", "oneOf", "allOf"):
                if key in schema and isinstance(schema[key], list):
                    schema[key] = [make_schema_strict(s) for s in schema[key]]
        for key in ("$defs", "definitions"):
            if key in schema and isinstance(schema[key], dict):
                schema[key] = {k: make_schema_strict(v) for k, v in schema[key].items()}
    return schema


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

