"""
URL Validation Utilities - SSRF Protection

Validates URLs and prevents Server-Side Request Forgery attacks.
"""

import ipaddress
from typing import Optional
from urllib.parse import urlparse


# Blocked metadata endpoints and internal IPs
BLOCKED_HOSTNAMES = {
    "169.254.169.254",  # AWS/GCP metadata
    "metadata.google.internal",  # GCP metadata
    "metadata",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "[::1]",  # IPv6 localhost
    "[0:0:0:0:0:0:0:1]",  # IPv6 localhost (full notation)
    "[::]",  # IPv6 unspecified address
}

# Private IP ranges (IPv4)
PRIVATE_IP_PREFIXES = [
    "10.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "192.168.",
    "127.",
    "169.254.",  # Link-local
]

# IPv6 private/reserved ranges (prefixes to block)
IPV6_BLOCKED_PREFIXES = [
    "::1",        # Loopback
    "::",         # Unspecified
    "fc",         # Unique local (fc00::/7)
    "fd",         # Unique local (fd00::/8)
    "fe80",       # Link-local
    "fe::",       # Link-local (alternative)
    "ff",         # Multicast
]

# Allowed schemes
ALLOWED_SCHEMES = {"http", "https"}

# Allowed ports (restrict to HTTP/HTTPS standard ports)
ALLOWED_PORTS = {80, 443, None}


def validate_url_safe(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate URL and prevent SSRF attacks.

    Args:
        url: The URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme not in ALLOWED_SCHEMES:
            return False, f"Invalid URL scheme. Only http and https are allowed."

        # Check hostname exists
        if not parsed.hostname:
            return False, "Invalid URL: no hostname"

        # Check for blocked hostnames
        hostname_lower = parsed.hostname.lower()
        if hostname_lower in BLOCKED_HOSTNAMES:
            return False, "Access to internal services is not allowed"

        # Check for private IP addresses (both IPv4 and IPv6)
        try:
            ip = ipaddress.ip_address(parsed.hostname)

            # Block private IPs (works for both IPv4 and IPv6)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False, "Access to private IP addresses is not allowed"

            # Block multicast
            if ip.is_multicast:
                return False, "Access to multicast addresses is not allowed"

        except ValueError:
            # Not an IP address, it's a hostname
            # Check if hostname starts with private IP prefix (IPv4)
            for prefix in PRIVATE_IP_PREFIXES:
                if hostname_lower.startswith(prefix):
                    return False, "Access to private networks is not allowed"

            # Check for IPv6 private prefixes in hostname
            for ipv6_prefix in IPV6_BLOCKED_PREFIXES:
                if hostname_lower.startswith(ipv6_prefix):
                    return False, "Access to private IPv6 addresses is not allowed"

        # Check port
        if parsed.port not in ALLOWED_PORTS:
            return False, f"Port {parsed.port} is not allowed. Only ports 80 and 443 are allowed."

        # Check for localhost variations in hostname
        if "localhost" in hostname_lower or hostname_lower.startswith("127."):
            return False, "Access to localhost is not allowed"

        return True, None

    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def normalize_url(url: str) -> str:
    """
    Normalize URL by adding https:// if missing.

    Args:
        url: The URL to normalize

    Returns:
        Normalized URL
    """
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def is_valid_url_format(url: str) -> bool:
    """
    Quick check if URL has valid format (basic validation).

    Args:
        url: The URL to check

    Returns:
        True if URL format is valid
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False
