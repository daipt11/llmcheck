"""Shared helpers used across the CLI, checker, and web layers."""


def mask_key(api_key: str) -> str:
    """Return a display-safe, masked form of an API key."""
    if not api_key:
        return "-"
    if len(api_key) > 8:
        return f"{api_key[:4]}...{api_key[-4:]}"
    return "***"
