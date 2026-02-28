from decimal import Decimal

from pydantic import BaseModel


class TaskProgressSummary(BaseModel):
    total_tasks: int
    completed: int
    in_progress: int
    blocked: int
    completion_percent: float


class BudgetSummary(BaseModel):
    total_budget: Decimal | None
    total_spent: Decimal
    remaining: Decimal | None
    burn_rate_percent: float | None
    alert_level: str  # "green", "yellow", "red"


class ScheduleHealth(BaseModel):
    days_elapsed: int
    estimated_total_days: int
    percent_complete: float
    days_ahead_behind: int  # positive = ahead, negative = behind
    status: str  # "on_track", "at_risk", "behind"


class RiskAlert(BaseModel):
    severity: str  # "low", "medium", "high", "critical"
    category: str
    message: str


class DailyReportContent(BaseModel):
    date: str
    project_title: str
    executive_summary: str
    task_progress: TaskProgressSummary
    budget_summary: BudgetSummary
    schedule_health: ScheduleHealth
    activities_today: list[str]
    risk_alerts: list[RiskAlert]
    upcoming_milestones: list[str]
    weather_note: str | None = None
