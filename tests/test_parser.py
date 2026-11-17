import pytest

from fixture_store import PAGINATED_LIST
from parser import (
    gender_from_division,
    is_placeholder_team,
    normalize_member_name,
    parse_detail_page,
    parse_list_fields,
    parse_list_page,
)

LISBON_PRO = "TP_5GGDDHUF8D"


def list_params(event: str, sex: str | None, page: int = 1) -> dict:
    params = {
        "content": "list",
        "fpid": "list",
        "pid": "list",
        "lang": "EN_CAP",
        "event": event,
        "search[age_class]": "%",
        "page": page,
    }
    if sex is not None:
        params["search[sex]"] = sex
    return params


@pytest.mark.parametrize(
    "division, expected",
    [
        ("TRYKA DOUBLES MIXED", "X"),
        ("MENS AND WOMENS", "X"),
        ("TRYKA PRO MENS", "M"),
        ("BOYS 12-13", "M"),
        pytest.param(
            "TRYKA PRO WOMENS",
            "W",
            marks=pytest.mark.xfail(
                strict=True,
                reason="known bug: 'WOMENS' contains 'MENS', so it is classed as mixed/men",
            ),
        ),
        ("GIRLS 8-9", "W"),
        ("TRYKA PRO", None),
    ],
)
def test_gender_from_division(division, expected):
    assert gender_from_division(division) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("O'SHEA, CIARÁN (IRL)", "Ciarán O'Shea (IRL)"),
        ("Murphy, Sean (IRL)", "Sean Murphy (IRL)"),
        ("BREEN, AOIFE", "Aoife Breen"),
        ("Already Normal", "Already Normal"),
    ],
)
def test_normalize_member_name(raw, expected):
    assert normalize_member_name(raw) == expected


def test_is_placeholder_team():
    assert is_placeholder_team(["1", "2", "3", "4"])
    assert is_placeholder_team(["Fred Martin", "2 2", "3", "4"])
    assert not is_placeholder_team(["Fred Martin", "Jo Bloggs"])
    assert not is_placeholder_team([])


def test_parse_list_page_entries(recorded_page):
    html = recorded_page(1, list_params(LISBON_PRO, "M"))
    entries, total_pages = parse_list_page(html)
    assert len(entries) == 12
    assert total_pages == 1
    idps = [idp for idp, _, _ in entries]
    assert "5GGDDHUFCB1B" in idps
    for idp, detail_event, search_event in entries:
        assert idp and detail_event and search_event


def test_parse_list_page_pagination(recorded_page):
    entries, total_pages = parse_list_page(recorded_page(*PAGINATED_LIST))
    assert len(entries) == 25
    assert total_pages > 1


def test_parse_list_fields(recorded_page):
    fields = parse_list_fields(recorded_page(1, list_params(LISBON_PRO, "M")))
    assert fields["5GGDDHUFCB1B"] == {
        "rank_overall": 1,
        "rank_age_group": 1,
        "overall_time": "00:57:28",
    }


def test_parse_detail_page(recorded_page):
    entries, _ = parse_list_page(recorded_page(1, list_params(LISBON_PRO, "M")))
    idp, detail_event, search_event = next(e for e in entries if e[0] == "5GGDDHUFCB1B")
    html = recorded_page(
        1,
        {
            "content": "detail",
            "fpid": "list",
            "pid": "list",
            "idp": idp,
            "lang": "EN_CAP",
            "event": detail_event,
            "search[sex]": "X",
            "search[age_class]": "%",
            "search_event": search_event,
        },
    )
    data = parse_detail_page(html)
    assert data is not None
    assert data["members"] == ["Robert Ronan"]
    assert data["age_group"] == "25 - 29"
    assert data["rank_overall"] == 1
    assert data["rank_age_group"] == 1
    assert data["overall_time"] == "00:57:28"
    assert len(data["raw_splits"]) == 31
    assert len(data["refined_splits"]) == 20
    assert data["refined_splits"][1] == {"name": "SkiErg", "time": "00:04:07", "place": 4}


def test_parse_detail_page_without_tables():
    assert parse_detail_page("<html><body><p>No results</p></body></html>") is None
