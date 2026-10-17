#!/usr/bin/env python3
"""Offline cache-usage report from a read-only export; makes no API/DB calls.

Run inside the backend Docker service, with the repository mounted at /repo:
python /repo/scripts/analyze-openai-cache.py SOURCE.json --output-dir /repo/docs/cache-analysis
"""
import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo


def dt(value):
    return datetime.fromisoformat(value)


def money(value):
    return Decimal(str(value or 0))


def costs(row):
    """Use contemporaneous stored rates, including tier/context multipliers."""
    multiplier = money(row["input_price_multiplier"])
    ordinary = row["input_tokens"] - row["cached_input_tokens"] - row["cache_write_input_tokens"]
    return {
        "ordinary": ordinary * money(row["input_price_per_million"]) * multiplier / 1_000_000,
        "read": row["cached_input_tokens"] * money(row["cached_input_price_per_million"]) * multiplier / 1_000_000,
        "write": row["cache_write_input_tokens"] * money(row["cache_write_price_per_million"]) * multiplier / 1_000_000,
        "output": row["output_tokens"] * money(row["output_price_per_million"]) * money(row["output_price_multiplier"]) / 1_000_000,
    }


def analyse(source, output_dir):
    rows = sorted(source["usage"], key=lambda r: (dt(r["created_at"]), r["id"]))
    assert rows, "No recorded calls"
    assert len({r["response_id"] for r in rows}) == len(rows), "Duplicate responses"
    zone = ZoneInfo("Africa/Johannesburg")
    prior = {}
    groups = defaultdict(list)
    timeline = []
    messages = source.get("message_metadata", [])
    uploads = source.get("upload_metadata", [])
    for number, row in enumerate(rows, 1):
        assert row["estimated_cost_usd"] is not None, "Unpriced calls need separate handling"
        assert row["input_tokens"] >= row["cached_input_tokens"] + row["cache_write_input_tokens"]
        assert abs(sum(costs(row).values()) - money(row["estimated_cost_usd"])) <= Decimal("0.0000005")
        previous = prior.get(row["agent_id"])
        start = dt(row["created_at"]) - timedelta(milliseconds=row["duration_ms"])
        gap = max((start - dt(previous["created_at"])).total_seconds(), 0) if previous else None
        prefix_changed = bool(previous and previous["cache_prefix_hash"] != row["cache_prefix_hash"])
        model_changed = bool(previous and previous["model"] != row["model"])
        drop = previous["cached_input_tokens"] - row["cached_input_tokens"] if previous else 0
        flags = []
        if not previous:
            flags.append("first call for agent")
        if model_changed:
            flags.append("model switch")
        if prefix_changed:
            flags.append("opening fingerprint changed")
        if gap is not None and gap >= 1800:
            flags.append("gap >=30 minutes; expiry plausible")
        if drop >= 5000:
            flags.append("read drop >=5000 tokens")
        comparable = previous and not model_changed and not prefix_changed and gap < 1800
        flat = bool(comparable and row["cached_input_tokens"] > 0 and row["cached_input_tokens"] == previous["cached_input_tokens"] and row["cache_write_input_tokens"] >= 5000)
        if flat:
            flags.append("flat read boundary; >=5000 write tokens")
        if comparable and drop >= 5000:
            flags.append("unexplained short-gap drop")
        lower = dt(previous["created_at"]) if previous else start
        user_events = sum(m["agent_id"] == row["agent_id"] and m["role"] == "user" and lower < dt(m["created_at"]) <= start for m in messages)
        upload_events = sum(lower < dt(u["uploaded_at"]) <= start for u in uploads)
        item = {
            "call": number, "usage_id": row["id"],
            "time_SAST": dt(row["created_at"]).astimezone(zone).isoformat(timespec="seconds"),
            "stage": row["task_name"], "agent_id": row["agent_id"],
            "model": row["model"], "service_tier": row["service_tier"],
            "gap_seconds_approx": round(gap, 1) if gap is not None else "",
            "input_tokens": row["input_tokens"], "read_tokens": row["cached_input_tokens"],
            "write_tokens": row["cache_write_input_tokens"],
            "ordinary_input_tokens": row["input_tokens"] - row["cached_input_tokens"] - row["cache_write_input_tokens"],
            "read_percent": round(100 * row["cached_input_tokens"] / max(row["input_tokens"], 1), 2),
            "read_drop_tokens": drop, "prefix_changed": prefix_changed,
            "user_messages_since_previous": user_events, "uploads_since_previous": upload_events,
            "flat_read_with_writes": flat,
            "diagnostic": row["cache_diagnostics"].get("type", "missing"),
            "write_cost_usd": f'{costs(row)["write"]:.6f}',
            "total_cost_usd": row["estimated_cost_usd"], "flags": "; ".join(flags),
        }
        timeline.append(item)
        groups[row["task_name"]].append((row, item))
        prior[row["agent_id"]] = row

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f'dataset-{source["dataset_id"]}'
    with (output_dir / f"{stem}-timeline.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(timeline[0]))
        writer.writeheader()
        writer.writerows(timeline)
    totals = {key: sum(costs(row)[key] for row in rows) for key in costs(rows[0])}
    recorded = sum(money(row["estimated_cost_usd"]) for row in rows)
    diagnostic = Counter(item["diagnostic"] for item in timeline)
    drops = sorted((item for item in timeline if item["read_drop_tokens"] >= 5000), key=lambda item: -item["read_drop_tokens"])
    largest_stage, largest_members = max(groups.items(), key=lambda pair: sum(costs(r)["write"] for r, _ in pair[1]))
    stage_models = Counter(r["model"] for r, _ in largest_members)
    main_model = stage_models.most_common(1)[0][0]
    model_rows = [r for r, _ in largest_members if r["model"] == main_model]
    read_boundary, boundary_count = Counter(r["cached_input_tokens"] for r in model_rows[1:]).most_common(1)[0]
    unexplained = sum("unexplained short-gap drop" in item["flags"] for item in drops)
    lines = [
        f'# Dataset {source["dataset_id"]}: cache reuse report', "",
        "Read-only production export analysed locally. No workflow reruns or model calls.",
        f'Exported {source["exported_at"]}. Times below use Africa/Johannesburg (UTC+02:00).', "",
        f'**{len(rows)} calls; ${recorded:.6f} recorded cost.** Input cost: ordinary ${totals["ordinary"]:.4f}, cache reads ${totals["read"]:.4f}, cache writes **${totals["write"]:.4f}**. Output ${totals["output"]:.4f}. Component totals differ from recorded totals only by per-call rounding.',
        "", "## Main findings", "",
        f'- **Repeated flat reuse is the main signal.** In {largest_stage}, {boundary_count} of {len(model_rows)-1} calls after the first {main_model} call read exactly {read_boundary:,} cached tokens. That stage alone spent ${sum(costs(r)["write"] for r, _ in largest_members):.4f} on cache writes.',
        f'- There are {len(drops)} drops of at least 5,000 cached tokens. Only {unexplained} occurs without a model switch or a long gap. See the separate drop table below.',
        '- The immediate next investigation is why cached reuse does not grow with the conversation in the quality gate. Existing records locate the symptom but cannot identify the changing prompt section or quantify avoidable spend.',
        "", "### Example quality-gate sequence", "",
        "These calls use the same model and opening fingerprint. Reads stay flat while write volume grows and falls.", "",
        "| Usage ID | Time (SAST) | Input | Cache read | Cache write |", "|---|---|---:|---:|---:|",
        *[f'| {r["id"]} | {dt(r["created_at"]).astimezone(zone).isoformat(timespec="seconds")} | {r["input_tokens"]:,} | {r["cached_input_tokens"]:,} | {r["cache_write_input_tokens"]:,} |' for r in [model_rows[1], model_rows[len(model_rows)//2], model_rows[-1]]],
        "", "## By workflow stage", "",
        "Read/write shares are token-weighted percentages of input. Flat-read calls reuse exactly the same token count as the preceding comparable call while writing at least 5,000 tokens. They are indicators, not proven wasted spend.", "",
        "| Stage | Calls | Read % | Write % | Write cost | Total cost | Flat-read calls |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for stage, members in groups.items():
        records = [r for r, _ in members]
        total_input = sum(r["input_tokens"] for r in records)
        reads = sum(r["cached_input_tokens"] for r in records)
        writes = sum(r["cache_write_input_tokens"] for r in records)
        lines.append(f'| {stage} | {len(records)} | {100*reads/total_input:.1f} | {100*writes/total_input:.1f} | ${sum(costs(r)["write"] for r in records):.4f} | ${sum(money(r["estimated_cost_usd"]) for r in records):.4f} | {sum(t["flat_read_with_writes"] for _, t in members)} |')
    lines += ["", "## Repeated cache-read boundaries", "", "| Stage / model | Calls after first with same fingerprint/model | Most common read boundary | Calls at that boundary |", "|---|---:|---:|---:|"]
    model_groups = defaultdict(list)
    for row, item in ((r, t) for stage in groups.values() for r, t in stage):
        model_groups[(row["task_name"], row["model"], row["agent_id"], row["cache_prefix_hash"])].append(row)
    for (stage, model, agent, fingerprint), records in model_groups.items():
        warm = records[1:]
        if len(warm) < 3:
            continue
        boundary, count = Counter(r["cached_input_tokens"] for r in warm).most_common(1)[0]
        lines.append(f'| {stage} / {model} (agent {agent}) | {len(warm)} | {boundary:,} | {count} |')
    lines += ["", "## Large drops in cache reads", "", "Threshold: 5,000 fewer cached tokens than the previous call for the same agent. Model switches and long gaps are shown separately from unexplained drops.", "", "| Usage ID | Time (SAST) | Stage | Read drop | Current read / write | Approx. gap | Context |", "|---|---|---|---:|---:|---:|---|"]
    for item in drops:
        lines.append(f'| {item["usage_id"]} | {item["time_SAST"]} | {item["stage"]} | {item["read_drop_tokens"]:,} | {item["read_tokens"]:,} / {item["write_tokens"]:,} | {item["gap_seconds_approx"]} s | {item["flags"]} |')
    lines += ["", "## Limits of this measurement", "",
        f'Provider diagnostic types: {dict(diagnostic)}. Nonempty diagnostics frequently say unavailable; their presence does not establish a cause.',
        "The stored opening fingerprint includes model, reasoning effort, temperature, tools and opening instructions. It does not hash the rendered conversation history. Identical fingerprints therefore do not prove identical cached content or a particular cache breakpoint.",
        "Equal cached-token counts suggest a stable reuse boundary; these records cannot establish which prompt section ends at that boundary, or whether writes contain previously seen tokens. New history, compaction, changed user evidence, cache expiry and provider behaviour remain possible explanations.",
        "Gap estimates subtract recorded model duration from the next usage timestamp. They are approximate. User/upload counts use metadata only and do not establish the full semantic dependencies of a change.",
        "No dollar amount is labelled avoidable without a controlled comparison. Short gaps under 30 minutes are an investigation heuristic, not evidence that the cache must still exist.",
        "", "## Reproduce locally", "",
        "Run this script in Docker against the retained metadata-only export. The script makes no network or database calls. Raw dataset values, user message text, filenames and model prompts are excluded from the export.",
        "", f'The full call sequence is in [{stem}-timeline.csv]({stem}-timeline.csv).', "",
    ]
    (output_dir / f"{stem}.md").write_text("\n".join(lines))
    print(json.dumps({"calls": len(rows), "recorded_cost": str(recorded), "costs": {k: str(v) for k,v in totals.items()}, "flat_read_calls": sum(t["flat_read_with_writes"] for t in timeline), "large_drops": len(drops), "unexplained_drops": [t["usage_id"] for t in timeline if "unexplained short-gap drop" in t["flags"]], "diagnostics": dict(diagnostic)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    analyse(json.loads(args.source.read_text()), args.output_dir)
