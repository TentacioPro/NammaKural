from urllib.error import HTTPError

from ops import audit_civic_catalog as audit


def test_catalog_separates_visible_controls_and_public_inventory():
    catalog = audit.load_catalog()
    districts = catalog["districts"]
    assert len({district["website"] for district in districts}) == 38
    routes = {route["id"]: route for route in catalog["routes"]}
    assert routes["gcc_pgrs"]["coverage"] == "visible_controls"
    assert routes["gcc_erp_legacy"]["fields"] != routes["gcc_pgrs"]["fields"]
    assert routes["esevai_services"]["coverage"] == "inventory_only"


def test_audit_reports_contact_and_field_changes_without_retaining_values():
    source = {"kind": "visible_form", "expected_text": ["description"]}
    old = audit.inspect_markup(
        '<p>Description</p><textarea maxlength="10"></textarea><input type="hidden" value="private-value">'
        '<a href="mailto:one@example.invalid">Contact</a>', source,
    )
    new = audit.inspect_markup(
        '<p>Description</p><textarea maxlength="25"></textarea><input type="hidden" value="private-value">'
        '<a href="mailto:two@example.invalid">Contact</a>', source,
    )
    assert old["static_controls"] == 1
    assert "private-value" not in str(new) and "example.invalid" not in str(new)
    assert audit.compare({"sample": new}, {"sample": old})[0]["signals"] == ["fields", "contacts"]


def test_audit_checks_robots_and_does_not_follow_redirects(monkeypatch):
    origin = "https://example.invalid"
    requested = []

    def fetch(url):
        requested.append(url)
        if url.endswith("/robots.txt"):
            return "User-agent: *\nDisallow: /gated"
        raise HTTPError(url, 302, "", {}, None)

    monkeypatch.setattr(audit, "fetch_text", fetch)
    results = audit._audit_host(origin, [
        ("gated", {"url": origin + "/gated"}),
        ("public", {"url": origin + "/public"}),
    ])
    assert results["gated"]["status"] == "robots_disallowed"
    assert results["public"]["status"] == "redirect_review"
    assert requested == [origin + "/robots.txt", origin + "/public"]


def test_unreachable_host_returns_review_status(monkeypatch):
    def unavailable(url):
        raise ConnectionResetError

    monkeypatch.setattr(audit, "fetch_text", unavailable)
    result = audit._audit_host("https://example.invalid", [("test", {})])
    assert result["test"]["status"] == "robots_unavailable"
