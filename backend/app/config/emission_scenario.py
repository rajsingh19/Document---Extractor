"""
config/emission_scenario.py — Configuration and Constants for Emissions Scenario Engine (Step 22C).

Defines lifecycle statuses, supported scenario types, quantification levels,
target comparison states, and calculation versioning.
"""

SCENARIO_CALCULATION_VERSION = "1.0"

# ── Scenario Types ─────────────────────────────────────────────────────────────
SCENARIO_TYPE_REDUCE_ACTIVITY = "REDUCE_ACTIVITY"
SCENARIO_TYPE_INCREASE_ACTIVITY = "INCREASE_ACTIVITY"
SCENARIO_TYPE_REPLACE_SOURCE = "REPLACE_SOURCE"
SCENARIO_TYPE_SHIFT_SOURCE = "SHIFT_SOURCE"
SCENARIO_TYPE_ADD_SOURCE = "ADD_SOURCE"
SCENARIO_TYPE_REMOVE_SOURCE = "REMOVE_SOURCE"

VALID_SCENARIO_TYPES = {
    SCENARIO_TYPE_REDUCE_ACTIVITY,
    SCENARIO_TYPE_INCREASE_ACTIVITY,
    SCENARIO_TYPE_REPLACE_SOURCE,
    SCENARIO_TYPE_SHIFT_SOURCE,
    SCENARIO_TYPE_ADD_SOURCE,
    SCENARIO_TYPE_REMOVE_SOURCE,
}

# ── Scenario Lifecycle Statuses ────────────────────────────────────────────────
SCENARIO_STATUS_DRAFT = "DRAFT"
SCENARIO_STATUS_CALCULATED = "CALCULATED"
SCENARIO_STATUS_ARCHIVED = "ARCHIVED"

VALID_SCENARIO_STATUSES = {
    SCENARIO_STATUS_DRAFT,
    SCENARIO_STATUS_CALCULATED,
    SCENARIO_STATUS_ARCHIVED,
}

# ── Quantification Statuses ───────────────────────────────────────────────────
QUANTIFICATION_STATUS_QUANTIFIED = "QUANTIFIED"
QUANTIFICATION_STATUS_PARTIALLY_QUANTIFIED = "PARTIALLY_QUANTIFIED"
QUANTIFICATION_STATUS_NOT_QUANTIFIABLE = "NOT_QUANTIFIABLE"

VALID_QUANTIFICATION_STATUSES = {
    QUANTIFICATION_STATUS_QUANTIFIED,
    QUANTIFICATION_STATUS_PARTIALLY_QUANTIFIED,
    QUANTIFICATION_STATUS_NOT_QUANTIFIABLE,
}

# ── Target Comparison Statuses ────────────────────────────────────────────────
TARGET_STATUS_MET = "TARGET_MET"
TARGET_STATUS_NOT_MET = "TARGET_NOT_MET"
TARGET_STATUS_NOT_DEFINED = "TARGET_NOT_DEFINED"
TARGET_STATUS_SCENARIO_NOT_QUANTIFIABLE = "SCENARIO_NOT_QUANTIFIABLE"

VALID_TARGET_STATUSES = {
    TARGET_STATUS_MET,
    TARGET_STATUS_NOT_MET,
    TARGET_STATUS_NOT_DEFINED,
    TARGET_STATUS_SCENARIO_NOT_QUANTIFIABLE,
}

# ── Line Item Result Statuses ─────────────────────────────────────────────────
RESULT_STATUS_QUANTIFIED = "QUANTIFIED"
RESULT_STATUS_UNRESOLVED_FACTOR = "UNRESOLVED_FACTOR"
RESULT_STATUS_MISSING_ACTIVITY = "MISSING_ACTIVITY"
RESULT_STATUS_ERROR = "ERROR"

# ── Defaults & Safeguard Messages ─────────────────────────────────────────────
DEFAULT_UNRESOLVED_FACTOR_NOTE = "A verified emission factor is not currently resolved for this replacement source. Quantitative emissions reduction cannot be calculated without substituting speculative values."
DEFAULT_SCENARIO_CAUTION = "Modeled scenario estimate based on user-defined assumptions. Does not represent historical actuals or guarantee operational reduction causality."
