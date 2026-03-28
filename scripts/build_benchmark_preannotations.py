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


DEFAULT_BENCHMARK_PATH = PROJECT_ROOT / "benchmark" / "eval_queries_seed.csv"
DEFAULT_REVIEW_BENCHMARK_PATH = PROJECT_ROOT / "benchmark" / "eval_queries_review.csv"
DEFAULT_REVIEW_SHEET_PATH = PROJECT_ROOT / "benchmark" / "query_scene_review_sheet.csv"


def parse_token_list(value) -> list[str]:
    if value is None:
        return []

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [item.strip() for item in text.split(",") if item.strip()]

    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    return []


def object_summary(record: dict) -> str:
    object_items = sorted(record.get("objects", {}).items(), key=lambda item: (-int(item[1]), str(item[0])))
    return ",".join(f"{name}:{count}" for name, count in object_items[:8])


def structured_candidate_tokens(parsed_query: dict, records: list[dict]) -> list[str]:
    return filter_scene_records(
        records,
        weather=parsed_query.get("weather"),
        timeofday=parsed_query.get("time"),
        object_types=parsed_query.get("objects") or [],
        location_kind=parsed_query.get("location"),
    )


def build_review_outputs(seed_df: pd.DataFrame, records: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    record_by_scene = {record["scene_token"]: record for record in records}
    benchmark_rows: list[dict] = []
    review_rows: list[dict] = []

    for _, row in seed_df.iterrows():
        query_id = str(row["query_id"])
        query_group = str(row["query_group"])
        query_text = str(row["query_text"])
        seed_scene_token = str(row["seed_scene_token"])
        parsed_query = parse_query(query_text)

        seed_suggestions = parse_token_list(row.get("candidate_scene_tokens"))
        if query_group == "open_semantic":
            suggested_tokens = [seed_scene_token]
            suggestion_basis = "seed_scene_only"
            review_instruction = (
                "Start from the seed scene. Add or remove scenes only after manual semantic review."
            )
        else:
            structured_tokens = seed_suggestions or structured_candidate_tokens(parsed_query, records)
            if seed_scene_token and seed_scene_token not in structured_tokens:
                structured_tokens = [seed_scene_token, *structured_tokens]
            suggested_tokens = structured_tokens
            suggestion_basis = "strict_structured_match"
            review_instruction = (
                "All suggested scenes satisfy the parsed structured conditions. Keep only the scenes that also match the "
                "full query semantics after manual review."
            )

        benchmark_rows.append(
            {
                **row.to_dict(),
                "suggested_relevant_scene_tokens": json.dumps(suggested_tokens, ensure_ascii=True),
                "suggested_relevant_count": len(suggested_tokens),
                "suggestion_basis": suggestion_basis,
                "review_status": "needs_manual_review",
                "review_instruction": review_instruction,
                "final_relevant_scene_tokens": "",
            }
        )

        for rank, scene_token in enumerate(suggested_tokens, start=1):
            record = record_by_scene.get(scene_token)
            if record is None:
                continue

            review_rows.append(
                {
                    "query_id": query_id,
                    "query_group": query_group,
                    "query_text": query_text,
                    "seed_scene_token": seed_scene_token,
                    "candidate_rank": rank,
                    "candidate_scene_token": scene_token,
                    "is_seed_scene": scene_token == seed_scene_token,
                    "suggested_label": 1,
                    "suggestion_basis": suggestion_basis,
                    "manual_label": "",
                    "scene_name": record.get("scene_name", ""),
                    "description": record.get("description", ""),
                    "weather": record.get("weather", ""),
                    "timeofday": record.get("timeofday", ""),
                    "location_kind": record.get("location_kind", ""),
                    "num_samples": int(record.get("num_samples", 0) or 0),
                    "object_summary": object_summary(record),
                    "review_comment": "",
                }
            )

    return pd.DataFrame(benchmark_rows), pd.DataFrame(review_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build review-ready preannotations for the benchmark seed set.")
    parser.add_argument("--benchmark-path", type=Path, default=DEFAULT_BENCHMARK_PATH)
    parser.add_argument("--review-benchmark-path", type=Path, default=DEFAULT_REVIEW_BENCHMARK_PATH)
    parser.add_argument("--review-sheet-path", type=Path, default=DEFAULT_REVIEW_SHEET_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.benchmark_path.exists():
        raise FileNotFoundError(f"Benchmark seed CSV not found: {args.benchmark_path}")

    seed_df = pd.read_csv(args.benchmark_path)
    records = build_scene_records()
    review_benchmark_df, review_sheet_df = build_review_outputs(seed_df, records)

    args.review_benchmark_path.parent.mkdir(parents=True, exist_ok=True)
    args.review_sheet_path.parent.mkdir(parents=True, exist_ok=True)
    review_benchmark_df.to_csv(args.review_benchmark_path, index=False, encoding="utf-8-sig")
    review_sheet_df.to_csv(args.review_sheet_path, index=False, encoding="utf-8-sig")

    print(
        json.dumps(
            {
                "review_benchmark_path": str(args.review_benchmark_path),
                "review_sheet_path": str(args.review_sheet_path),
                "query_count": int(len(review_benchmark_df)),
                "review_rows": int(len(review_sheet_df)),
                "group_counts": review_benchmark_df["query_group"].value_counts().to_dict(),
                "suggested_count_stats": review_benchmark_df.groupby("query_group")["suggested_relevant_count"].agg(["min", "median", "max"]).to_dict(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
