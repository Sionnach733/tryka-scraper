"""Parse HTML pages from tryka.r.mikatiming.com."""

import re
from bs4 import BeautifulSoup



def gender_from_division(division: str) -> str | None:
    upper = division.upper()
    # Check mixed / combined first to avoid false matches
    if "MIXED" in upper or ("MENS" in upper and "WOMENS" in upper):
        return "X"
    if "MENS" in upper or "MEN" in upper or "BOYS" in upper:
        return "M"
    if "WOMENS" in upper or "WOMEN" in upper or "GIRLS" in upper:
        return "W"
    return None


def normalize_member_name(name: str) -> str:
    """Convert 'Surname, Firstname (COUNTRY)' to 'Firstname Surname (COUNTRY)' with title case."""
    m = re.match(r"^(.+?),\s*(.+?)(\s*\(.*\))$", name)
    if m:
        surname, firstname, country = m.group(1), m.group(2), m.group(3)
        return f"{firstname.title()} {surname.title()}{country}"
    # No country code: "Surname, Firstname"
    m = re.match(r"^(.+?),\s*(.+)$", name)
    if m:
        surname, firstname = m.group(1).strip(), m.group(2).strip()
        return f"{firstname.title()} {surname.title()}"
    return name


def _text(tag) -> str:
    """Strip HTML and return clean text."""
    return tag.get_text(strip=True).replace("\u2013", "-").replace("\xa0", " ")


def _parse_int(value: str) -> int | None:
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return None


def parse_list_page(html: str) -> tuple[list[str], int]:
    """
    Parse a results list page.
    Returns (list_of_(idp, detail_event_id)_tuples, total_pages).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extract (idp, detail_event_id, search_event_id) from each result link.
    # The detail URL's event= param may differ from the list page's event= param,
    # and search_event= is required for the detail page to return data.
    entries: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        idp_m = re.search(r"[?&]idp=([A-Z0-9]+)", href)
        event_m = re.search(r"[?&]event=([A-Z0-9_]+)", href)
        search_event_m = re.search(r"[?&]search_event=([A-Z0-9_]+)", href)
        if idp_m and event_m:
            idp = idp_m.group(1)
            detail_event = event_m.group(1)
            search_event = search_event_m.group(1) if search_event_m else detail_event
            if idp not in seen:
                seen.add(idp)
                entries.append((idp, detail_event, search_event))

    # Find total pages from pagination links. The site obfuscates these as
    # href="#" with a `data-silver` attribute: the real query string encoded as
    # comma-separated ASCII codes (e.g. "63,112,97,103,101,61,49" -> "?page=1").
    page_nums = set()
    for a in soup.find_all("a"):
        candidates = []
        if a.get("href"):
            candidates.append(a["href"])
        silver = a.get("data-silver")
        if silver:
            try:
                candidates.append("".join(chr(int(c)) for c in silver.split(",")))
            except ValueError:
                pass
        for cand in candidates:
            m = re.search(r"[?&]page=(\d+)", cand)
            if m:
                page_nums.add(int(m.group(1)))
    total_pages = max(page_nums) if page_nums else 1

    return entries, total_pages


def parse_detail_page(html: str) -> dict | None:
    """
    Parse an athlete/team detail page.
    Returns a dict with all extracted fields, or None if the page has no results.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Collect all th -> td mappings from every table on the page
    fields: dict[str, str] = {}
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td:
                key = _text(th)
                val = _text(td)
                if key and key not in fields:
                    fields[key] = val

    if not fields:
        return None

    # Solo athletes use a "Name" field; team events use "Member 1", "Member 2", …
    members = []
    if "Name" in fields and fields["Name"] and fields["Name"] != "-":
        members = [fields["Name"]]
    else:
        i = 1
        while f"Member {i}" in fields:
            name = fields[f"Member {i}"]
            if name and name != "-":
                members.append(name)
            i += 1

    members = [normalize_member_name(m) for m in members]

    def _clean(v: str | None) -> str | None:
        if not v or v in ("-", "–"):
            return None
        return v

    result = {
        "race_name": _clean(fields.get("Event")),
        "division": _clean(fields.get("Division")),
        "members": members,
        "bib_number": _clean(fields.get("Bib Number")),
        "gym_affiliate": _clean(fields.get("Gym Affiliate")),
        "age_group": _clean(fields.get("Age Group")),
        "rank_overall": _parse_int(fields.get("Rank (M/W)", "")),
        "rank_age_group": _parse_int(fields.get("Rank (AG)", "")),
        "league_points": _parse_int(fields.get("League Points", "")),
        "overall_time": _clean(fields.get("Overall Time")),
        "penalty": _clean(fields.get("Penalty")),
        "bonus": _clean(fields.get("Bonus")),
        "disqual_reason": _clean(fields.get("Disqual Reason")),
    }

    # --- Raw splits (table with Time Of Day column) ---
    raw_splits = []
    for table in soup.find_all("table"):
        headers = [_text(th) for th in table.find_all("th")]
        if "Time Of Day" in headers:
            for row in table.find("tbody").find_all("tr"):
                th = row.find("th")
                tds = row.find_all("td")
                if not th or len(tds) < 3:
                    continue
                raw_splits.append(
                    {
                        "name": _text(th),
                        "time_of_day": _clean(_text(tds[0])),
                        "time": _clean(_text(tds[1])),
                        "diff": _clean(_text(tds[2])),
                    }
                )
            break
    result["raw_splits"] = raw_splits

    # --- Refined splits (table with Split / Time / Place) ---
    refined_splits = []
    for table in soup.find_all("table"):
        headers = [_text(th) for th in table.find_all("th")]
        if headers == ["Split", "Time", "Place"] or (
            "Split" in headers and "Time" in headers and "Place" in headers
            and "Time Of Day" not in headers
        ):
            for row in table.find("tbody").find_all("tr"):
                th = row.find("th")
                tds = row.find_all("td")
                if not th or len(tds) < 2:
                    continue
                place_text = _clean(_text(tds[1])) if len(tds) > 1 else None
                refined_splits.append(
                    {
                        "name": _text(th),
                        "time": _clean(_text(tds[0])),
                        "place": _parse_int(place_text) if place_text else None,
                    }
                )
            break
    result["refined_splits"] = refined_splits

    return result
