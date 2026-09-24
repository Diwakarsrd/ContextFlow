"""The `contextflow` CLI.

contextflow init
contextflow ingest ./docs
contextflow search "payments architecture"
contextflow serve
contextflow mcp
contextflow evaluate --benchmark benchmarks/datasets/acme_support_v1.yaml
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from contextflow.connectors.filesystem.connector import FilesystemConnector
from contextflow.engine import local_workspace

app = typer.Typer(
    name="contextflow",
    help="ContextFlow — open-source context infrastructure for AI agents.",
    add_completion=False,
)
console = Console()

_STATE_FILE = Path(".contextflow") / "state.json"

# The CLI uses `contextflow.engine.local_workspace()` — a persistent,
# dependency-free workspace (SQLite metadata + JSON vector/graph files
# under ./.contextflow/). This is what makes `contextflow ingest` and
# `contextflow search` share state across separate process invocations.


@app.command()
def demo() -> None:
    """Set up a sample workspace and run ingest -> search -> context-pack
    against it, so a new user sees the whole flow work in one command
    with zero setup. Writes sample docs to ./contextflow-demo/docs and a
    workspace to ./contextflow-demo/.contextflow — safe to delete afterward."""
    demo_dir = Path("contextflow-demo")
    docs_dir = demo_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    (docs_dir / "architecture.md").write_text(
        "Stripe was selected as the payment processor for Acme Corp.\n"
        "The migration is planned for Q4. The Payments Team owns this service.\n"
    )
    (docs_dir / "support.md").write_text(
        "Customers may request a full refund within 30 days of purchase.\n"
        "After 30 days, refunds are issued as store credit only.\n"
        "Support is available Monday through Friday, 9am to 6pm ET.\n"
    )

    console.print(f"[bold green]Created[/] sample docs in {docs_dir}/")

    engine = local_workspace(str(demo_dir / ".contextflow"))

    console.print("\n[bold]$ contextflow ingest[/] contextflow-demo/docs")
    connector = FilesystemConnector(config={"path": str(docs_dir)})
    count = engine.sync(connector)
    console.print(f"Ingested {count} chunks")

    console.print('\n[bold]$ contextflow search[/] "payment decisions"')
    results = engine.retrieve("payment decisions", limit=5)
    table = Table()
    table.add_column("Source", style="cyan")
    table.add_column("Content")
    for obj in results:
        table.add_row(obj.source, obj.content[:100] + ("…" if len(obj.content) > 100 else ""))
    console.print(table)

    console.print(
        '\n[bold]$ contextflow context-pack[/] "What decisions were made about payments?"'
    )
    pack = engine.context_pack("What decisions were made about payments?", max_tokens=1000)
    lines = [f"[bold]Query:[/] {pack.task}"]
    for bucket_name in ["facts", "documents", "conversations", "decisions", "risks"]:
        bucket = getattr(pack, bucket_name)
        if bucket:
            lines.append("")
            lines.append(f"[bold]{bucket_name.capitalize()}[/]")
            for item in bucket:
                snippet = item["content"][:80] + ("…" if len(item["content"]) > 80 else "")
                lines.append(f"  • {snippet}")
    lines.append("")
    lines.append(f"[bold]Confidence:[/] {pack.confidence:.0%}")
    console.print(Panel("\n".join(lines), title="Context Pack", expand=False))

    console.print(
        f"\n[dim]Demo workspace is at ./{demo_dir}/ — re-run "
        f'`contextflow search "<query>" --path {demo_dir}/.contextflow` yourself, '
        f"or delete the directory when done.[/]"
    )


@app.command()
def init() -> None:
    """Set up a local-first ContextFlow workspace (no cloud account needed)."""
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps({"initialized": True}))
    console.print("[bold green]Initialized[/] ContextFlow in ./.contextflow")
    console.print("  (persistent SQLite metadata + local vector/graph files)")
    console.print("Next: [bold]contextflow ingest <path>[/]")


@app.command()
def ingest(
    path: str = typer.Argument(..., help="Directory to ingest"),
    workspace: str = typer.Option(".contextflow", "--path", help="Workspace directory to use"),
) -> None:
    """Ingest a local directory of files into the engine."""
    engine = local_workspace(workspace)
    connector = FilesystemConnector(config={"path": path})
    count = engine.sync(connector)
    console.print(f"[bold green]Ingested[/] {count} chunks from {path}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, help="Max results"),
    workspace: str = typer.Option(".contextflow", "--path", help="Workspace directory to use"),
) -> None:
    """Search ingested context."""
    engine = local_workspace(workspace)
    results = engine.retrieve(query, limit=limit)
    if not results:
        console.print("[yellow]No results.[/] Have you run `contextflow ingest <path>` yet?")
        return
    table = Table(title=f'Results for "{query}"')
    table.add_column("Source", style="cyan")
    table.add_column("Content")
    for obj in results:
        table.add_row(obj.source, obj.content[:100] + ("…" if len(obj.content) > 100 else ""))
    console.print(table)


@app.command(name="context-pack")
def context_pack_cmd(
    task: str = typer.Argument(..., help="Task or question to build a Context Pack for"),
    entity: str = typer.Option(None, help="Optional entity to scope the pack to"),
    max_tokens: int = typer.Option(1000, help="Token budget"),
    workspace: str = typer.Option(".contextflow", "--path", help="Workspace directory to use"),
) -> None:
    """Build and pretty-print a Context Pack for a task."""
    engine = local_workspace(workspace)
    pack = engine.context_pack(task=task, entity=entity, max_tokens=max_tokens)

    lines = [f"[bold]Query:[/] {pack.task}"]
    for bucket_name in ["facts", "documents", "conversations", "decisions", "risks"]:
        bucket = getattr(pack, bucket_name)
        if bucket:
            lines.append("")
            lines.append(f"[bold]{bucket_name.capitalize()}[/]")
            for item in bucket:
                snippet = item["content"][:80] + ("…" if len(item["content"]) > 80 else "")
                lines.append(f"  • {snippet}")
    if pack.sources:
        lines.append("")
        lines.append("[bold]Sources[/]")
        for source in pack.sources:
            lines.append(f"  • {source}")
    lines.append("")
    lines.append(f"[bold]Confidence:[/] {pack.confidence:.0%}")

    console.print(Panel("\n".join(lines), title="Context Pack", expand=False))


@app.command()
def trace(
    query: str = typer.Argument(..., help="Query to trace through the retrieval pipeline"),
    limit: int = typer.Option(10, help="Max results"),
    workspace: str = typer.Option(".contextflow", "--path", help="Workspace directory to use"),
) -> None:
    """Run a query with full pipeline tracing: candidates in/out of each
    stage (routing, permission/tenant filtering, reranking, compile),
    plus timing."""
    engine = local_workspace(workspace)
    _pack, trace_obj = engine.context_pack_with_trace(query, max_tokens=1000, limit=limit)

    lines = [f"[bold]Query:[/] {query}", ""]
    for stage in trace_obj.stages:
        arrow = " " * 4 + "↓"
        detail_str = (
            f" ({', '.join(f'{k}={v}' for k, v in stage.details.items())})" if stage.details else ""
        )
        lines.append(
            f"{stage.count_out} after {stage.name}{detail_str}  [{stage.duration_ms:.1f}ms]"
        )
        lines.append(arrow)
    if lines[-1].strip() == "↓":
        lines.pop()  # no trailing arrow after the last stage
    lines.append("")
    if trace_obj.final_confidence is not None:
        lines.append(f"[bold]Confidence:[/] {trace_obj.final_confidence:.0%}")
    if trace_obj.final_tokens is not None:
        lines.append(f"[bold]Tokens:[/] {trace_obj.final_tokens}")
    lines.append(f"[bold]Total time:[/] {trace_obj.total_duration_ms:.1f}ms")

    console.print(Panel("\n".join(lines), title="Context Trace", expand=False))


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000),
    workspace: str = typer.Option(".contextflow", "--path", help="Workspace directory to use"),
) -> None:
    """Run the REST API server over the workspace `contextflow ingest` wrote."""
    import uvicorn

    from contextflow.api.app import create_app

    uvicorn.run(create_app(engine=local_workspace(workspace)), host=host, port=port)


@app.command()
def mcp(
    transport: str = typer.Option(
        "stdio", help="'stdio' (default, local) or 'http' (remote agents)"
    ),
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8765),
    workspace: str = typer.Option(
        ".contextflow",
        "--path",
        help="Workspace directory to use (pass an absolute path when an MCP "
        "client like Claude Desktop launches this, since its working directory varies)",
    ),
) -> None:
    """Run the MCP server so agents (Claude, Cursor, ...) can connect.

    Over stdio (default), no auth is needed — the trust boundary is
    "who can run this process." Over http, real Bearer-token auth is
    enforced once you've run `contextflow auth create-key`.
    """
    from contextflow.mcp.server import main as mcp_main

    mcp_main(transport=transport, host=host, port=port, engine=local_workspace(workspace))


auth_app = typer.Typer(help="Manage API keys shared by the REST API and MCP-over-HTTP.")
app.add_typer(auth_app, name="auth")


@auth_app.command("create-key")
def auth_create_key(
    principal: str = typer.Argument(..., help="Identity this key authenticates as"),
    expires_in_days: int = typer.Option(
        None, help="Optional expiry in days from now (default: never expires)"
    ),
) -> None:
    """Generate an API key for `principal`. Only the hash is persisted to
    .contextflow/api_keys.json — this is the only time the plaintext key is
    shown; store it now."""
    from contextflow.auth.api_keys import APIKeyStore

    store = APIKeyStore.from_env_and_file()
    key = store.create_key(principal, expires_in_days=expires_in_days)
    console.print(f"[bold green]Created key for '{principal}':[/] {key}")
    console.print(f"Use it as: Authorization: Bearer {key}")
    if expires_in_days:
        console.print(f"Expires in {expires_in_days} day(s).")
    console.print(
        "[yellow]This key will not be shown again[/] — only its hash is saved. "
        "Store it now (e.g. a secrets manager); `contextflow auth revoke-key` to invalidate it."
    )


@auth_app.command("revoke-key")
def auth_revoke_key(
    key: str = typer.Argument(..., help="The plaintext API key to revoke"),
) -> None:
    """Revoke an API key so it can no longer authenticate."""
    from contextflow.auth.api_keys import APIKeyStore

    store = APIKeyStore.from_env_and_file()
    if store.revoke_key(key):
        console.print("[bold green]Revoked.[/]")
    else:
        console.print("[yellow]No matching key found (already revoked or never existed).[/]")


@app.command()
def evaluate(
    benchmark: str = typer.Option(
        "benchmarks/datasets/acme_support_v1.yaml", help="Path to benchmark file"
    ),
    output: str = typer.Option(
        None, help="Save results as JSON to this path (for later comparison)"
    ),
    compare_to: str = typer.Option(
        None, help="Compare against a previously saved result JSON file"
    ),
) -> None:
    """Run the ContextBench evaluation harness against a benchmark dataset."""
    from contextflow.evaluation.benchmarks import (
        compare_results,
        load_result,
        run_benchmark,
        save_result,
    )

    result = run_benchmark(benchmark)

    table = Table(title=f"ContextBench: {result.name} ({result.num_queries} queries)")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Recall@5", f"{result.recall:.1%}")
    table.add_row("Precision@5", f"{result.precision:.1%}")
    table.add_row("MRR", f"{result.mrr:.3f}")
    table.add_row("NDCG@5", f"{result.ndcg:.3f}")
    table.add_row("Avg context tokens", f"{result.avg_tokens:.0f}")
    console.print(table)

    if compare_to:
        baseline = load_result(compare_to)
        deltas = compare_results(baseline, result)
        delta_table = Table(title=f"vs. {compare_to}")
        delta_table.add_column("Metric")
        delta_table.add_column("Delta", justify="right")
        for metric, delta in deltas.items():
            sign = "+" if delta >= 0 else ""
            style = "green" if delta > 0 else ("red" if delta < 0 else "")
            delta_table.add_row(
                metric, f"[{style}]{sign}{delta:.3f}[/]" if style else f"{sign}{delta:.3f}"
            )
        console.print(delta_table)

    if output:
        save_result(result, output)
        console.print(f"Saved results to {output}")


@auth_app.command("assign-role")
def auth_assign_role(
    principal: str = typer.Argument(..., help="Principal to grant the role to"),
    role: str = typer.Argument(..., help="Role name, e.g. 'admin' or 'analyst'"),
) -> None:
    """Grant a role to a principal (stored in .contextflow/roles.json)."""
    from contextflow.governance.policies import RoleStore

    store = RoleStore()
    store.assign(principal, role)
    console.print(f"[bold green]Granted[/] role '{role}' to '{principal}'")


@auth_app.command("roles")
def auth_list_roles(
    principal: str = typer.Argument(..., help="Principal to look up"),
) -> None:
    """List roles held by a principal."""
    from contextflow.governance.policies import RoleStore

    store = RoleStore()
    roles = store.roles_for(principal)
    console.print(f"{principal}: {', '.join(roles) if roles else '(no roles)'}")


memory_app = typer.Typer(help="Store and recall facts in session/user/agent/org memory.")
app.add_typer(memory_app, name="memory")


@memory_app.command("remember")
def memory_remember(
    scope: str = typer.Argument(..., help="session | user | agent | org"),
    scope_id: str = typer.Argument(..., help="Identifier within that scope, e.g. a user id"),
    fact: str = typer.Argument(..., help="The fact to remember"),
) -> None:
    """Store a fact in memory."""
    from contextflow.memory.store import MemoryStore

    store = MemoryStore()
    entry_id = store.remember(scope, scope_id, fact)
    console.print(f"[bold green]Remembered[/] ({entry_id[:8]}…): {fact}")


@memory_app.command("recall")
def memory_recall(
    scope: str = typer.Argument(..., help="session | user | agent | org"),
    scope_id: str = typer.Argument(..., help="Identifier within that scope"),
    query: str = typer.Option(
        None, help="Optional keyword query; omit to list all, most recent first"
    ),
    limit: int = typer.Option(10),
) -> None:
    """Recall facts from memory."""
    from contextflow.memory.store import MemoryStore

    store = MemoryStore()
    entries = store.recall(scope, scope_id, query, limit)
    if not entries:
        console.print(f"[yellow]No memories for {scope}/{scope_id}.[/]")
        return
    table = Table(title=f"Memory: {scope}/{scope_id}")
    table.add_column("Fact")
    for entry in entries:
        table.add_row(entry.content)
    console.print(table)


audit_app = typer.Typer(help="Query the audit log.")
app.add_typer(audit_app, name="audit")


@audit_app.command("query")
def audit_query(
    principal: str = typer.Option(None, help="Filter by principal"),
    action: str = typer.Option(None, help="Filter by action (search, context_pack, ...)"),
) -> None:
    """Query the audit log."""
    from contextflow.governance.audit import AuditLog

    log = AuditLog()
    entries = log.query(principal=principal, action=action)
    if not entries:
        console.print("[yellow]No matching audit entries.[/]")
        return
    table = Table(title="Audit Log")
    table.add_column("Time")
    table.add_column("Principal")
    table.add_column("Action")
    table.add_column("Details")
    for entry in entries:
        import datetime

        ts = datetime.datetime.fromtimestamp(entry["ts"], tz=datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        details = {k: v for k, v in entry.items() if k not in ("ts", "principal", "action")}
        table.add_row(ts, entry["principal"], entry["action"], str(details))
    console.print(table)


@app.command(name="benchmark-scale")
def benchmark_scale(
    sizes: str = typer.Option("100,500,1000,2000", help="Comma-separated corpus sizes to test"),
    persistent: bool = typer.Option(
        False, help="Use the persistent (SQLite+file) backend instead of in-memory"
    ),
) -> None:
    """Measure real ingestion throughput and retrieval latency at
    increasing corpus sizes. See benchmarks/performance/results.md for
    previously captured numbers and their methodology/caveats."""
    import tempfile

    from contextflow.engine import ContextEngine, local_workspace
    from contextflow.evaluation.performance import run_scale_sweep

    size_list = [int(s.strip()) for s in sizes.split(",")]

    if persistent:

        def factory():
            return local_workspace(tempfile.mkdtemp())
    else:

        def factory():
            return ContextEngine()

    console.print(
        f"Running scale sweep: {size_list} ({'persistent' if persistent else 'in-memory'} backend)..."
    )
    result = run_scale_sweep(size_list, factory)

    table = Table(title="Performance / Scale Benchmark")
    table.add_column("Corpus size", justify="right")
    table.add_column("Ingest (docs/s)", justify="right")
    table.add_column("Retrieval p50", justify="right")
    table.add_column("Retrieval p95", justify="right")
    table.add_column("Retrieval p99", justify="right")
    for p in result.points:
        table.add_row(
            str(p.corpus_size),
            f"{p.ingest_throughput_per_sec:,.0f}",
            f"{p.retrieval_latency.p50_ms:.2f}ms",
            f"{p.retrieval_latency.p95_ms:.2f}ms",
            f"{p.retrieval_latency.p99_ms:.2f}ms",
        )
    console.print(table)
    console.print(
        "[dim]Single-machine, single-run numbers. See "
        "benchmarks/performance/results.md for methodology and caveats.[/]"
    )


@app.command()
def connectors() -> None:
    """List available connectors."""
    console.print("Built-in (v0.1): github, postgres, filesystem, slack, notion")
    console.print("  slack/notion are untested against live workspaces — see docs/integrations/")
    console.print("See CONTRIBUTING.md to add more.")


if __name__ == "__main__":
    app()
