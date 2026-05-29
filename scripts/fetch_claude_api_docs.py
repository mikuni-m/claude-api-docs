#!/usr/bin/env python3
"""
Claude API documentation fetcher for platform.claude.com/docs
"""

import requests
import time
from pathlib import Path
from typing import List, Tuple, Set
import logging
from datetime import datetime
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import json
import hashlib
import os
import re
import random

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

BASE_URL = "https://platform.claude.com"
SITEMAP_URLS = [
    "https://platform.claude.com/docs/sitemap.xml",
    "https://platform.claude.com/docs/sitemap_index.xml",
]
MANIFEST_FILE = "docs_manifest.json"

HEADERS = {
    'User-Agent': 'Claude-API-Docs-Fetcher/1.0',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0'
}

MAX_RETRIES = 3
RETRY_DELAY = 2
MAX_RETRY_DELAY = 30
RATE_LIMIT_DELAY = 0.5

# Sections to include (English content, excluding API reference)
# Note: actual sitemap sections are: agents-and-tools, api, build-with-claude,
#       get-started, intro, manage-claude, managed-agents, test-and-evaluate
INCLUDED_SECTIONS = [
    '/docs/en/get-started',
    '/docs/en/intro',
    '/docs/en/build-with-claude/',
    '/docs/en/agents-and-tools/',
    '/docs/en/managed-agents/',
    '/docs/en/manage-claude/',
    '/docs/en/test-and-evaluate/',
]

# Specific paths to always include even if they don't match above patterns
ALWAYS_INCLUDE = [
    '/docs/en/get-started',
    '/docs/en/intro',
]

# Sub-paths to exclude within included sections
EXCLUDED_SUBPATHS = [
    '/docs/en/api/',
]


def load_manifest(docs_dir: Path) -> dict:
    manifest_path = docs_dir / MANIFEST_FILE
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            if "files" not in manifest:
                manifest["files"] = {}
            return manifest
        except Exception as e:
            logger.warning(f"Failed to load manifest: {e}")
    return {"files": {}, "last_updated": None}


def save_manifest(docs_dir: Path, manifest: dict) -> None:
    manifest_path = docs_dir / MANIFEST_FILE
    manifest["last_updated"] = datetime.now().isoformat()

    github_repo = os.environ.get('GITHUB_REPOSITORY', 'mikuni-m/claude-api-docs')
    github_ref = os.environ.get('GITHUB_REF_NAME', 'main')

    if not re.match(r'^[\w.-]+/[\w.-]+$', github_repo):
        logger.warning(f"Invalid repository format: {github_repo}, using default")
        github_repo = 'mikuni-m/claude-api-docs'

    if not re.match(r'^[\w.-]+$', github_ref):
        logger.warning(f"Invalid ref format: {github_ref}, using default")
        github_ref = 'main'

    manifest["base_url"] = f"https://raw.githubusercontent.com/{github_repo}/{github_ref}/docs/"
    manifest["github_repository"] = github_repo
    manifest["github_ref"] = github_ref
    manifest["description"] = "Claude API documentation manifest. Keys are filenames, append to base_url for full URL."
    manifest_path.write_text(json.dumps(manifest, indent=2))


def url_to_safe_filename(url_path: str) -> str:
    """Convert a URL path like /docs/en/build-with-claude/prompt-caching to a safe filename."""
    prefix = '/docs/en/'
    if prefix in url_path:
        path = url_path.split(prefix)[-1]
    else:
        path = url_path.lstrip('/')

    # Remove trailing slash
    path = path.rstrip('/')

    if '/' not in path:
        return path + '.md' if not path.endswith('.md') else path

    # Replace slashes with double underscores
    safe_name = path.replace('/', '__')
    if not safe_name.endswith('.md'):
        safe_name += '.md'
    return safe_name


def is_included_page(url_path: str) -> bool:
    """Check if a URL path should be included based on section filters."""
    # Must be English
    if '/docs/en/' not in url_path:
        return False

    # Check exclusions first
    for excluded in EXCLUDED_SUBPATHS:
        if excluded in url_path:
            return False

    # Check always-include list
    for always in ALWAYS_INCLUDE:
        if url_path == always or url_path.startswith(always + '/'):
            return True

    # Check included sections
    for section in INCLUDED_SECTIONS:
        if url_path == section.rstrip('/') or url_path.startswith(section.rstrip('/') + '/'):
            return True

    return False


def discover_pages_from_sitemap(session: requests.Session) -> Tuple[List[str], str]:
    """
    Try to discover pages from sitemap. Returns (pages, base_url).
    Falls back to llms.txt if sitemap fails.
    """
    for sitemap_url in SITEMAP_URLS:
        try:
            logger.info(f"Trying sitemap: {sitemap_url}")
            response = session.get(sitemap_url, headers=HEADERS, timeout=30)
            if response.status_code != 200:
                continue

            try:
                parser = ET.XMLParser(forbid_dtd=True, forbid_entities=True, forbid_external=True)
                root = ET.fromstring(response.content, parser=parser)
            except TypeError:
                root = ET.fromstring(response.content)

            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = []
            for url_elem in root.findall('.//ns:url', namespace):
                loc = url_elem.find('ns:loc', namespace)
                if loc is not None and loc.text:
                    urls.append(loc.text)

            if not urls:
                for loc in root.findall('.//loc'):
                    if loc.text:
                        urls.append(loc.text)

            logger.info(f"Found {len(urls)} URLs in sitemap")
            pages = []
            for url in urls:
                parsed = urlparse(url)
                path = parsed.path.rstrip('/')
                if is_included_page(path):
                    pages.append(path)

            pages = sorted(list(set(pages)))
            logger.info(f"Filtered to {len(pages)} included pages")
            return pages, BASE_URL

        except Exception as e:
            logger.warning(f"Sitemap {sitemap_url} failed: {e}")
            continue

    # Fallback: use llms.txt to discover pages
    logger.info("Sitemap not available, trying llms.txt...")
    return discover_pages_from_llms_txt(session)


def discover_pages_from_llms_txt(session: requests.Session) -> Tuple[List[str], str]:
    """Parse llms.txt to get page list."""
    try:
        response = session.get(f"{BASE_URL}/docs/llms.txt", headers=HEADERS, timeout=30)
        response.raise_for_status()
        content = response.text

        pages = []
        for line in content.splitlines():
            line = line.strip()
            # Lines look like: - [Title](https://platform.claude.com/docs/en/...)
            match = re.search(r'https://platform\.claude\.com(/docs/en/[^\s\)]+)', line)
            if match:
                path = match.group(1).rstrip('/')
                if is_included_page(path):
                    pages.append(path)

        pages = sorted(list(set(pages)))
        logger.info(f"Discovered {len(pages)} pages from llms.txt")
        return pages, BASE_URL

    except Exception as e:
        logger.error(f"llms.txt also failed: {e}")
        return get_fallback_pages(), BASE_URL


def get_fallback_pages() -> List[str]:
    """Hardcoded fallback list of core pages."""
    return [
        "/docs/en/get-started",
        "/docs/en/about-claude/models/overview",
        "/docs/en/about-claude/pricing",
        "/docs/en/build-with-claude/overview",
        "/docs/en/build-with-claude/prompt-caching",
        "/docs/en/build-with-claude/batch",
        "/docs/en/build-with-claude/extended-thinking",
        "/docs/en/build-with-claude/streaming",
        "/docs/en/build-with-claude/token-counting",
        "/docs/en/build-with-claude/files",
        "/docs/en/build-with-claude/citations",
        "/docs/en/agents-and-tools/overview",
        "/docs/en/agents-and-tools/tool-use/overview",
        "/docs/en/agents-and-tools/computer-use",
        "/docs/en/agents-and-tools/web-search",
        "/docs/en/mcp/overview",
        "/docs/en/managed-agents/overview",
        "/docs/en/admin/authentication",
    ]


def validate_markdown_content(content: str, filename: str) -> None:
    if not content or content.startswith('<!DOCTYPE') or '<html' in content[:100]:
        raise ValueError("Received HTML instead of markdown")

    if len(content.strip()) < 50:
        raise ValueError(f"Content too short ({len(content)} bytes)")

    lines = content.split('\n')
    markdown_indicators = ['# ', '## ', '### ', '```', '- ', '* ', '1. ', '[', '**', '_', '> ']
    indicator_count = sum(
        1 for line in lines[:50]
        if any(line.strip().startswith(ind) or ind in line for ind in markdown_indicators)
    )

    if indicator_count < 3:
        raise ValueError(f"Content doesn't appear to be markdown ({indicator_count} indicators found)")


def fetch_markdown_content(path: str, session: requests.Session) -> Tuple[str, str]:
    markdown_url = f"{BASE_URL}{path}.md"
    filename = url_to_safe_filename(path)

    logger.info(f"Fetching: {markdown_url} -> {filename}")

    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(markdown_url, headers=HEADERS, timeout=30, allow_redirects=True)

            if response.status_code == 429:
                wait_time = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            content = response.text
            validate_markdown_content(content, filename)

            logger.info(f"Fetched {filename} ({len(content)} bytes)")
            return filename, content

        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {filename}: {e}")
            if attempt < MAX_RETRIES - 1:
                delay = min(RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                jittered_delay = delay * random.uniform(0.5, 1.0)
                logger.info(f"Retrying in {jittered_delay:.1f} seconds...")
                time.sleep(jittered_delay)
            else:
                raise Exception(f"Failed to fetch {filename} after {MAX_RETRIES} attempts: {e}")

        except ValueError as e:
            logger.error(f"Content validation failed for {filename}: {e}")
            raise


def content_has_changed(content: str, old_hash: str) -> bool:
    new_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    return new_hash != old_hash


def save_markdown_file(docs_dir: Path, filename: str, content: str) -> str:
    file_path = docs_dir / filename
    file_path.write_text(content, encoding='utf-8')
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def cleanup_old_files(docs_dir: Path, current_files: Set[str], manifest: dict) -> None:
    previous_files = set(manifest.get("files", {}).keys())
    for filename in previous_files - current_files:
        if filename == MANIFEST_FILE:
            continue
        file_path = docs_dir / filename
        if file_path.exists():
            logger.info(f"Removing obsolete file: {filename}")
            file_path.unlink()


def main():
    start_time = datetime.now()
    logger.info("Starting Claude API documentation fetch")

    docs_dir = Path(__file__).parent.parent / 'docs'
    docs_dir.mkdir(exist_ok=True)
    logger.info(f"Output directory: {docs_dir}")

    manifest = load_manifest(docs_dir)
    successful = 0
    failed = 0
    failed_pages = []
    fetched_files = set()
    new_manifest = {"files": {}}

    with requests.Session() as session:
        pages, base_url = discover_pages_from_sitemap(session)

        if not pages:
            logger.error("No documentation pages discovered!")
            sys.exit(1)

        for i, page_path in enumerate(pages, 1):
            logger.info(f"Processing {i}/{len(pages)}: {page_path}")

            try:
                filename, content = fetch_markdown_content(page_path, session)

                old_hash = manifest.get("files", {}).get(filename, {}).get("hash", "")
                old_entry = manifest.get("files", {}).get(filename, {})

                if content_has_changed(content, old_hash):
                    content_hash = save_markdown_file(docs_dir, filename, content)
                    last_updated = datetime.now().isoformat()
                    logger.info(f"Updated: {filename}")
                else:
                    content_hash = old_hash
                    last_updated = old_entry.get("last_updated", datetime.now().isoformat())
                    logger.info(f"Unchanged: {filename}")

                new_manifest["files"][filename] = {
                    "original_url": f"{base_url}{page_path}",
                    "original_md_url": f"{base_url}{page_path}.md",
                    "hash": content_hash,
                    "last_updated": last_updated
                }

                fetched_files.add(filename)
                successful += 1

                if i < len(pages):
                    time.sleep(RATE_LIMIT_DELAY)

            except Exception as e:
                logger.error(f"Failed to process {page_path}: {e}")
                failed += 1
                failed_pages.append(page_path)

    cleanup_old_files(docs_dir, fetched_files, manifest)

    new_manifest["fetch_metadata"] = {
        "last_fetch_completed": datetime.now().isoformat(),
        "fetch_duration_seconds": (datetime.now() - start_time).total_seconds(),
        "total_pages_discovered": len(pages),
        "pages_fetched_successfully": successful,
        "pages_failed": failed,
        "failed_pages": failed_pages,
        "source_url": BASE_URL,
        "fetch_tool_version": "1.0"
    }

    save_manifest(docs_dir, new_manifest)

    duration = datetime.now() - start_time
    logger.info("=" * 50)
    logger.info(f"Fetch completed in {duration}")
    logger.info(f"Discovered pages: {len(pages)}")
    logger.info(f"Successful: {successful}/{len(pages)}")
    logger.info(f"Failed: {failed}")

    if failed_pages:
        logger.warning("Failed pages:")
        for page in failed_pages:
            logger.warning(f"  - {page}")
        if successful == 0:
            logger.error("No pages were fetched successfully!")
            sys.exit(1)
    else:
        logger.info("All pages fetched successfully!")


if __name__ == "__main__":
    main()
