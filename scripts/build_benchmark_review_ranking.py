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

import app
from src.kg_builder import build_scene_records


DEFAULT_REVIEW_BENCHMARK_PATH = PROJECT_ROOT / "benchmark" / "eval_queries_review.csv"
DEFAULT_RANKED_BENCHMARK_PATH = PROJECT_ROOT / "benchmark" / "eval_queries_ranked_review.csv"
DEFAULT_RANKED_REVIEW_SHEET_PATH = PROJECT_ROOT / "benchmark" / "query_scene_ranked_review_sheet.csv"
DEFAULT_SHORTLIST_SIZE = 5


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


def scene_score_map(query_text: str, scene_tokens: list[str]) -> dict[str, float]:
    if not scene_tokens:
        return {}

    query_vector, _model_name = app.encode_text_query(query_text)
    hit_limit = max(40, len(scene_tokens) * 5)
    hits = app.search_frame_hits(query_vector, hit_limit, scene_tokens)

    score_map: dict[str, float] = {}
    for hit in hits:
        scene_token = str(hit.get("scene_token") or "").strip()
        if not scene_token:
            continue
        score = float(hit.get("score", 0.0) or 0.0)
        existing = score_map.get(scene_token)
        if existing is None or score > existing:
            score_map[scene_token] = score
    return score_map


def rank_scene_tokens(scene_tokens: list[str], score_map: dict[str, float]) -> list[str]:
    indexed_tokens = list(enumerate(scene_tokens))
    ranked = sorted(
        indexed_tokens,
        key=lambda item: (
            -(score_map.get(item[1], -1.0)),
            item[0],
        ),
    )
    return [token for _, token in ranked]


def build_ranked_outputs(review_df: pd.DataFrame, shortlist_size: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    records = build_scene_records()
    record_by_scene = {record["scene_token"]: record for record in records}

    benchmark_rows: list[dict] = []
    review_rows: list[dict] = []

    for _, row in review_df.iterrows():
        row_dict = row.to_dict()
        query_id = str(row_dict["query_id"])
        query_group = str(row_dict["query_group"])
        query_text = str(row_dict["query_text"])
        scene_tokens = parse_token_list(row_dict.get("suggested_relevant_scene_tokens"))

        if query_group == "open_semantic":
            score_map = {}
            ranked_tokens = scene_tokens
        else:
            score_map = scene_score_map(query_text, scene_tokens)
            ranked_tokens = rank_scene_tokens(scene_tokens, score_map)

        shortlist_tokens = ranked_tokens[:shortlist_size]
        benchmark_rows.append(
            {
                **row_dict,
                "ranked_suggested_scene_tokens": json.dumps(ranked_tokens, ensure_ascii=True),
                "review_shortlist_scene_tokens": json.dumps(shortlist_tokens, ensure_ascii=True),
                "review_shortlist_count": len(shortlist_tokens),
            }
        )

        for rank, scene_token in enumerate(ranked_tokens, start=1):
            record = record_by_scene.get(scene_token)
            if record is None:
                continue
            review_rows.append(
                {
                    "query_id": query_id,
                    "query_group": query_group,
                    "query_text": query_text,
                    "candidate_rank": rank,
                    "candidate_scene_token": scene_token,
                    "is_seed_scene": scene_token == str(row_dict.get("seed_scene_token") or ""),
                    "best_frame_score": score_map.get(scene_token, ""),
                    "in_review_shortlist": rank <= shortlist_size,
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
    parser = argparse.ArgumentParser(description="Rank benchmark review candidates by actual retrieval similarity.")
    parser.add_argument("--review-benchmark-path", type=Path, default=DEFAULT_REVIEW_BENCHMARK_PATH)
    parser.add_argument("--ranked-benchmark-path", type=Path, default=DEFAULT_RANKED_BENCHMARK_PATH)
    parser.add_argument("--ranked-review-sheet-path", type=Path, default=DEFAULT_RANKED_REVIEW_SHEET_PATH)
    parser.add_argument("--shortlist-size", type=int, default=DEFAULT_SHORTLIST_SIZE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.review_benchmark_path.exists():
        raise FileNotFoundError(f"Review benchmark CSV not found: {args.review_benchmark_path}")

    review_df = pd.read_csv(args.review_benchmark_path)
    ranked_benchmark_df, ranked_review_df = build_ranked_outputs(review_df, args.shortlist_size)

    args.ranked_benchmark_path.parent.mkdir(parents=True, exist_ok=True)
    args.ranked_review_sheet_path.parent.mkdir(parents=True, exist_ok=True)
    ranked_benchmark_df.to_csv(args.ranked_benchmark_path, index=False, encoding="utf-8-sig")
    ranked_review_df.to_csv(args.ranked_review_sheet_path, index=False, encoding="utf-8-sig")

    print(
        json.dumps(
            {
                "ranked_benchmark_path": str(args.ranked_benchmark_path),
                "ranked_review_sheet_path": str(args.ranked_review_sheet_path),
                "query_count": int(len(ranked_benchmark_df)),
                "review_rows": int(len(ranked_review_df)),
                "shortlist_size": int(args.shortlist_size),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
