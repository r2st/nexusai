#!/usr/bin/env python3
"""
NexusAI Load Test Results Analyzer
===================================
Parses Locust CSV and k6 JSON results, validates SLA compliance,
and generates an HTML report with charts.

Usage:
    python analyze_results.py --results-dir ./results/20240101_120000
    python analyze_results.py --results-dir ./results/latest --profile spike
"""

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class SLAThresholds:
    p50_ms: int = 100
    p95_ms: int = 200
    p99_ms: int = 500
    max_ms: int = 2000
    error_rate_pct: float = 1.0
    min_rps: int = 500


@dataclass
class EndpointResult:
    name: str
    method: str = "GET"
    requests: int = 0
    failures: int = 0
    avg_ms: float = 0
    min_ms: float = 0
    max_ms: float = 0
    median_ms: float = 0
    p95_ms: float = 0
    p99_ms: float = 0
    rps: float = 0
    error_rate: float = 0


@dataclass
class TestSummary:
    timestamp: str = ""
    profile: str = "unknown"
    target_users: int = 0
    duration_seconds: int = 0
    total_requests: int = 0
    total_failures: int = 0
    overall_rps: float = 0
    overall_avg_ms: float = 0
    overall_p50_ms: float = 0
    overall_p95_ms: float = 0
    overall_p99_ms: float = 0
    overall_max_ms: float = 0
    error_rate_pct: float = 0
    endpoints: list = field(default_factory=list)
    sla_pass: bool = False
    sla_violations: list = field(default_factory=list)


def parse_locust_stats(results_dir: str) -> Optional[TestSummary]:
    """Parse Locust CSV stats files."""
    stats_file = None
    for pattern in ["locust_stats.csv", "*_stats.csv"]:
        matches = list(Path(results_dir).glob(pattern))
        if matches:
            stats_file = matches[0]
            break

    if not stats_file:
        return None

    summary = TestSummary(timestamp=datetime.now().isoformat())
    endpoints = []

    with open(stats_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "")
            req_type = row.get("Type", "GET")

            if name == "Aggregated":
                summary.total_requests = int(row.get("Request Count", 0))
                summary.total_failures = int(row.get("Failure Count", 0))
                summary.overall_avg_ms = float(row.get("Average Response Time", 0))
                summary.overall_p50_ms = float(row.get("50%", 0))
                summary.overall_p95_ms = float(row.get("95%", 0) or row.get("99%", 0))
                summary.overall_p99_ms = float(row.get("99%", 0))
                summary.overall_max_ms = float(row.get("Max Response Time", 0))
                summary.overall_rps = float(row.get("Requests/s", 0))
                if summary.total_requests > 0:
                    summary.error_rate_pct = (
                        summary.total_failures / summary.total_requests * 100
                    )
            else:
                ep = EndpointResult(
                    name=name,
                    method=req_type,
                    requests=int(row.get("Request Count", 0)),
                    failures=int(row.get("Failure Count", 0)),
                    avg_ms=float(row.get("Average Response Time", 0)),
                    min_ms=float(row.get("Min Response Time", 0)),
                    max_ms=float(row.get("Max Response Time", 0)),
                    median_ms=float(row.get("50%", 0)),
                    p95_ms=float(row.get("95%", 0) or 0),
                    p99_ms=float(row.get("99%", 0) or 0),
                    rps=float(row.get("Requests/s", 0)),
                )
                if ep.requests > 0:
                    ep.error_rate = ep.failures / ep.requests * 100
                endpoints.append(ep)

    summary.endpoints = endpoints
    return summary


def parse_k6_summary(results_dir: str) -> Optional[TestSummary]:
    """Parse k6 JSON summary."""
    summary_file = None
    for pattern in ["k6_summary.json", "*k6_summary*.json"]:
        matches = list(Path(results_dir).glob(pattern))
        if matches:
            summary_file = matches[0]
            break

    if not summary_file:
        return None

    with open(summary_file, "r") as f:
        data = json.load(f)

    summary = TestSummary(
        timestamp=data.get("timestamp", datetime.now().isoformat()),
        profile=data.get("profile", "unknown"),
        target_users=data.get("max_vus", 0),
        total_requests=data.get("total_requests", 0),
    )

    rt = data.get("response_times", {})
    summary.overall_p50_ms = rt.get("p50_ms", 0)
    summary.overall_p95_ms = rt.get("p95_ms", 0)
    summary.overall_p99_ms = rt.get("p99_ms", 0)
    summary.overall_avg_ms = rt.get("avg_ms", 0)
    summary.error_rate_pct = data.get("error_rate", 0)

    return summary


def validate_sla(summary: TestSummary, sla: SLAThresholds) -> TestSummary:
    """Validate results against SLA thresholds."""
    violations = []

    if summary.overall_p95_ms > sla.p95_ms:
        violations.append(
            f"P95 latency {summary.overall_p95_ms:.1f}ms exceeds {sla.p95_ms}ms limit"
        )

    if summary.overall_p99_ms > sla.p99_ms:
        violations.append(
            f"P99 latency {summary.overall_p99_ms:.1f}ms exceeds {sla.p99_ms}ms limit"
        )

    if summary.error_rate_pct > sla.error_rate_pct:
        violations.append(
            f"Error rate {summary.error_rate_pct:.2f}% exceeds {sla.error_rate_pct}% limit"
        )

    if summary.overall_rps > 0 and summary.overall_rps < sla.min_rps:
        violations.append(
            f"Throughput {summary.overall_rps:.1f} RPS below {sla.min_rps} RPS minimum"
        )

    # Per-endpoint P95 checks
    for ep in summary.endpoints:
        if ep.p95_ms > sla.p95_ms and ep.requests > 10:
            violations.append(
                f"Endpoint '{ep.name}' P95 {ep.p95_ms:.1f}ms exceeds {sla.p95_ms}ms"
            )

    summary.sla_violations = violations
    summary.sla_pass = len(violations) == 0
    return summary


def generate_html_report(
    summary: TestSummary,
    sla: SLAThresholds,
    output_path: str,
    profile: str = "",
    users: int = 0,
    duration: int = 0,
) -> None:
    """Generate an HTML report with test results."""
    sla_status = "PASS" if summary.sla_pass else "FAIL"
    sla_color = "#22c55e" if summary.sla_pass else "#ef4444"

    endpoints_rows = ""
    for ep in sorted(summary.endpoints, key=lambda e: e.p95_ms, reverse=True):
        p95_color = "#22c55e" if ep.p95_ms <= sla.p95_ms else "#ef4444"
        err_color = "#22c55e" if ep.error_rate <= sla.error_rate_pct else "#ef4444"
        endpoints_rows += f"""
        <tr>
            <td>{ep.method}</td>
            <td>{ep.name}</td>
            <td>{ep.requests:,}</td>
            <td>{ep.avg_ms:.1f}</td>
            <td>{ep.median_ms:.1f}</td>
            <td style="color:{p95_color};font-weight:bold">{ep.p95_ms:.1f}</td>
            <td>{ep.p99_ms:.1f}</td>
            <td>{ep.max_ms:.1f}</td>
            <td>{ep.rps:.1f}</td>
            <td style="color:{err_color}">{ep.error_rate:.2f}%</td>
        </tr>"""

    violations_html = ""
    if summary.sla_violations:
        violations_html = '<div class="violations"><h3>SLA Violations</h3><ul>'
        for v in summary.sla_violations:
            violations_html += f"<li>{v}</li>"
        violations_html += "</ul></div>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NexusAI Load Test Report - {profile}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #0f172a; color: #e2e8f0; padding: 2rem; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ font-size: 2rem; margin-bottom: 0.5rem; color: #f8fafc; }}
        h2 {{ font-size: 1.3rem; margin-bottom: 1rem; color: #94a3b8; }}
        h3 {{ color: #f8fafc; margin-bottom: 0.5rem; }}
        .header {{ text-align: center; padding: 2rem 0; border-bottom: 1px solid #1e293b; margin-bottom: 2rem; }}
        .sla-badge {{ display: inline-block; padding: 0.5rem 2rem; border-radius: 9999px;
                     font-size: 1.5rem; font-weight: bold; color: white; background: {sla_color};
                     margin: 1rem 0; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 1rem; margin-bottom: 2rem; }}
        .metric-card {{ background: #1e293b; border-radius: 12px; padding: 1.5rem; text-align: center; }}
        .metric-value {{ font-size: 2rem; font-weight: bold; color: #f8fafc; }}
        .metric-label {{ font-size: 0.85rem; color: #64748b; margin-top: 0.25rem; }}
        .metric-sla {{ font-size: 0.75rem; color: #94a3b8; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        th {{ background: #1e293b; padding: 0.75rem; text-align: left; font-size: 0.85rem;
             color: #94a3b8; border-bottom: 2px solid #334155; }}
        td {{ padding: 0.75rem; border-bottom: 1px solid #1e293b; font-size: 0.9rem; }}
        tr:hover {{ background: #1e293b44; }}
        .violations {{ background: #7f1d1d33; border: 1px solid #ef4444; border-radius: 12px;
                      padding: 1.5rem; margin: 1.5rem 0; }}
        .violations li {{ color: #fca5a5; margin: 0.5rem 0 0.5rem 1.5rem; }}
        .section {{ background: #1e293b; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; }}
        .timestamp {{ color: #64748b; font-size: 0.85rem; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>NexusAI Load Test Report</h1>
        <h2>Profile: {profile or summary.profile} | {users or summary.target_users:,} Users | {duration or summary.duration_seconds}s</h2>
        <div class="sla-badge">SLA: {sla_status}</div>
        <div class="timestamp">Generated: {summary.timestamp}</div>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-value" style="color:{'#22c55e' if summary.overall_p95_ms <= sla.p95_ms else '#ef4444'}">{summary.overall_p95_ms:.1f}ms</div>
            <div class="metric-label">P95 Response Time</div>
            <div class="metric-sla">SLA: &lt;{sla.p95_ms}ms</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{summary.overall_p50_ms:.1f}ms</div>
            <div class="metric-label">P50 (Median)</div>
            <div class="metric-sla">SLA: &lt;{sla.p50_ms}ms</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{summary.overall_p99_ms:.1f}ms</div>
            <div class="metric-label">P99 Response Time</div>
            <div class="metric-sla">SLA: &lt;{sla.p99_ms}ms</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{summary.total_requests:,}</div>
            <div class="metric-label">Total Requests</div>
            <div class="metric-sla">&nbsp;</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:{'#22c55e' if summary.error_rate_pct <= sla.error_rate_pct else '#ef4444'}">{summary.error_rate_pct:.2f}%</div>
            <div class="metric-label">Error Rate</div>
            <div class="metric-sla">SLA: &lt;{sla.error_rate_pct}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{summary.overall_rps:.1f}</div>
            <div class="metric-label">Requests/sec</div>
            <div class="metric-sla">SLA: &gt;{sla.min_rps}/s</div>
        </div>
    </div>

    {violations_html}

    <div class="section">
        <h3>Endpoint Breakdown</h3>
        <table>
            <thead>
                <tr>
                    <th>Method</th>
                    <th>Endpoint</th>
                    <th>Requests</th>
                    <th>Avg (ms)</th>
                    <th>Median (ms)</th>
                    <th>P95 (ms)</th>
                    <th>P99 (ms)</th>
                    <th>Max (ms)</th>
                    <th>RPS</th>
                    <th>Error %</th>
                </tr>
            </thead>
            <tbody>
                {endpoints_rows if endpoints_rows else '<tr><td colspan="10" style="text-align:center;color:#64748b">No per-endpoint data available (use Locust for detailed breakdown)</td></tr>'}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h3>Test Configuration</h3>
        <table>
            <tr><td><strong>Profile</strong></td><td>{profile or summary.profile}</td></tr>
            <tr><td><strong>Target Users</strong></td><td>{users or summary.target_users:,}</td></tr>
            <tr><td><strong>Duration</strong></td><td>{duration or summary.duration_seconds}s</td></tr>
            <tr><td><strong>P95 SLA Target</strong></td><td>&lt;{sla.p95_ms}ms</td></tr>
            <tr><td><strong>Error Rate SLA</strong></td><td>&lt;{sla.error_rate_pct}%</td></tr>
        </table>
    </div>
</div>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)


def print_console_report(summary: TestSummary, sla: SLAThresholds) -> None:
    """Print a formatted console report."""
    status = "PASS" if summary.sla_pass else "FAIL"
    status_icon = "\u2705" if summary.sla_pass else "\u274c"

    print()
    print("=" * 64)
    print("           NexusAI LOAD TEST ANALYSIS REPORT")
    print("=" * 64)
    print(f"  Profile:         {summary.profile}")
    print(f"  Target Users:    {summary.target_users:,}")
    print(f"  Total Requests:  {summary.total_requests:,}")
    print(f"  Total Failures:  {summary.total_failures:,}")
    print("-" * 64)
    print("  RESPONSE TIMES")
    print(f"  P50 (Median):    {summary.overall_p50_ms:.1f}ms  (SLA: <{sla.p50_ms}ms)")
    print(f"  P95:             {summary.overall_p95_ms:.1f}ms  (SLA: <{sla.p95_ms}ms)  <- KEY")
    print(f"  P99:             {summary.overall_p99_ms:.1f}ms  (SLA: <{sla.p99_ms}ms)")
    print(f"  Average:         {summary.overall_avg_ms:.1f}ms")
    print(f"  Max:             {summary.overall_max_ms:.1f}ms")
    print("-" * 64)
    print(f"  Error Rate:      {summary.error_rate_pct:.2f}%  (SLA: <{sla.error_rate_pct}%)")
    print(f"  Throughput:      {summary.overall_rps:.1f} req/s  (SLA: >{sla.min_rps}/s)")
    print("-" * 64)

    if summary.sla_violations:
        print(f"  {status_icon} SLA: {status}")
        for v in summary.sla_violations:
            print(f"    - {v}")
    else:
        print(f"  {status_icon} SLA: {status} - All targets met")

    print("=" * 64)

    # Top 5 slowest endpoints
    if summary.endpoints:
        print("\n  TOP 5 SLOWEST ENDPOINTS (by P95)")
        print("-" * 64)
        for ep in sorted(summary.endpoints, key=lambda e: e.p95_ms, reverse=True)[:5]:
            marker = " <-- OVER SLA" if ep.p95_ms > sla.p95_ms else ""
            print(f"  {ep.method:6s} {ep.name:40s} P95={ep.p95_ms:.0f}ms{marker}")
        print()


def main():
    parser = argparse.ArgumentParser(description="NexusAI Load Test Analyzer")
    parser.add_argument("--results-dir", required=True, help="Path to results directory")
    parser.add_argument("--profile", default="unknown", help="Test profile name")
    parser.add_argument("--users", type=int, default=0, help="Target user count")
    parser.add_argument("--duration", type=int, default=0, help="Test duration (seconds)")
    parser.add_argument("--output", default=None, help="Output HTML report path")
    parser.add_argument(
        "--p95-threshold", type=int, default=200, help="P95 SLA threshold in ms"
    )
    args = parser.parse_args()

    sla = SLAThresholds(p95_ms=args.p95_threshold)

    # Try Locust results first, then k6
    summary = parse_locust_stats(args.results_dir)
    source = "Locust"

    if not summary:
        summary = parse_k6_summary(args.results_dir)
        source = "k6"

    if not summary:
        print("No test results found in", args.results_dir)
        sys.exit(1)

    summary.profile = args.profile
    summary.target_users = args.users or summary.target_users
    summary.duration_seconds = args.duration or summary.duration_seconds

    summary = validate_sla(summary, sla)

    print(f"\n  Data source: {source}")
    print_console_report(summary, sla)

    if args.output:
        generate_html_report(
            summary, sla, args.output,
            profile=args.profile, users=args.users, duration=args.duration
        )
        print(f"  HTML report saved to: {args.output}\n")

    # Exit with error if SLA violated
    sys.exit(0 if summary.sla_pass else 1)


if __name__ == "__main__":
    main()
