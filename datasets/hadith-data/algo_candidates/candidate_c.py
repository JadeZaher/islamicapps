"""
Candidate C - Nested matn handling
"""
import re
from typing import List

def _find_quoted_matn(text: str) -> List[tuple[int, int]]:
    """
    Find quoted matn sections to avoid false splits
    Returns list of (start, end) indices of quoted matn
    """
    return []

def extract_branches(text_ar: str) -> list[list[str]]:
    # First identify quoted matn to protect
    protected_ranges = _find_quoted_matn(text_ar)
    # Then split on unprotected ح markers
    return []