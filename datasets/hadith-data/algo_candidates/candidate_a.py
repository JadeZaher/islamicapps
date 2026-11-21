"""
Candidate A - Simple regex-based ح split
"""
import re

def extract_branches(text_ar: str) -> list[list[str]]:
    """
    Split text on ح markers
    """
    # Split on ح followed by verb
    segments = re.split(r'ح\s+و?(?:حدثنا|حدثني|أخبرنا|أنبأنا|ثنا|نا)', text_ar)
    return []