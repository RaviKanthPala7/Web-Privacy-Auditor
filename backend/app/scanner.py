import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from app.models import (
    AuditReport,
    Category,
    CategorySummary,
    CookieFinding,
    ScriptFinding,
    ThirdPartyRequest,
    TrackerMatch,
)

RULES_PATH = Path(__file__).parent / "rules" / "trackers.json"
DEFAULT_TIMEOUT_MS = 60_000


def _load_rules() -> list[dict]:
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _domain(url: str) -> str:
    """Extract hostname from a URL, e.g. https://a.b.com/x -> a.b.com"""
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def _is_third_party(request_domain: str, page_domain: str) -> bool:
    """True if request goes to a different site than the page you audited."""
    if not request_domain or not page_domain:
        return False
    return request_domain != page_domain and not request_domain.endswith("." + page_domain)


def _match_trackers(urls: list[str], rules: list[dict]) -> list[TrackerMatch]:
    """If any URL contains a pattern from trackers.json, record a match."""
    seen: set[tuple[str, str]] = set()
    matches: list[TrackerMatch] = []

    for url in urls:
        lower = url.lower()
        for rule in rules:
            for pattern in rule["patterns"]:
                if pattern.lower() in lower:
                    key = (rule["name"], url)
                    if key in seen:
                        break
                    seen.add(key)
                    try:
                        category = Category(rule["category"])
                    except ValueError:
                        category = Category.UNKNOWN
                    matches.append(
                        TrackerMatch(
                            name=rule["name"],
                            category=category,
                            matched_url=url,
                            why_it_matters=rule["why_it_matters"],
                        )
                    )
                    break

    return matches


def _build_summary(trackers: list[TrackerMatch]) -> list[CategorySummary]:
    counts: dict[Category, int] = {}
    for t in trackers:
        counts[t.category] = counts.get(t.category, 0) + 1
    return [
        CategorySummary(category=cat, count=n)
        for cat, n in sorted(counts.items(), key=lambda x: x[0].value)
    ]


def _run_audit_sync(url: str, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> AuditReport:
    """
    Sync Playwright scan (runs in a worker thread on Windows so uvicorn + /audit work).
  1. Open page in Chromium
  2. Collect network requests, cookies, scripts
  3. Match trackers.json patterns
  4. Return AuditReport
    """
    rules = _load_rules()
    started = time.perf_counter()
    scanned_at = datetime.now(timezone.utc).isoformat()
    page_domain = _domain(url)

    network_hits: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def on_request(request):
            req_url = request.url
            req_domain = _domain(req_url)
            if _is_third_party(req_domain, page_domain):
                network_hits.append(
                    {
                        "url": req_url,
                        "domain": req_domain,
                        "resource_type": request.resource_type,
                    }
                )

        page.on("request", on_request)

        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        except Exception:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        page.wait_for_timeout(2000)

        page_title = page.title()
        cookies_raw = context.cookies()
        scripts_raw = page.eval_on_selector_all(
            "script[src]",
            "els => els.map(s => ({ src: s.src, async: s.async, defer: s.defer }))",
        )

        browser.close()

    duration_ms = int((time.perf_counter() - started) * 1000)
    all_urls = [h["url"] for h in network_hits] + [s["src"] for s in scripts_raw]
    trackers = _match_trackers(all_urls, rules)

    third_parties: list[ThirdPartyRequest] = []
    seen_domains: set[str] = set()
    for hit in network_hits:
        if hit["domain"] in seen_domains:
            continue
        seen_domains.add(hit["domain"])
        third_parties.append(
            ThirdPartyRequest(
                domain=hit["domain"],
                url=hit["url"],
                resource_type=hit["resource_type"],
            )
        )

    cookies = [
        CookieFinding(
            name=c.get("name", ""),
            domain=c.get("domain", ""),
            path=c.get("path", "/"),
            secure=c.get("secure", False),
            http_only=c.get("httpOnly", False),
            same_site=c.get("sameSite"),
        )
        for c in cookies_raw
    ]

    scripts: list[ScriptFinding] = []
    seen_script_domains: set[str] = set()
    for s in scripts_raw:
        src = s.get("src", "")
        dom = _domain(src)
        if not _is_third_party(dom, page_domain) or dom in seen_script_domains:
            continue
        seen_script_domains.add(dom)
        scripts.append(
            ScriptFinding(
                src=src,
                domain=dom,
                async_attr=bool(s.get("async")),
                defer_attr=bool(s.get("defer")),
            )
        )

    notes: list[str] = []
    if any(t.category == Category.ADVERTISING for t in trackers):
        notes.append("Advertising trackers detected — review consent and privacy policy.")
    if len(third_parties) > 10:
        notes.append(f"Many third parties ({len(third_parties)}) — consider a tag governance review.")

    return AuditReport(
        url=url,
        scanned_at=scanned_at,
        duration_ms=duration_ms,
        summary=_build_summary(trackers),
        trackers=trackers,
        third_parties=third_parties[:50],
        cookies=cookies[:100],
        scripts=scripts[:50],
        page_title=page_title,
        notes=notes,
    )


async def run_audit(url: str, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> AuditReport:
    """Async wrapper — runs sync Playwright in a thread (fixes Windows + uvicorn)."""
    return await asyncio.to_thread(_run_audit_sync, url, timeout_ms)
