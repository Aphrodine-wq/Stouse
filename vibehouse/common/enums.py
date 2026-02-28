import enum


class UserRole(str, enum.Enum):
    HOMEOWNER = "homeowner"
    CONTRACTOR = "contractor"
    INSPECTOR = "inspector"
    ADMIN = "admin"


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    DESIGNING = "designing"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PhaseType(str, enum.Enum):
    SITE_PREP = "site_prep"
    FOUNDATION = "foundation"
    FRAMING = "framing"
    ROOFING = "roofing"
    MEP = "mep"
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    LANDSCAPE = "landscape"
    FINAL = "final"


class TaskStatus(str, enum.Enum):
    BACKLOG = "backlog"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"


class DesignArtifactType(str, enum.Enum):
    FLOOR_PLAN = "floor_plan"
    ELEVATION = "elevation"
    STRUCTURAL = "structural"
    MEP = "mep"
    MATERIAL_LIST = "material_list"
    COST_ESTIMATE = "cost_estimate"


class DisputeStatus(str, enum.Enum):
    IDENTIFIED = "identified"
    DIRECT_RESOLUTION = "direct_resolution"
    AI_MEDIATION = "ai_mediation"
    EXTERNAL_MEDIATION = "external_mediation"
    RESOLVED = "resolved"
    CLOSED = "closed"


class DisputeType(str, enum.Enum):
    QUALITY = "quality"
    TIMELINE = "timeline"
    BUDGET = "budget"
    SCOPE = "scope"
    SAFETY = "safety"
    COMMUNICATION = "communication"


class ContractStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class VendorSearchStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class BidStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    OVERDUE = "overdue"


class NotificationType(str, enum.Enum):
    PROJECT_UPDATE = "project_update"
    DESIGN_READY = "design_ready"
    BID_RECEIVED = "bid_received"
    PAYMENT_RECEIVED = "payment_received"
    INVOICE_SENT = "invoice_sent"
    DISPUTE_FILED = "dispute_filed"
    DISPUTE_RESOLVED = "dispute_resolved"
    TASK_COMPLETED = "task_completed"
    REPORT_READY = "report_ready"
    CHANGE_ORDER = "change_order"
    SYSTEM = "system"


class ChangeOrderStatus(str, enum.Enum):
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"


class DocumentCategory(str, enum.Enum):
    GENERAL = "general"
    CONTRACT = "contract"
    PERMIT = "permit"
    INSPECTION = "inspection"
    PHOTO = "photo"
    DRAWING = "drawing"
    INVOICE = "invoice"
    INSURANCE = "insurance"
