def check_input_safety(text: str, max_length: int = 1000) -> tuple[bool, str]:
    """
    Returns (is_safe, reason).
    Checks for length and basic prompt injection attempts.
    """
    if not text:
        return False, "Input is empty."

    # 1. Length Guard
    if len(text) > max_length:
        return False, f"Input exceeds maximum length of {max_length} characters."

    # 2. Prompt Injection Guard (Basic)
    # Checks for common attempts to override system instructions.
    forbidden_phrases = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "system prompt",
        "you are now",
        "override",
    ]
    
    lower_text = text.lower()
    for phrase in forbidden_phrases:
        if phrase in lower_text:
            return False, f"Potential safety violation detected: '{phrase}'"

    return True, ""