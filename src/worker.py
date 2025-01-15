"""
Entrypoint for the backend worker
"""
import datadog  # noqa: F401, I001

from broker import broker as worker # noqa: F401