"""
config/reduction_intelligence.py — Configuration and Scoring Constants for Reduction Opportunity Intelligence Engine (Step 22A).

CRITICAL BOUNDARIES:
- Deterministic weights and thresholds for priority ranking.
- No arbitrary magic numbers in service logic.
- Purely deterministic decision-support layer.
"""
from decimal import Decimal

REDUCTION_INTELLIGENCE_VERSION = "1.0"

# ==============================================================================
# 1. SCORING WEIGHTS (Total = 100)
# ==============================================================================
IMPACT_WEIGHT = Decimal("30.0")          # Materiality relative to total posted emissions
TREND_WEIGHT = Decimal("20.0")           # Historical emissions trend direction & magnitude
FORECAST_WEIGHT = Decimal("15.0")        # Step 21 predictive emission trajectory
PERSISTENCE_WEIGHT = Decimal("15.0")     # Consistency of issue across actual reporting periods
ACTIONABILITY_WEIGHT = Decimal("10.0")   # Presence of concrete, actionable operational opportunity
DATA_QUALITY_WEIGHT = Decimal("5.0")     # Data gaps, review flags, or confidence issues
BLOCKER_WEIGHT = Decimal("5.0")          # Material blockers (unresolved factor, missing activity)

# Validation check: sum must equal 100
TOTAL_MAX_WEIGHT = (
    IMPACT_WEIGHT
    + TREND_WEIGHT
    + FORECAST_WEIGHT
    + PERSISTENCE_WEIGHT
    + ACTIONABILITY_WEIGHT
    + DATA_QUALITY_WEIGHT
    + BLOCKER_WEIGHT
)
assert TOTAL_MAX_WEIGHT == Decimal("100.0"), f"Total weights must sum to 100, got {TOTAL_MAX_WEIGHT}"

# ==============================================================================
# 2. IMPACT THRESHOLDS & SCORE TIERS (Max 30)
# ==============================================================================
# Ratio: source_posted_emissions / total_posted_emissions
IMPACT_TIER_VERY_HIGH_PCT = Decimal("50.0")   # >= 50% of total posted emissions -> 30/30
IMPACT_TIER_HIGH_PCT = Decimal("25.0")        # 25% to <50% -> 22/30
IMPACT_TIER_MEDIUM_PCT = Decimal("10.0")      # 10% to <25% -> 14/30
# <10% -> 6/30

IMPACT_SCORE_VERY_HIGH = Decimal("30.0")
IMPACT_SCORE_HIGH = Decimal("22.0")
IMPACT_SCORE_MEDIUM = Decimal("14.0")
IMPACT_SCORE_LOW = Decimal("6.0")
IMPACT_SCORE_ZERO = Decimal("0.0")

# ==============================================================================
# 3. TREND THRESHOLDS & SCORE TIERS (Max 20)
# ==============================================================================
# Period-over-period percentage increase
TREND_TIER_STRONG_INCREASE_PCT = Decimal("25.0")   # >= 25% increase -> 20/20
TREND_TIER_MODERATE_INCREASE_PCT = Decimal("10.0") # 10% to <25% increase -> 14/20
TREND_TIER_WEAK_INCREASE_PCT = Decimal("0.0")      # 0% to <10% increase -> 8/20
# <= 0% increase -> 0/20

TREND_SCORE_STRONG = Decimal("20.0")
TREND_SCORE_MODERATE = Decimal("14.0")
TREND_SCORE_WEAK = Decimal("8.0")
TREND_SCORE_STABLE_OR_DECREASING = Decimal("0.0")

# Multi-period consecutive increase bonus (capped at TREND_WEIGHT)
TREND_REPEATED_INCREASE_BONUS = Decimal("4.0")

# ==============================================================================
# 4. FORECAST SCORE TIERS (Max 15)
# ==============================================================================
FORECAST_SCORE_INCREASE = Decimal("15.0")    # Forecast indicates >2% increase
FORECAST_SCORE_UNCERTAIN = Decimal("8.0")    # Forecast uncertain / moderate increase
FORECAST_SCORE_DECREASE = Decimal("0.0")     # Forecast indicates decrease
FORECAST_SCORE_UNAVAILABLE = Decimal("0.0")  # Insufficient data / unavailable (no penalty)

# ==============================================================================
# 5. PERSISTENCE SCORE TIERS (Max 15)
# ==============================================================================
# Based on count of actual distinct reporting periods with valid data
PERSISTENCE_PERIODS_STRONG = 3   # 3+ actual periods -> 15/15
PERSISTENCE_PERIODS_MODERATE = 2 # 2 actual periods -> 10/15
PERSISTENCE_PERIODS_LOW = 1      # 1 actual period -> 5/15

PERSISTENCE_SCORE_STRONG = Decimal("15.0")
PERSISTENCE_SCORE_MODERATE = Decimal("10.0")
PERSISTENCE_SCORE_LOW = Decimal("5.0")
PERSISTENCE_SCORE_ZERO = Decimal("0.0")

# ==============================================================================
# 6. ACTIONABILITY SCORE TIERS (Max 10)
# ==============================================================================
ACTIONABILITY_SCORE_CONCRETE = Decimal("10.0")  # Concrete ReductionOpportunity with actionable steps
ACTIONABILITY_SCORE_ANALYSIS = Decimal("6.0")   # Needs analysis / investigation
ACTIONABILITY_SCORE_DATA_GAP = Decimal("3.0")   # Classified as DATA_GAP
ACTIONABILITY_SCORE_NONE = Decimal("0.0")

# ==============================================================================
# 7. DATA QUALITY SCORE TIERS (Max 5)
# ==============================================================================
DATA_QUALITY_SCORE_UNRESOLVED_FACTOR = Decimal("5.0")  # Missing/unresolved emission factor
DATA_QUALITY_SCORE_REVIEW_REQUIRED = Decimal("4.0")    # Needs human review
DATA_QUALITY_SCORE_MISSING_DATA = Decimal("3.0")       # Missing activity fields
DATA_QUALITY_SCORE_CLEAN = Decimal("0.0")              # Verified, high quality

# ==============================================================================
# 8. BLOCKER SCORE TIERS (Max 5)
# ==============================================================================
BLOCKER_SCORE_CRITICAL = Decimal("5.0")   # Unresolved factor or missing core activity blocking accounting
BLOCKER_SCORE_MODERATE = Decimal("3.0")   # Data sufficiency / review blocker
BLOCKER_SCORE_NONE = Decimal("0.0")

# ==============================================================================
# 9. PRIORITY LEVEL CLASSIFICATION (Score 0 - 100)
# ==============================================================================
# Deterministic mapping thresholds
PRIORITY_THRESHOLD_CRITICAL = Decimal("80.0")  # >= 80 -> CRITICAL
PRIORITY_THRESHOLD_HIGH = Decimal("60.0")      # 60 to <80 -> HIGH
PRIORITY_THRESHOLD_MEDIUM = Decimal("40.0")    # 40 to <60 -> MEDIUM
PRIORITY_THRESHOLD_LOW = Decimal("20.0")       # 20 to <40 -> LOW
# < 20 -> INFORMATIONAL

PRIORITY_LEVEL_CRITICAL = "CRITICAL"
PRIORITY_LEVEL_HIGH = "HIGH"
PRIORITY_LEVEL_MEDIUM = "MEDIUM"
PRIORITY_LEVEL_LOW = "LOW"
PRIORITY_LEVEL_INFORMATIONAL = "INFORMATIONAL"

# ==============================================================================
# 10. EXISTING PROJECT MODIFIERS
# ==============================================================================
# Modifiers when a project already addresses this priority (applied transparently)
PROJECT_STATUS_IN_PROGRESS_ADJUSTMENT = Decimal("-10.0")  # Avoid presenting in-progress project as fresh action
PROJECT_STATUS_COMPLETED_ADJUSTMENT = Decimal("-25.0")    # Completed project should deprioritize unless new emissions appear
