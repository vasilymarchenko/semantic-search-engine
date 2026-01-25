"""
URL fetching utilities for the ingestion pipeline.

Provides async HTTP fetching with proper error handling and user-agent.
"""

import re
from pathlib import Path
from typing import Literal

import aiohttp

from semantic_search.processors import RawDocument


async def fetch_url(
    url: str,
    timeout: int = 30,
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
) -> RawDocument:
    """
    Fetch HTML content from a URL.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        user_agent: User-Agent header to use

    Returns:
        RawDocument with HTML content

    Raises:
        aiohttp.ClientError: On network errors
        asyncio.TimeoutError: On timeout
    """
    headers = {"User-Agent": user_agent}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            response.raise_for_status()

            # Get content as text
            html_content = await response.text()

            # Extract some metadata from response
            metadata = {
                "status_code": response.status,
                "content_type": response.headers.get("Content-Type", ""),
                "content_length": len(html_content),
            }

            return RawDocument(
                content=html_content,
                source_type="web",
                url=url,
                metadata=metadata,
            )


def detect_source_type(source: str) -> Literal["url", "file"]:
    """
    Detect if source is a URL or file path.

    Args:
        source: URL or file path

    Returns:
        "url" or "file"
    """
    # Simple URL detection
    if source.startswith(("http://", "https://")):
        return "url"
    return "file"


def detect_file_format(file_path: Path) -> Literal["html", "markdown", "pdf", "unknown"]:
    """
    Detect file format from extension and content.

    Args:
        file_path: Path to file

    Returns:
        Format type: "html", "markdown", "pdf", "unknown"
    """
    suffix = file_path.suffix.lower()

    format_map = {
        ".html": "html",
        ".htm": "html",
        ".md": "markdown",
        ".markdown": "markdown",
        ".pdf": "pdf",
    }

    return format_map.get(suffix, "unknown")


def generate_output_name(source: str, source_type: Literal["url", "file"]) -> str:
    """
    Generate a clean output filename from source.

    Args:
        source: URL or file path
        source_type: Type of source

    Returns:
        Clean filename without extension
    """
    if source_type == "url":
        # Extract domain and path
        # https://example.com/blog/my-post -> example-com-blog-my-post
        clean = re.sub(r"^https?://", "", source)
        clean = re.sub(r"[^\w\-/]", "-", clean)
        clean = clean.strip("-").replace("/", "-")
        # Limit length
        if len(clean) > 80:
            clean = clean[:80]
        return clean or "document"
    else:
        # Use filename without extension
        return Path(source).stem
