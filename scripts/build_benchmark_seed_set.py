from __future__ import annotations

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
from pathlib import Path

import pandas as pd

from src.kg_builder import build_scene_records, filter_scene_records
from src.nlp_parser import parse_query


DEFAULT_OPEN_COUNT = 12
DEFAULT_TWO_COUNT = 12
DEFAULT_THREE_COUNT = 12
DEFAULT_QUERY_OUTPUT = PROJECT_ROOT / "benchmark" / "eval_queries_seed.csv"
DEFAULT_AID_OUTPUT = PROJECT_ROOT / "benchmark" / "query_scene_annotation_aid.csv"


def condition_count(parsed_query: dict) -> int:
    return (
        int(bool(parsed_query.get("weather")))
        + int(bool(parsed_query.get("time")))
        + int(bool(parsed_query.get("location")))
        + len(parsed_query.get("objects") or [])
    )


def build_signature(parsed_query: dict) -> tuple[str, str, str, tuple[str, ...]]:
    return (
        str(parsed_query.get("weather") or ""),
        str(parsed_query.get("time") or ""),
        str(parsed_query.get("location") or ""),
        tuple(str(item) for item in (parsed_query.get("objects") or [])),
    )


def object_summary(record: dict) -> str:
    object_items = sorted(record.get("objects", {}).items(), key=lambda item: (-int(item[1]), str(item[0])))
    return ",".join(f"{name}:{count}" for name, count in object_items[:8])


def select_rows(rows: list[dict], target_count: int) -> list[dict]:
    selected: list[dict] = []
    used_signatures: set[tuple[str, str, str, tuple[str, ...]]] = set()

    for row in rows:
        signature = build_signature(row["parsed_query"])
        if signature in used_signatures:
            continue
        used_signatures.add(signature)
        selected.append(row)
        if len(selected) >= target_count:
            return selected

    for row in rows:
        if row in selected:
            continue
        selected.append(row)
        if len(selected) >= target_count:
            break

    return selected


def build_candidate_rows(records: list[dict]) -> list[dict]:
    scene_name_lookup = {record["scene_token"]: record for record in records}
    rows: list[dict] = []

    for record in records:
        query_text = str(record.get("description") or "").strip()
        if not query_text:
            continue

        parsed_query = parse_query(query_text)
        parsed_count = condition_count(parsed_query)
        candidate_scene_tokens = filter_scene_records(
            records,
            weather=parsed_query.get("weather"),
            timeofday=parsed_query.get("time"),
            object_types=parsed_query.get("objects") or [],
            location_kind=parsed_query.get("location"),
        )

        if parsed_count <= 1:
            query_group = "open_semantic"
        elif parsed_count == 2:
            query_group = "two_condition"
        else:
            query_group = "three_plus"

        rows.append(
            {
                "query_text": query_text,
                "query_group": query_group,
                "seed_scene_token": record["scene_token"],
                "seed_scene_name": record.get("scene_name", ""),
                "seed_description": query_text,
                "parsed_query": parsed_query,
                "parsed_condition_count": parsed_count,
                "candidate_scene_tokens": candidate_scene_tokens,
                "candidate_scene_count": len(candidate_scene_tokens),
                "seed_scene_record": scene_name_lookup[record["scene_token"]],
            }
        )

    return rows


def build_query_dataframe(
    candidate_rows: list[dict],
    open_count: int,
    two_count: int,
    three_count: int,
) -> pd.DataFrame:
    open_rows = [
        row
        for row in candidate_rows
        if row["query_group"] == "open_semantic"
    ]
    open_rows.sort(key=lambda row: (-len(row["query_text"]), row["seed_scene_name"], row["seed_scene_token"]))

    two_rows = [
        row
        for row in candidate_rows
        if row["query_group"] == "two_condition" and 1 <= row["candidate_scene_count"] <= 20
    ]
    two_rows.sort(
        key=lambda row: (
            row["candidate_scene_count"],
            -len(row["query_text"]),
            row["seed_scene_name"],
            row["seed_scene_token"],
        )
    )

    three_rows = [
        row
        for row in candidate_rows
        if row["query_group"] == "three_plus" and 1 <= row["candidate_scene_count"] <= 20
    ]
    three_rows.sort(
        key=lambda row: (
            row["candidate_scene_count"],
            -row["parsed_condition_count"],
            -len(row["query_text"]),
            row["seed_scene_name"],
            row["seed_scene_token"],
        )
    )

    selected_rows = (
        select_rows(open_rows, open_count)
        + select_rows(two_rows, two_count)
        + select_rows(three_rows, three_count)
    )

    query_rows: list[dict] = []
    for index, row in enumerate(selected_rows, start=1):
        parsed_query = row["parsed_query"]
        query_rows.append(
            {
                "query_id": f"B{index:03d}",
                "query_group": row["query_group"],
                "query_text": row["query_text"],
                "relevant_scene_tokens": "",
                "annotation_status": "todo",
                "seed_scene_token": row["seed_scene_token"],
                "seed_scene_name": row["seed_scene_name"],
                "parsed_condition_count": row["parsed_condition_count"],
                "parsed_weather": str(parsed_query.get("weather") or ""),
                "parsed_time": str(parsed_query.get("time") or ""),
                "parsed_location": str(parsed_query.get("location") or ""),
                "parsed_objects": json.dumps(parsed_query.get("objects") or [], ensure_ascii=True),
                "candidate_scene_count": row["candidate_scene_count"],
                "candidate_scene_tokens": (
                    json.dumps(row["candidate_scene_tokens"], ensure_ascii=True)
                    if row["query_group"] != "open_semantic"
                    else ""
                ),
                "notes": (
                    "Source query comes directly from the current dataset scene description. "
                    "Fill relevant_scene_tokens after scene-level review."
                ),
            }
        )

    return pd.DataFrame(query_rows)


def build_annotation_aid(query_df: pd.DataFrame, records: list[dict]) -> pd.DataFrame:
    record_by_scene = {record["scene_token"]: record for record in records}
    aid_rows: list[dict] = []

    for _, query_row in query_df.iterrows():
        seed_scene_token = str(query_row["seed_scene_token"])
        candidate_scene_tokens = []
        if str(query_row["candidate_scene_tokens"]).strip():
            candidate_scene_tokens = json.loads(str(query_row["candidate_scene_tokens"]))

        if str(query_row["query_group"]) == "open_semantic":
            candidate_scene_tokens = [seed_scene_token]

        for scene_token in candidate_scene_tokens:
            record = record_by_scene.get(scene_token)
            if record is None:
                continue
            aid_rows.append(
                {
                    "query_id": str(query_row["query_id"]),
                    "query_group": str(query_row["query_group"]),
                    "query_text": str(query_row["query_text"]),
                    "seed_scene_token": seed_scene_token,
                    "candidate_scene_token": scene_token,
                    "is_seed_scene": scene_token == seed_scene_token,
                    "scene_name": record.get("scene_name", ""),
                    "description": record.get("description", ""),
                    "weather": record.get("weather", ""),
                    "timeofday": record.get("timeofday", ""),
                    "location_kind": record.get("location_kind", ""),
                    "num_samples": int(record.get("num_samples", 0) or 0),
                    "object_summary": object_summary(record),
                }
            )

    return pd.DataFrame(aid_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an annotation-ready benchmark seed set from the current trainval subset.")
    parser.add_argument("--open-count", type=int, default=DEFAULT_OPEN_COUNT)
    parser.add_argument("--two-count", type=int, default=DEFAULT_TWO_COUNT)
    parser.add_argument("--three-count", type=int, default=DEFAULT_THREE_COUNT)
    parser.add_argument("--query-output", type=Path, default=DEFAULT_QUERY_OUTPUT)
    parser.add_argument("--aid-output", type=Path, default=DEFAULT_AID_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = build_scene_records()
    candidate_rows = build_candidate_rows(records)
    query_df = build_query_dataframe(candidate_rows, args.open_count, args.two_count, args.three_count)
    aid_df = build_annotation_aid(query_df, records)

    args.query_output.parent.mkdir(parents=True, exist_ok=True)
    args.aid_output.parent.mkdir(parents=True, exist_ok=True)
    query_df.to_csv(args.query_output, index=False, encoding="utf-8-sig")
    aid_df.to_csv(args.aid_output, index=False, encoding="utf-8-sig")

    print(
        json.dumps(
            {
                "query_output": str(args.query_output),
                "aid_output": str(args.aid_output),
                "query_count": int(len(query_df)),
                "group_counts": query_df["query_group"].value_counts().to_dict(),
                "aid_rows": int(len(aid_df)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
