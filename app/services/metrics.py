import time
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class MetricsService:
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self.entries: List[Dict[str, Any]] = []
        self.start_time = datetime.now()

    def record_classification(self, feedback_text: str, categories: List[Dict],
                              latency_ms: float, confidence: float,
                              needs_review: bool, assigned_team: str,
                              error: Optional[str] = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "feedback_text": feedback_text[:100],
            "categories": categories,
            "latency_ms": round(latency_ms, 1),
            "confidence": round(confidence, 3),
            "needs_review": needs_review,
            "assigned_team": assigned_team,
            "error": error
        }
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def get_summary(self) -> Dict[str, Any]:
        total = len(self.entries)
        if total == 0:
            return {
                "total_processed": 0,
                "auto_tagged": 0,
                "needs_review": 0,
                "avg_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
                "avg_confidence": 0,
                "error_rate": 0,
                "category_distribution": {},
                "team_distribution": {},
                "latency_over_time": [],
                "confidence_histogram": [0] * 10,
                "uptime_hours": 0,
                "throughput_per_hour": 0
            }

        latencies = [e["latency_ms"] for e in self.entries if e.get("latency_ms")]
        confidences = [e["confidence"] for e in self.entries if e.get("confidence")]
        errors = [e for e in self.entries if e.get("error")]
        needs_review_count = sum(1 for e in self.entries if e.get("needs_review"))

        latencies_sorted = sorted(latencies)
        p95_idx = int(len(latencies_sorted) * 0.95)
        p99_idx = int(len(latencies_sorted) * 0.99)

        cat_dist = defaultdict(int)
        for e in self.entries:
            for c in e.get("categories", []):
                cat_name = c.get("category", "unknown")
                sub_name = c.get("subcategory", "")
                key = f"{cat_name}.{sub_name}" if sub_name else cat_name
                cat_dist[key] += 1

        team_dist = defaultdict(int)
        for e in self.entries:
            t = e.get("assigned_team", "none")
            if t and t != "none":
                team_dist[t] += 1

        uptime = (datetime.now() - self.start_time).total_seconds() / 3600

        buckets = [0] * 10
        for c in confidences:
            idx = min(int(c * 10), 9)
            buckets[idx] += 1

        now = datetime.now()
        hourly = defaultdict(int)
        for e in self.entries:
            ts = e.get("timestamp", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    hour_key = dt.strftime("%Y-%m-%d %H:00")
                    hourly[hour_key] += 1
                except ValueError:
                    pass

        latency_over_time = []
        for e in self.entries[-200:]:
            ts = e.get("timestamp", "")
            if ts and e.get("latency_ms"):
                try:
                    dt = datetime.fromisoformat(ts)
                    latency_over_time.append({
                        "time": dt.strftime("%H:%M"),
                        "latency": e["latency_ms"]
                    })
                except ValueError:
                    pass

        return {
            "total_processed": total,
            "auto_tagged": total - needs_review_count,
            "needs_review": needs_review_count,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "p95_latency_ms": round(latencies_sorted[p95_idx], 1) if latencies_sorted else 0,
            "p99_latency_ms": round(latencies_sorted[p99_idx], 1) if latencies_sorted else 0,
            "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
            "error_rate": round(len(errors) / total, 4),
            "category_distribution": dict(sorted(cat_dist.items(), key=lambda x: x[1], reverse=True)[:30]),
            "team_distribution": dict(team_dist),
            "latency_over_time": latency_over_time,
            "confidence_histogram": buckets,
            "uptime_hours": round(uptime, 2),
            "throughput_per_hour": round(total / uptime, 1) if uptime > 0 else total
        }

    def get_trends(self, days: int = 7) -> Dict[str, Any]:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent = [e for e in self.entries if e.get("timestamp", "") >= cutoff]

        cat_counts = defaultdict(int)
        for e in recent:
            for c in e.get("categories", []):
                cat_name = c.get("category", "unknown")
                cat_counts[cat_name] += 1

        day_buckets = defaultdict(lambda: defaultdict(int))
        for e in recent:
            ts = e.get("timestamp", "")
            if ts:
                try:
                    day = datetime.fromisoformat(ts).strftime("%Y-%m-%d")
                    for c in e.get("categories", []):
                        cat_name = c.get("category", "unknown")
                        day_buckets[day][cat_name] += 1
                except ValueError:
                    pass

        sentiment_counts = defaultdict(int)
        for e in recent:
            for c in e.get("categories", []):
                cat_name = c.get("category", "unknown")
                sentiment_counts[cat_name] += 1

        return {
            "total_in_period": len(recent),
            "category_counts": dict(sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)),
            "daily_breakdown": {k: dict(v) for k, v in sorted(day_buckets.items())},
            "needs_review_count": sum(1 for e in recent if e.get("needs_review")),
            "avg_confidence": round(
                sum(e.get("confidence", 0) for e in recent if e.get("confidence")) / max(len(recent), 1), 3
            ),
            "period_days": days
        }


metrics_service = MetricsService()
