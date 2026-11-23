"""Shared exception types."""

from __future__ import annotations


class DataNotVerifiedError(NotImplementedError):
    """Raised when a feature depends on a data table that is not verified yet.

    Legacy-font mappings and Bikram Sambat month lengths cannot be derived by
    formula. Until a table has been checked against a trusted source and
    marked ``"status": "verified"``, the feature refuses to guess.
    """
