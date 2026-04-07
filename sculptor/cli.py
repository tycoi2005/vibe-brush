"""Interactive CLI for the Open Brush AI Sculptor.

Provides a REPL where users type natural language prompts
and see them executed live in Open Brush.
"""

import logging
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.text import Text
from rich.table import Table

from .config import load_config, validate_config
from .llm_client import LLMClient
from .openbrush_client import OpenBrushClient, OpenBrushError
from .planner import StagedPlanner
from .executor import Executor


console = Console()

BANNER = """
[bold magenta]╔══════════════════════════════════════════════════════════╗[/]
[bold magenta]║[/]  [bold cyan]🎨 Open Brush AI Sculptor[/]                               [bold magenta]║[/]
[bold magenta]║[/]  [dim]Create 3D art with natural language[/]                     [bold magenta]║[/]
[bold magenta]╚══════════════════════════════════════════════════════════╝[/]
"""

HELP_TEXT = """
[bold cyan]Commands:[/]
  [bold green]/new[/]       — Clear sketch and start fresh
  [bold green]/save[/]      — Save current sketch (optionally: /save myname)
  [bold green]/export[/]    — Export sketch to glTF/OBJ
  [bold green]/undo[/]      — Undo last action
  [bold green]/redo[/]      — Redo last action
  [bold green]/status[/]    — Check Open Brush connection
  [bold green]/refine[/]    — Refine the last artwork (e.g., /refine make it bigger)
  [bold green]/reset[/]     — Reset session memory and conversation history
  [bold green]/help[/]      — Show this help
  [bold green]/quit[/]      — Exit

[bold cyan]Usage:[/]
  Just type what you want to create! The agent runs 4 stages automatically:
  [bold]💡 Ideas → ✏️ Sketch → 🖼️ Overall → ✨ Details[/]

  Examples:
  • [italic]"draw a glowing spiral tower"[/]
  • [italic]"create a fractal tree with autumn colors"[/]
  • [italic]"make a wireframe sphere with orbiting rings"[/]
  • [italic]"build a mountain landscape with a sunset"[/]
"""


def check_connection(client: OpenBrushClient) -> bool:
    """Check and display Open Brush connection status."""
    if client.is_connected():
        console.print("  [green]✓[/] Connected to Open Brush")
        return True
    else:
        console.print("  [red]✗[/] Cannot connect to Open Brush")
        console.print("    [dim]Make sure Open Brush is running with API enabled.[/]")
        console.print("    [dim]See: docs/install_openbrush.md[/]")
        return False


def display_plan(plan):
    """Display an art plan summary to the user."""
    table = Table(title=f"🎨 {plan.title}", show_lines=False, expand=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Action", style="cyan")
    table.add_column("Details", style="white")

    for i, step in enumerate(plan.steps):
        action = step.get("action", "?")
        # Build details string
        details_parts = []
        for k, v in step.items():
            if k == "action":
                continue
            if isinstance(v, list) and len(v) <= 3:
                details_parts.append(f"{k}={v}")
            elif isinstance(v, list):
                details_parts.append(f"{k}=[{len(v)} items]")
            else:
                details_parts.append(f"{k}={v}")
        details = ", ".join(details_parts) if details_parts else ""
        table.add_row(str(i + 1), action, details)

    console.print(table)
    console.print(f"  [dim]{plan.description}[/]")


def run_cli(config_path: str | None = None):
    """Main CLI entry point."""
    console.print(BANNER)

    # Load config
    config = load_config(config_path)
    issues = validate_config(config)
    if issues:
        for issue in issues:
            console.print(f"  [yellow]⚠[/] {issue}")
        console.print()

        # Check if API key is missing
        if any("API key" in i for i in issues):
            console.print("[bold red]Cannot start without an LLM API key.[/]")
            console.print("Set OPENAI_API_KEY env var or configure config.yaml")
            console.print("See config.example.yaml for reference.")
            sys.exit(1)

    # Initialize components
    llm_config = config.get("llm", {})
    ob_config = config.get("openbrush", {})

    llm = _create_llm_client(llm_config)

    ob_client = OpenBrushClient(
        host=ob_config.get("host", "localhost"),
        port=ob_config.get("port", 40074),
        command_delay=ob_config.get("command_delay", 0.05),
    )

    planner = StagedPlanner(llm)

    console.print("[bold]Checking connections...[/]")
    console.print(f"  [dim]LLM: {llm_config.get('base_url')} ({llm_config.get('model')})[/]")
    ob_connected = check_connection(ob_client)
    console.print()

    if not ob_connected:
        console.print("[yellow]⚠ Open Brush is not connected. You can still generate plans,[/]")
        console.print("[yellow]  but execution will fail until Open Brush is running.[/]")
        console.print()

    console.print(HELP_TEXT)

    # REPL loop
    last_plan = None
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]🖌️  sculptor[/]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye! 👋[/]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # ── Handle commands ────────────────────────────────────
        if user_input.startswith("/"):
            cmd_parts = user_input.split(maxsplit=1)
            cmd = cmd_parts[0].lower()
            cmd_arg = cmd_parts[1] if len(cmd_parts) > 1 else ""

            if cmd in ("/quit", "/exit", "/q"):
                console.print("[dim]Goodbye! 👋[/]")
                break

            elif cmd == "/help":
                console.print(HELP_TEXT)

            elif cmd == "/new":
                try:
                    ob_client.new_sketch()
                    planner.reset_history()
                    last_plan = None
                    console.print("[green]✓[/] New sketch created")
                except OpenBrushError as e:
                    console.print(f"[red]✗[/] {e}")

            elif cmd == "/save":
                try:
                    if cmd_arg:
                        ob_client.save(cmd_arg)
                        console.print(f"[green]✓[/] Saved as '{cmd_arg}'")
                    else:
                        ob_client.save_overwrite()
                        console.print("[green]✓[/] Saved")
                except OpenBrushError as e:
                    console.print(f"[red]✗[/] {e}")

            elif cmd == "/export":
                _handle_export_and_copy(ob_client, wait_time=2)

            elif cmd == "/undo":
                try:
                    ob_client.undo()
                    console.print("[green]✓[/] Undone")
                except OpenBrushError as e:
                    console.print(f"[red]✗[/] {e}")

            elif cmd == "/redo":
                try:
                    ob_client.redo()
                    console.print("[green]✓[/] Redone")
                except OpenBrushError as e:
                    console.print(f"[red]✗[/] {e}")

            elif cmd == "/status":
                check_connection(ob_client)

            elif cmd == "/reset":
                planner.reset_history()
                last_plan = None
                console.print("[green]✓[/] Conversation history cleared")

            elif cmd == "/refine":
                if not last_plan:
                    console.print("[yellow]No previous artwork to refine. Create something first![/]")
                    continue
                if not cmd_arg:
                    console.print("[yellow]Usage: /refine <feedback>[/]")
                    console.print("[dim]Example: /refine make the tree taller and add more branches[/]")
                    continue

                # Refine the last plan
                with console.status("[bold cyan]Thinking...[/]"):
                    try:
                        plan = planner.refine(cmd_arg)
                    except Exception as e:
                        console.print(f"[red]✗ LLM Error:[/] {e}")
                        continue

                display_plan(plan)

                # Ask for confirmation
                confirm = Prompt.ask("Execute this plan?", choices=["y", "n"], default="y")
                if confirm == "y":
                    _execute_plan(plan, ob_client, config)
                    last_plan = plan

            else:
                console.print(f"[yellow]Unknown command: {cmd}. Type /help for help.[/]")

            continue

        # ── Generate and execute art plan (4-stage auto-chain) ────
        confirm = Prompt.ask(
            "\n[bold cyan]🚀 Run 4-stage pipeline?[/] (💡ideas → ✏️sketch → 🖼️overall → ✨details)",
            choices=["y", "n"],
            default="y",
        )
        if confirm == "n":
            console.print("[dim]Cancelled.[/]")
            continue

        if sys.platform == "darwin":
            console.print("\n[bold yellow]👉 Quick! Click the Open Brush window to ensure it doesn't pause![/]")
            for i in range(3, 0, -1):
                console.print(f"[dim]Starting in {i}...[/]", end="\r")
                time.sleep(1)
            console.print(" " * 20, end="\r")

        # Stage 1 — Ideas
        console.print("\n[bold cyan]💡 Stage 1 — Ideation...[/]")
        with console.status("[dim]Thinking...[/]"):
            try:
                concept = planner.stage1_ideate(user_input)
            except Exception as e:
                console.print(f"[red]✗ Stage 1 Error:[/] {e}")
                continue
        console.print(Panel(concept, title="💡 Concept Brief", border_style="cyan", padding=(1, 2)))

        # Stage 2 — Sketch
        console.print("\n[bold cyan]✏️  Stage 2 — Rough Sketch...[/]")
        with console.status("[dim]Blocking...[/]"):
            try:
                sketch_plan = planner.stage2_sketch()
            except Exception as e:
                console.print(f"[red]✗ Stage 2 Error:[/] {e}")
                continue
        display_plan(sketch_plan)
        _execute_plan(sketch_plan, ob_client, config, stage_label="✏️  Sketch")

        # Stage 3 — Overall
        console.print("\n[bold cyan]🖼️  Stage 3 — Overall Drawing...[/]")
        with console.status("[dim]Composing...[/]"):
            try:
                overall_plan = planner.stage3_overall()
            except Exception as e:
                console.print(f"[red]✗ Stage 3 Error:[/] {e}")
                continue
        display_plan(overall_plan)
        _execute_plan(overall_plan, ob_client, config, stage_label="🖼️  Overall")

        # Stage 4 — Details
        console.print("\n[bold cyan]✨ Stage 4 — Detail Pass...[/]")
        with console.status("[dim]Polishing...[/]"):
            try:
                details_plan = planner.stage4_details()
            except Exception as e:
                console.print(f"[red]✗ Stage 4 Error:[/] {e}")
                continue
        display_plan(details_plan)
        _execute_plan(details_plan, ob_client, config, stage_label="✨ Details")

        last_plan = details_plan
        console.print("\n[bold green]🎉 Pipeline complete![/]")

        export_config = config.get("export", {})
        if export_config.get("auto_save"):
            try:
                ob_client.save_overwrite()
                console.print("  [dim]Auto-saved[/]")
            except OpenBrushError:
                pass
        if export_config.get("auto_export"):
            _handle_export_and_copy(ob_client, wait_time=2)


def _handle_export_and_copy(ob_client: OpenBrushClient, wait_time: int = 5):
    """Trigger Open Brush export, wait, copy to results, and auto-convert JSON to OBJ."""
    import shutil, os, sys
    from pathlib import Path
    try:
        console.print(f"  [dim]Exporting model. Waiting {wait_time}s for Open Brush to generate file...[/]")
        ob_client.export_current()
        time.sleep(wait_time)

        exports_dir = Path.home() / "Documents/Open Brush/Exports"
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)

        if exports_dir.exists():
            items = list(exports_dir.glob("*"))
            if not items:
                console.print("  [yellow]⚠ Export folder is empty! Open Brush might still be generating it.[/yellow]")
                return

            newest = max(items, key=os.path.getmtime)
            dest = results_dir / newest.name
            if newest.is_dir():
                if dest.exists(): shutil.rmtree(dest)
                shutil.copytree(newest, dest)
            else:
                shutil.copy2(newest, dest)
            console.print(f"  [green]✓[/] Exported and saved to: [cyan]{dest}[/cyan]")

            # Automatically convert JSON to OBJ if JSON exists
            try:
                from scripts.json_to_obj import convert_json_to_obj
                json_files = list(dest.rglob("*.json")) if dest.is_dir() else ([dest] if dest.suffix == ".json" else [])
                main_jsons = [jf for jf in json_files if not jf.name.endswith(".metadata.json")]

                for jf in main_jsons:
                    out_obj = jf.with_suffix(".obj")
                    if not out_obj.exists():
                        convert_json_to_obj(str(jf), str(out_obj))
                        console.print(f"  [green]✓[/] Auto-converted JSON to OBJ: [cyan]{out_obj}[/cyan]")
            except ImportError:
                console.print("  [dim yellow]json_to_obj script not found, skipping conversion.[/]")
            except Exception as e:
                console.print(f"  [dim yellow]JSON to OBJ conversion failed: {e}[/]")
        else:
            console.print(f"  [red]⚠ Cannot access {exports_dir}! MacOS might be blocking terminal access.[/red]")
    except OpenBrushError as e:
        console.print(f"  [red]✗ Export failed:[/red] {e}")
    except Exception as e:
        console.print(f"  [red]⚠ Export processing error: {e}[/red]")


def _execute_plan(plan, ob_client: OpenBrushClient, config: dict, stage_label: str = ""):
    """Execute a plan with progress display."""
    total = len(plan.steps)
    label = f"{stage_label} — Executing" if stage_label else "Executing"
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task(label, total=total)

        def on_step(i, total, desc):
            progress.update(task, completed=i, description=f"[cyan]{desc}[/]")

        executor = Executor(ob_client, on_step=on_step)
        results = executor.execute(plan)
        progress.update(task, completed=total, description="[green]Done![/]")

    # Show results
    console.print(f"\n  [green]✓[/] Completed: {results['completed']}/{results['total_steps']} steps")
    console.print(f"  [green]✓[/] Paths drawn: {results['paths_drawn']}")

    if results["errors"]:
        console.print(f"  [yellow]⚠ Errors: {len(results['errors'])}[/]")
        for err in results["errors"]:
            console.print(f"    [dim red]{err}[/]")


def setup_logging(debug: bool = False):
    """Configure logging: always log to file, optionally verbose to console."""
    log_dir = Path(".")  # log file in current directory
    log_file = log_dir / "sculptor.log"

    # Root sculptor logger
    logger = logging.getLogger("sculptor")
    logger.setLevel(logging.DEBUG)  # capture everything, handlers filter

    # File handler — always DEBUG level for full diagnostics
    fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(fh)

    # Console handler — INFO or DEBUG depending on flag
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.DEBUG if debug else logging.WARNING)
    ch.setFormatter(logging.Formatter("  [%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    logger.info("=" * 60)
    logger.info("Sculptor session started (debug=%s)", debug)
    logger.info("Log file: %s", log_file.resolve())

    return log_file


def main():
    """Entry point for the CLI."""
    import argparse
    parser = argparse.ArgumentParser(description="Open Brush AI Sculptor")
    parser.add_argument("-c", "--config", help="Path to config.yaml")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging to console")
    parser.add_argument(
        "--prompt", "-p",
        help="Execute a single prompt and exit (non-interactive mode)"
    )
    args = parser.parse_args()

    # Setup logging before anything else
    log_file = setup_logging(debug=args.debug)
    console.print(f"  [dim]📝 Log file: {log_file.resolve()}[/]")
    if args.prompt:
        # Non-interactive mode
        config = load_config(args.config)
        issues = validate_config(config)
        if issues:
            for issue in issues:
                print(f"Warning: {issue}")
            if any("API key" in i for i in issues):
                print("Error: Cannot start without an LLM API key.")
                sys.exit(1)

        llm_config = config.get("llm", {})
        ob_config = config.get("openbrush", {})

        llm = _create_llm_client(llm_config)

        ob_client = OpenBrushClient(
            host=ob_config.get("host", "localhost"),
            port=ob_config.get("port", 40074),
            command_delay=ob_config.get("command_delay", 0.05),
        )

        planner = StagedPlanner(llm)
        # Non-interactive mode: run full 4-stage pipeline silently
        try:
            concept, sketch, overall, details = planner.run_pipeline(args.prompt)
        except Exception as e:
            console.print(f"[red]✗ Pipeline Error:[/] {e}")
            sys.exit(1)

        console.print(f"\n🎨 {details.title}: {details.description}")

        def on_step(i, total, desc):
            console.print(f"  [{i+1}/{total}] {desc}")

        for stage_plan, label in [
            (sketch, "Sketch"),
            (overall, "Overall"),
            (details, "Details"),
        ]:
            executor = Executor(ob_client, on_step=on_step)
            results = executor.execute(stage_plan)
            console.print(f"  [{label}] ✓ {results['completed']}/{results['total_steps']} steps, {results['paths_drawn']} paths drawn")
            if results["errors"]:
                for err in results["errors"]:
                    console.print(f"    ⚠ {err}")

        export_config = config.get("export", {})
        if export_config.get("auto_save"):
            try: ob_client.save_overwrite()
            except OpenBrushError: pass
        if export_config.get("auto_export"):
            _handle_export_and_copy(ob_client, wait_time=5)

        if any(results.get("errors") for results in []):
            sys.exit(1)
    else:
        run_cli(args.config)


def _create_llm_client(llm_config: dict) -> LLMClient:
    """Create an LLM client from config with optional throttling settings."""
    return LLMClient(
        api_key=llm_config.get("api_key", ""),
        base_url=llm_config.get("base_url", "https://api.openai.com/v1"),
        model=llm_config.get("model", "gpt-4o"),
        temperature=llm_config.get("temperature", 0.7),
        max_tokens=llm_config.get("max_tokens", 4096),
        call_delay=llm_config.get("call_delay"),
        requests_per_minute=llm_config.get("requests_per_minute"),
    )


if __name__ == "__main__":
    main()
