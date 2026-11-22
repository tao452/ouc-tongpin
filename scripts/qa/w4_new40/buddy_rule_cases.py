"""Run confirmed business boundaries only after M5 implementation confirmation."""

import json
import re
from decimal import Decimal

from common import BASE_COMMIT, ROOT

RULE_FILE = ROOT / "docs/qa/w4-additional-40/rule-confirmations-20261122.json"
COMMENT = re.compile(
    r"https://github\.com/tao452/ouc-tongpin/pull/\d+#(?:issuecomment-|pullrequestreview-|discussion_r)\d+\Z"
)


def load_rules():
    rules = json.loads(RULE_FILE.read_bytes())["cases"]
    for rule in rules.values():
        business = rule["business"]
        if business["confirmed"]:
            assert business["confirmed_by"].casefold() == "tao452"
            assert COMMENT.fullmatch(business["comment_url"])
        implementation = rule["implementation"]
        if implementation["confirmed"]:
            assert implementation["confirmed_by"].casefold() == "raylee06"
            assert COMMENT.fullmatch(implementation["comment_url"])
            assert re.fullmatch(r"[0-9a-f]{40}", implementation["source_commit"])
        assert rule["valid_status"] == 201 and rule["invalid_status"] == 400
    assert rules["S1-113"]["latitude_range"] == [-90, 90]
    assert rules["S1-113"]["longitude_range"] == [-180, 180]
    assert rules["S1-114"]["unit"] == "unicode_code_points"
    assert rules["S1-114"]["maximum"] == 200
    return rules


def ready(rule):
    return rule["business"]["confirmed"] and rule["implementation"]["confirmed"]


def coordinates(s, rule):
    lat_min, lat_max = map(Decimal, map(str, rule["latitude_range"]))
    lng_min, lng_max = map(Decimal, map(str, rule["longitude_range"]))
    step = Decimal("0.000001")
    samples = [
        (lat_min, lng_min, rule["valid_status"]),
        (lat_max, lng_max, rule["valid_status"]),
        (lat_min - step, Decimal(0), rule["invalid_status"]),
        (lat_max + step, Decimal(0), rule["invalid_status"]),
        (Decimal(0), lng_min - step, rule["invalid_status"]),
        (Decimal(0), lng_max + step, rule["invalid_status"]),
    ]
    actor = s.actor()
    errors = []
    for number, (lat, lng, expected) in enumerate(samples, 1):
        body = s.need()
        body["location"].update(lat=float(lat), lng=float(lng))
        before = s.buddy_count(actor)
        status, response, _ = s.buddy(actor, body)
        after = s.buddy_count(actor)
        snapshot = s.sql(
            "SELECT id,latitude,longitude FROM buddy_demand WHERE user_id="
            + str(int(actor["id"]))
            + " ORDER BY id"
        )
        s.record(
            {
                "kind": "coordinate_boundary",
                "sample": number,
                "input_decimal": {"lat": str(lat), "lng": str(lng)},
                "expected_status": expected,
                "actual_status": status,
                "owned_rows_before": before,
                "owned_rows_after": after,
                "owned_snapshot": snapshot,
            }
        )
        good = status == expected and after - before == (1 if expected == 201 else 0)
        if status == 201:
            current = s.sql(
                "SELECT latitude,longitude FROM buddy_demand WHERE user_id="
                + str(int(actor["id"]))
                + " AND id="
                + str(int(response["id"]))
            )
            got_lat, got_lng = map(Decimal, current.split("\t"))
            good = good and got_lat == lat and got_lng == lng
        if not good:
            errors.append(
                {
                    "sample": number,
                    "expected": expected,
                    "actual": status,
                    "row_delta": after - before,
                }
            )
    # Preserve all six samples even when an early boundary exposes a defect.
    assert not errors, errors


def emoji(s, rule):
    assert rule["unit"] == "unicode_code_points" and rule["maximum"] == 200
    actor = s.actor()
    errors = []
    for number in [100, 101, 200, 201]:
        remark = "\U0001f600" * number
        lengths = {
            "unicode_code_points": len(remark),
            "utf16_code_units": len(remark.encode("utf-16-le")) // 2,
            "utf8_bytes": len(remark.encode("utf-8")),
        }
        expected = (
            rule["valid_status"]
            if lengths[rule["unit"]] <= rule["maximum"]
            else rule["invalid_status"]
        )
        body = s.need()
        body["remark"] = remark
        before = s.buddy_count(actor)
        status, response, _ = s.buddy(actor, body)
        after = s.buddy_count(actor)
        s.record(
            {
                "kind": "emoji_boundary",
                "repeat_count": number,
                "lengths": lengths,
                "approved_unit": rule["unit"],
                "expected_status": expected,
                "actual_status": status,
                "owned_rows_before": before,
                "owned_rows_after": after,
            }
        )
        good = status == expected and after - before == (1 if expected == 201 else 0)
        if status == 201:
            row = s.sql(
                "SELECT HEX(remark),CHAR_LENGTH(remark),LENGTH(remark) FROM buddy_demand WHERE user_id="
                + str(int(actor["id"]))
                + " AND id="
                + str(int(response["id"]))
            ).split("\t")
            good = (
                good
                and row[0].lower() == remark.encode("utf-8").hex()
                and int(row[1]) == number
                and int(row[2]) == number * 4
            )
        if not good:
            errors.append(
                {
                    "repeat_count": number,
                    "expected": expected,
                    "actual": status,
                    "row_delta": after - before,
                }
            )
    assert not errors, errors


def register(s):
    rules = load_rules()
    s.rule_confirmations = rules
    for number, check in [(113, coordinates), (114, emoji)]:
        cid = f"S1-{number}"
        rule = rules[cid]
        if ready(rule):
            s.run(number, lambda rule=rule, check=check: check(s, rule))
        else:
            s.results.append(
                {
                    "case_id": cid,
                    "status": "NOT_RUN",
                    "executed": False,
                    "source_commit": BASE_COMMIT,
                    "reason": "M1 business rule confirmed; M5 implementation/contract confirmation pending",
                    "business_confirmation": rule["business"],
                    "evidence": [],
                }
            )
