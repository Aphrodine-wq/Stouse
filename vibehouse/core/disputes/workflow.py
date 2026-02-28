from datetime import datetime, timedelta, timezone

from vibehouse.common.enums import DisputeStatus, DisputeType
from vibehouse.common.logging import get_logger
from vibehouse.core.disputes.schemas import DisputeAnalysis, EscalationRule, ResolutionOption

logger = get_logger("disputes.workflow")

# Escalation rules per PRD: 4h → Direct, 72h → AI Mediation, 96h → External
ESCALATION_RULES = [
    EscalationRule(
        from_status=DisputeStatus.IDENTIFIED.value,
        to_status=DisputeStatus.DIRECT_RESOLUTION.value,
        trigger_hours=4,
        notification_message="Dispute has been open for 4 hours. Moving to direct resolution.",
    ),
    EscalationRule(
        from_status=DisputeStatus.DIRECT_RESOLUTION.value,
        to_status=DisputeStatus.AI_MEDIATION.value,
        trigger_hours=72,
        notification_message="Direct resolution period expired. Escalating to AI mediation.",
    ),
    EscalationRule(
        from_status=DisputeStatus.AI_MEDIATION.value,
        to_status=DisputeStatus.EXTERNAL_MEDIATION.value,
        trigger_hours=96,
        notification_message="AI mediation period expired. Escalating to external mediation.",
    ),
]


def check_escalation_needed(
    current_status: str, status_changed_at: datetime
) -> EscalationRule | None:
    now = datetime.now(timezone.utc)

    for rule in ESCALATION_RULES:
        if rule.from_status == current_status:
            deadline = status_changed_at + timedelta(hours=rule.trigger_hours)
            if now >= deadline:
                return rule

    return None


def generate_resolution_options(
    dispute_type: str, description: str
) -> DisputeAnalysis:
    dtype = DisputeType(dispute_type) if dispute_type in DisputeType.__members__.values() else DisputeType.SCOPE

    # Generate type-specific resolution options
    options_map = {
        DisputeType.QUALITY: [
            ResolutionOption(
                option_id="q1",
                title="Rework at contractor's expense",
                description="Contractor redoes the work to meet specifications at no additional cost",
                impact="Timeline extends 3-5 days, no budget impact",
                recommended=True,
            ),
            ResolutionOption(
                option_id="q2",
                title="Partial credit and acceptance",
                description="Accept work as-is with a negotiated discount",
                impact="Budget savings, no timeline impact",
            ),
            ResolutionOption(
                option_id="q3",
                title="Third-party quality assessment",
                description="Hire an independent inspector to evaluate the work",
                impact="1-2 day delay, $500-1000 assessment cost",
            ),
        ],
        DisputeType.TIMELINE: [
            ResolutionOption(
                option_id="t1",
                title="Accelerated schedule with overtime",
                description="Contractor adds crew/hours to recover lost time",
                impact="May increase costs 10-15%, recovers 50-75% of delay",
                recommended=True,
            ),
            ResolutionOption(
                option_id="t2",
                title="Revised timeline acceptance",
                description="Accept the new timeline with adjusted milestones",
                impact="Overall project extends, dependent phases shift",
            ),
            ResolutionOption(
                option_id="t3",
                title="Penalty clause enforcement",
                description="Apply contractual penalty for late delivery",
                impact="Financial compensation, may strain relationship",
            ),
        ],
        DisputeType.BUDGET: [
            ResolutionOption(
                option_id="b1",
                title="Value engineering review",
                description="Review scope for cost-saving alternatives without compromising quality",
                impact="Potential 5-15% savings, minor spec changes",
                recommended=True,
            ),
            ResolutionOption(
                option_id="b2",
                title="Formal change order process",
                description="Document scope change and agree on revised budget",
                impact="Transparent cost adjustment with approval workflow",
            ),
            ResolutionOption(
                option_id="b3",
                title="Competitive re-bid",
                description="Solicit competing bids for remaining work",
                impact="2-3 week delay for bidding process",
            ),
        ],
    }

    # Default options for other dispute types
    default_options = [
        ResolutionOption(
            option_id="d1",
            title="Direct negotiation",
            description="Parties discuss and agree on a resolution directly",
            impact="Minimal delay if resolved quickly",
            recommended=True,
        ),
        ResolutionOption(
            option_id="d2",
            title="Mediated discussion",
            description="Platform facilitates structured dialogue between parties",
            impact="1-3 day resolution timeline",
        ),
        ResolutionOption(
            option_id="d3",
            title="Contract review and arbitration",
            description="Review contract terms and apply arbitration clause",
            impact="5-10 day process, binding resolution",
        ),
    ]

    options = options_map.get(dtype, default_options)

    severity_map = {
        DisputeType.SAFETY: "critical",
        DisputeType.QUALITY: "high",
        DisputeType.BUDGET: "high",
        DisputeType.TIMELINE: "medium",
        DisputeType.SCOPE: "medium",
        DisputeType.COMMUNICATION: "low",
    }

    return DisputeAnalysis(
        severity=severity_map.get(dtype, "medium"),
        category=dispute_type,
        root_cause_assessment=f"Analysis of {dispute_type} dispute based on project context and description.",
        resolution_options=options,
        recommended_action=next(
            (o.title for o in options if o.recommended), options[0].title
        ),
        estimated_resolution_days=3 if dtype == DisputeType.COMMUNICATION else 5,
    )
