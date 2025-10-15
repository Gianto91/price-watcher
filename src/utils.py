# arriba:
from typing import Optional
import re

def parse_price_text(txt: str) -> Optional[float]:
    if not txt:
        return None
    m = re.search(r"S\/\s*([\d\.,]+)", txt)
    if not m:
        return None
    digits = m.group(1)
    if re.search(r"\d+\.\d{3}", digits) and re.search(r",\d{2}$", digits):
        digits = digits.replace(".", "").replace(",", ".")
    else:
        if digits.count(".") > 1 and "," not in digits:
            digits = digits.replace(".", "")
        digits = digits.replace(",", "")
    try:
        return float(digits)
    except:
        return None
