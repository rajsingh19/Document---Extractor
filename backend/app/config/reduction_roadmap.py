"""
config/reduction_roadmap.py — Configuration and Named Constants for Personalized Reduction Roadmap Engine (Step 22B).

Defines deterministic planning rules, planning phases, action types, statuses,
and explicit product boundaries preventing fabricated savings/ROI.
"""
from decimal import Decimal

REDUCTION_ROADMAP_VERSION = "1.0"

# ==============================================================================
# 1. PLANNING PHASES & WINDOWS (Suggested planning windows, not predictions)
# ==============================================================================
PHASE_1_FOUNDATION = "PHASE_1_FOUNDATION"       # Days 0–30: Resolve data gaps, confirm baseline, validate activity data
PHASE_2_ACTION = "PHASE_2_ACTION"               # Days 31–90: Initiate reduction projects, track activity, establish project baselines
PHASE_3_MEASUREMENT = "PHASE_3_MEASUREMENT"     # Days 91–180: Measure results, compare against baseline, update ledger
PHASE_4_VERIFICATION = "PHASE_4_VERIFICATION"   # Days 181+: Verification, reporting, target progress assessment

PHASE_LABELS = {
    PHASE_1_FOUNDATION: "Phase 1: Foundation (0–30 days)",
    PHASE_2_ACTION: "Phase 2: Action & Implementation (31–90 days)",
    PHASE_3_MEASUREMENT: "Phase 3: Measurement & Accounting (91–180 days)",
    PHASE_4_VERIFICATION: "Phase 4: Verification & Target Review (181+ days)",
}

# ==============================================================================
# 2. ACTION TYPES
# ==============================================================================
ACTION_TYPE_DATA_COLLECTION = "DATA_COLLECTION"
ACTION_TYPE_DATA_QUALITY = "DATA_QUALITY"
ACTION_TYPE_BASELINE_REVIEW = "BASELINE_REVIEW"
ACTION_TYPE_INVESTIGATION = "INVESTIGATION"
ACTION_TYPE_REDUCTION_PROJECT = "REDUCTION_PROJECT"
ACTION_TYPE_MONITORING = "MONITORING"
ACTION_TYPE_MEASUREMENT = "MEASUREMENT"
ACTION_TYPE_VERIFICATION = "VERIFICATION"
ACTION_TYPE_REPORTING = "REPORTING"

VALID_ACTION_TYPES = {
    ACTION_TYPE_DATA_COLLECTION,
    ACTION_TYPE_DATA_QUALITY,
    ACTION_TYPE_BASELINE_REVIEW,
    ACTION_TYPE_INVESTIGATION,
    ACTION_TYPE_REDUCTION_PROJECT,
    ACTION_TYPE_MONITORING,
    ACTION_TYPE_MEASUREMENT,
    ACTION_TYPE_VERIFICATION,
    ACTION_TYPE_REPORTING,
}

# ==============================================================================
# 3. ROADMAP & ITEM STATUSES
# ==============================================================================
# Roadmap status
ROADMAP_STATUS_DRAFT = "DRAFT"
ROADMAP_STATUS_ACTIVE = "ACTIVE"
ROADMAP_STATUS_ON_TRACK = "ON_TRACK"
ROADMAP_STATUS_AT_RISK = "AT_RISK"
ROADMAP_STATUS_COMPLETED = "COMPLETED"
ROADMAP_STATUS_ARCHIVED = "ARCHIVED"

VALID_ROADMAP_STATUSES = {
    ROADMAP_STATUS_DRAFT,
    ROADMAP_STATUS_ACTIVE,
    ROADMAP_STATUS_ON_TRACK,
    ROADMAP_STATUS_AT_RISK,
    ROADMAP_STATUS_COMPLETED,
    ROADMAP_STATUS_ARCHIVED,
}

# Roadmap item status
ITEM_STATUS_NOT_STARTED = "NOT_STARTED"
ITEM_STATUS_IN_PROGRESS = "IN_PROGRESS"
ITEM_STATUS_BLOCKED = "BLOCKED"
ITEM_STATUS_COMPLETED = "COMPLETED"
ITEM_STATUS_CANCELLED = "CANCELLED"

VALID_ITEM_STATUSES = {
    ITEM_STATUS_NOT_STARTED,
    ITEM_STATUS_IN_PROGRESS,
    ITEM_STATUS_BLOCKED,
    ITEM_STATUS_COMPLETED,
    ITEM_STATUS_CANCELLED,
}

# ==============================================================================
# 4. CONTRIBUTION & FEASIBILITY STATUSES
# ==============================================================================
CONTRIBUTION_STATUS_NOT_QUANTIFIED = "NOT_QUANTIFIED"
CONTRIBUTION_STATUS_PARTIALLY_QUANTIFIED = "PARTIALLY_QUANTIFIED"
CONTRIBUTION_STATUS_QUANTIFIED = "QUANTIFIED"
CONTRIBUTION_STATUS_ESTIMATED = "ESTIMATED"

TARGET_FEASIBILITY_CALCULATED = "TARGET_CALCULATED"
TARGET_FEASIBILITY_UNKNOWN = "TARGET_FEASIBILITY_UNKNOWN"
TARGET_FEASIBILITY_DATA_INSUFFICIENT = "TARGET_DATA_INSUFFICIENT"
TARGET_FEASIBILITY_SUPPORTED = "TARGET_SUPPORTED"

# ==============================================================================
# 5. AUDIT EVENT TYPES
# ==============================================================================
EVENT_TYPE_CREATED = "CREATED"
EVENT_TYPE_STATUS_CHANGED = "STATUS_CHANGED"
EVENT_TYPE_ITEM_STATUS_CHANGED = "ITEM_STATUS_CHANGED"
EVENT_TYPE_TARGET_UPDATED = "TARGET_UPDATED"
EVENT_TYPE_REGENERATED = "REGENERATED"
EVENT_TYPE_NOTE_ADDED = "NOTE_ADDED"

# ==============================================================================
# 6. EFFORT & PRIORITY TIERS
# ==============================================================================
EFFORT_LOW = "LOW"
EFFORT_MEDIUM = "MEDIUM"
EFFORT_HIGH = "HIGH"

PRIORITY_CRITICAL = "CRITICAL"
PRIORITY_HIGH = "HIGH"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_LOW = "LOW"

# Default limitations text
DEFAULT_FEASIBILITY_NOTE = (
    "Current data identifies prioritized reduction areas, but verified intervention-level "
    "reduction estimates are not yet available to determine whether the full reduction target is achievable."
)

DEFAULT_MEASUREMENT_METHOD = (
    "Compare POSTED activity emissions for the project measurement period against the verified accounting baseline period."
)

DEFAULT_VERIFICATION_METHOD = (
    "Use the existing ReductionMeasurement / VerificationRecord internal and external review workflow (Step 17)."
)
