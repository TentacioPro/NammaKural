"""Check public civic source pages for changes without touching submission flows."""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "civic" / "tn_public_catalog.json"
DEFAULT_SNAPSHOT = ROOT / "scratch" / "civic-audit" / "current.json"
AGENT = "NammaKuralCatalogAudit"
LIMIT = 2_000_000
PROBE_TIMEOUT = 8
CONTROL_ATTRIBUTES = ("type", "name", "id", "required", "aria-required", "maxlength",
                      "minlength", "min", "max", "pattern", "accept", "placeholder")
IGNORED = {"script", "style", "template"}
EMAIL = re.compile(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,}", re.I)
PHONE = re.compile(r"(?<!\w)(?:\+91[\s-]*)?(?:\d[\s-]*){10,11}(?!\w)")


class PublicMarkup(HTMLParser):
    """Extract comparison signals from returned markup. Hidden field values are ignored."""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.controls: list[dict] = []
        self.options: list[str] = []
        self.contact_links: set[str] = set()
        self._skip: str | None = None
        self._option_text: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if self._skip:
            return
        if tag in IGNORED:
            self._skip = tag
            return
        attributes = dict(attrs)
        if tag in {"input", "textarea", "select"} and attributes.get("type") != "hidden":
            self.controls.append({"tag": tag, **{key: attributes[key] for key in CONTROL_ATTRIBUTES if key in attributes}})
        if tag == "option":
            self._option_text = []
        href = attributes.get("href") or ""
        if tag == "a":
            try:
                link = urlsplit(href)
            except ValueError:
                return
            if link.scheme in {"mailto", "tel", "whatsapp"} or link.hostname in {
                "wa.me", "api.whatsapp.com", "www.whatsapp.com", "whatsapp.com",
            }:
                self.contact_links.add(href.strip().casefold().split("?subject=", 1)[0])

    def handle_endtag(self, tag):
        if tag == self._skip:
            self._skip = None
        if tag == "option" and self._option_text is not None:
            self.options.append(" ".join(self._option_text))
            self._option_text = None

    def handle_data(self, data):
        if not self._skip and (normalized := " ".join(data.split())):
            self.parts.append(normalized)
            if self._option_text is not None:
                self._option_text.append(normalized)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def inspect_markup(body: str, source: dict) -> dict:
    parser = PublicMarkup()
    parser.feed(body)
    visible = " ".join(parser.parts).casefold()
    missing = [marker for marker in source.get("expected_text", []) if marker.casefold() not in visible]
    emails = {match.group().casefold() for match in EMAIL.finditer(visible)}
    phones = {re.sub(r"\D", "", match.group()) for match in PHONE.finditer(visible)}
    return {
        "status": ("markers_missing" if missing else "public_document")
        if source["kind"] != "app_shell" else "app_shell_only",
        "missing_markers": missing,
        "static_controls": len(parser.controls),
        "static_options": len(parser.options),
        "fingerprints": {
            "fields": digest([parser.controls, parser.options]),
            "contacts": digest([sorted(emails), sorted(phones), sorted(parser.contact_links)]),
            "visible_text": digest(visible),
        },
    }


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_text(url: str) -> str:
    opener = build_opener(NoRedirect)
    request = Request(url, headers={"User-Agent": f"{AGENT}/1.0"}, method="GET")
    with opener.open(request, timeout=PROBE_TIMEOUT) as response:
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
            raise ValueError("unhandled document type")
        body = response.read(LIMIT + 1)
        if len(body) > LIMIT:
            raise ValueError("document exceeds byte limit")
        return body.decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def _audit_host(origin: str, sources: list[tuple[str, dict]]) -> dict[str, dict]:
    policy = RobotFileParser()
    try:
        policy.parse(fetch_text(f"{origin}/robots.txt").splitlines())
    except HTTPError as error:
        if error.code not in (404, 410):
            return {id_: {"status": "robots_unavailable", "http_status": error.code} for id_, _ in sources}
        policy.parse([])
    except (OSError, ValueError, LookupError) as error:
        return {id_: {"status": "robots_unavailable", "error_type": type(error).__name__} for id_, _ in sources}

    results = {}
    for id_, source in sources:
        if not policy.can_fetch(AGENT, source["url"]):
            results[id_] = {"status": "robots_disallowed"}
            continue
        try:
            results[id_] = inspect_markup(fetch_text(source["url"]), source)
        except HTTPError as error:
            state = "redirect_review" if 300 <= error.code < 400 else "unavailable"
            results[id_] = {"status": state, "http_status": error.code}
        except (OSError, ValueError, LookupError) as error:
            results[id_] = {"status": "unavailable", "error_type": type(error).__name__}
    return results


def load_catalog(path: Path = CATALOG) -> dict:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    sources = catalog["sources"]
    for id_, source in sources.items():
        url = urlsplit(source["url"])
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.port is not None or url.query or url.fragment):
            raise ValueError(f"{id_}: provide an HTTPS public source URL without parameters")
    route_ids = set()
    for route in catalog["routes"]:
        if route["id"] in route_ids or not route["sources"] or not set(route["sources"]) <= sources.keys():
            raise ValueError(f"Invalid or duplicate route {route['id']}")
        route_ids.add(route["id"])
        fields = route.get("fields", [])
        keys = {field["key"] for field in fields}
        if len(keys) != len(fields):
            raise ValueError(f"{route['id']}: duplicate field keys")
        if any("depends_on" in field and field["depends_on"] not in keys for field in fields):
            raise ValueError(f"{route['id']}: missing prerequisite field")
        if any(field.get("type") == "verification" and field.get("handling") != "portal" for field in fields):
            raise ValueError(f"{route['id']}: verification fields must stay with the portal")
    return catalog


def compare(current: dict, baseline: dict) -> list[dict]:
    changes = []
    for key, result in current.items():
        previous = baseline.get(key)
        if not previous:
            changes.append({"source": key, "signals": ["no_baseline"], "status": result["status"]})
            continue
        flags = []
        if (previous["status"], previous.get("http_status")) != (result["status"], result.get("http_status")):
            flags.append("availability")
        if previous.get("missing_markers") != result.get("missing_markers"):
            flags.append("expected_text")
        if "fingerprints" in previous and "fingerprints" in result:
            flags.extend(name for name, value in result["fingerprints"].items() if previous["fingerprints"].get(name) != value)
        if flags:
            changes.append({"source": key, "signals": flags, "status": result["status"]})
    return changes


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source", action="append", help="Audit only this registered source. May be repeated.")
    cli.add_argument("--validate", action="store_true", help="Validate the register without network access.")
    cli.add_argument("--baseline", type=Path, help="Compare with a previously reviewed audit snapshot.")
    cli.add_argument("--output", type=Path, default=DEFAULT_SNAPSHOT)
    args = cli.parse_args()
    catalog = load_catalog()
    sources = catalog["sources"]
    if args.validate:
        print(f"Valid register: {len(catalog['routes'])} routes, {len(sources)} monitored sources, {len(catalog['districts'])} districts")
        return 0
    ids = list(dict.fromkeys(args.source or sources))
    if unknown := set(ids) - sources.keys():
        cli.error(f"Unknown source IDs: {', '.join(sorted(unknown))}")
    host_groups = defaultdict(list)
    for key in ids:
        origin = f"https://{urlsplit(sources[key]['url']).netloc}"
        host_groups[origin].append((key, sources[key]))
    with ThreadPoolExecutor(max_workers=4) as executor:
        batches = executor.map(lambda group: _audit_host(*group), host_groups.items())
        observations = {key: value for batch in batches for key, value in batch.items()}
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))["sources"] if args.baseline else {}
    snapshot = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": observations,
        "review_queue": compare(observations, baseline),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for key, observation in observations.items():
        print(f"{key}: {observation['status']}")
    print(f"Review items: {len(snapshot['review_queue'])} · {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
