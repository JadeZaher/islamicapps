"""
Candidate B - Regex with noun phrase awareness
"""
import re

def extract_branches(text_ar: str) -> list[list[str]]:
    """
    Split with basic noun phrase handling
    """
    # Match segments between ح markers
    pattern = r'(?:ح\s+و?(?:حدثنا|حدثني|أخبرنا|أنبأنا|ثنا|نا))(.*?)(?=ح\s+و?(?:حدثنا|حدثني|أخبرنا|أنبأنا|ثنا|نا)|$)'
    segments = re.findall(pattern, text_ar)
    return []