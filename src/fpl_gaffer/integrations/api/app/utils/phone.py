from typing import Optional


def normalize_phone_number(number: Optional[str]) -> str:
    """Normalize phone inputs for exact WhatsApp/user lookup matching."""
    if not number:
        return ""

    cleaned = number.removeprefix("whatsapp:").strip()
    for char in (" ", "-", "(", ")"):
        cleaned = cleaned.replace(char, "")

    if cleaned.startswith("00"):
        cleaned = f"+{cleaned[2:]}"

    return cleaned
