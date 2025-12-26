"""Data models for the reconciliation app."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class MatchStatus(Enum):
    """Status of a reconciliation match."""
    EXACT_MATCH = "exact_match"
    MATCH_WITH_DATE_NOTE = "match_with_date_note"
    AMOUNT_VARIANCE = "amount_variance"
    MISSING_IN_B = "missing_in_b"
    MISSING_IN_A = "missing_in_a"


@dataclass
class ReconConfig:
    """Configuration for a reconciliation run."""
    source_a_path: str
    source_b_path: str
    output_dir: str
    match_key: str
    amount_tolerance: float = 0.0
    # Column mappings for dynamic column selection
    date_col_a: str = "date"
    date_col_b: str = "date"
    amount_col_a: str = "amount"
    amount_col_b: str = "amount"
    description_col_a: Optional[str] = None
    description_col_b: Optional[str] = None


@dataclass
class ReconSummary:
    """Summary counts for reconciliation results."""
    exact_matches: int = 0
    matches_with_date_note: int = 0
    amount_variances: int = 0
    missing_in_b: int = 0
    missing_in_a: int = 0
    
    @property
    def total_matched(self) -> int:
        """Total records considered matched (exact + date note)."""
        return self.exact_matches + self.matches_with_date_note
    
    @property
    def total_unmatched(self) -> int:
        """Total records with issues."""
        return self.amount_variances + self.missing_in_b + self.missing_in_a


@dataclass
class ReconResult:
    """Container for all reconciliation outputs."""
    config: ReconConfig
    summary: ReconSummary
    # Results are stored in DuckDB tables, accessed via engine
    exact_matches_table: str = "exact_matches"
    date_note_table: str = "matches_with_date_note"
    amount_variance_table: str = "amount_variances"
    missing_in_b_table: str = "missing_in_b"
    missing_in_a_table: str = "missing_in_a"
