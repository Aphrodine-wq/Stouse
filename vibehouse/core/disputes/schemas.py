from pydantic import BaseModel


class ResolutionOption(BaseModel):
    option_id: str
    title: str
    description: str
    impact: str
    recommended: bool = False


class DisputeAnalysis(BaseModel):
    severity: str  # "low", "medium", "high", "critical"
    category: str
    root_cause_assessment: str
    resolution_options: list[ResolutionOption]
    recommended_action: str
    estimated_resolution_days: int


class EscalationRule(BaseModel):
    from_status: str
    to_status: str
    trigger_hours: int
    notification_message: str
