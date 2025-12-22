"""Helper utilities for MFA notifications."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import Request

from apps.users.domain import User


def extract_request_metadata(request: Optional[Request] = None) -> dict:
    """Extract IP address and user-agent from request for security emails."""
    metadata = {
        "ip_address": "Unknown",
        "user_agent": "Unknown",
        "timestamp": datetime.now(timezone.utc),
    }

    if request:
        if request.client:
            metadata["ip_address"] = request.client.host
        metadata["user_agent"] = request.headers.get("user-agent", "Unknown")

    return metadata


def get_user_language(user: User) -> str:
    """Get user's preferred language for emails, default to English."""
    language = getattr(user, "language", None) or "en"
    return str(language) if language else "en"


def get_user_display_name(user: User) -> str:
    """Get user's first name, fallback to generic greeting."""
    first_name = getattr(user, "first_name", None)
    return first_name if first_name else "there"


def get_user_email(user: User) -> str:
    """Get user's email address (encrypted or regular)."""
    email_encrypted = getattr(user, "email_encrypted", None)
    email = getattr(user, "email", None)

    user_email = email_encrypted or email

    if not user_email:
        raise ValueError(f"No email found for user_id={user.id}")

    return user_email
