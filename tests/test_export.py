"""Test script for Open Brush export functionality.

Draws a more substantial shape, saves, then exports with detailed logging.
"""

import os
import time
from pathlib import Path
from sculptor.openbrush_client import OpenBrushClient


EXPORTS_DIR = Path.home() / "Documents" / "Open Brush" / "Exports"


def scan_dir_recursive(path: Path, indent: int = 2):
    """Recursively list contents of a directory."""
    prefix = " " * indent
    try:
        items = sorted(path.iterdir(), key=lambda p: p.name)
    except PermissionError:
        print(f"{prefix}⚠  Permission denied: {path}")
        return
    if not items:
        print(f"{prefix}(empty)")
        return
    for item in items:
        if item.name == ".DS_Store":
            continue
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item.stat().st_mtime))
        if item.is_dir():
            print(f"{prefix}📁 {item.name}/  ({mtime})")
            scan_dir_recursive(item, indent + 4)
        else:
            size = item.stat().st_size
            print(f"{prefix}📄 {item.name}  ({size:,} bytes, {mtime})")


def snapshot_exports():
    """Take a snapshot of the Exports folder contents."""
    files = set()
    if EXPORTS_DIR.exists():
        try:
            for f in EXPORTS_DIR.rglob("*"):
                if f.name != ".DS_Store":
                    files.add(f)
        except PermissionError:
            pass
    return files


def test_export():
    print("=" * 60)
    print("  Open Brush Export Test (v2)")
    print("=" * 60)
    print(f"\n  Exports dir: {EXPORTS_DIR}")
    print(f"  Exists: {EXPORTS_DIR.exists()}")

    # ── Connect ──
    print("\n── Connecting ──")
    client = OpenBrushClient()
    if not client.is_connected():
        print("✗ Cannot connect to Open Brush at localhost:40074.")
        return
    print("✓ Connected.")

    # ── Snapshot before ──
    print("\n── Export folder BEFORE ──")
    before = snapshot_exports()
    if EXPORTS_DIR.exists():
        scan_dir_recursive(EXPORTS_DIR)
    else:
        print("  (does not exist yet)")

    # ── Clear & draw a more substantial shape ──
    print("\n── Drawing a more substantial shape ──")
    client.new_sketch()
    time.sleep(1)

    # Draw a cube-like wireframe (12 edges) so there's real geometry
    client.set_brush("ink", size=0.3, color_html="dodgerblue")
    s = 0.5  # half-size

    # Bottom square
    client.draw_path([(-s, 0, -s), (s, 0, -s), (s, 0, s), (-s, 0, s), (-s, 0, -s)])
    time.sleep(0.3)
    # Top square
    client.draw_path([(-s, 2*s, -s), (s, 2*s, -s), (s, 2*s, s), (-s, 2*s, s), (-s, 2*s, -s)])
    time.sleep(0.3)
    # Vertical pillars
    client.draw_path([(-s, 0, -s), (-s, 2*s, -s)])
    time.sleep(0.3)
    client.draw_path([(s, 0, -s), (s, 2*s, -s)])
    time.sleep(0.3)
    client.draw_path([(s, 0, s), (s, 2*s, s)])
    time.sleep(0.3)
    client.draw_path([(-s, 0, s), (-s, 2*s, s)])
    time.sleep(0.3)

    print("✓ Drew a wireframe cube (6 strokes).")

    # ── Save first (Open Brush may need a saved sketch to export) ──
    print("\n── Saving sketch first ──")
    resp = client.save("export_test")
    print(f"  save response: {resp.status_code}")
    time.sleep(2)

    # ── Export ──
    print("\n── Calling export_current() ──")
    resp = client.export_current()
    print(f"  HTTP status:  {resp.status_code}")
    print(f"  Content-Length: {resp.headers.get('Content-Length', 'N/A')}")
    print(f"  Response body: '{resp.text}'")

    # ── Poll for new files ──
    print("\n── Polling for exported files (up to 15s) ──")
    for i in range(15):
        time.sleep(1)
        after = snapshot_exports()
        new_files = after - before
        # Filter to only actual files (not dirs)
        new_real = [f for f in new_files if f.is_file() and f.stat().st_size > 0]
        print(f"  {i+1}s: {len(new_files)} new items, {len(new_real)} non-empty files", end="")
        if new_real:
            print(" ✓ FOUND!")
            break
        print()
    else:
        print("\n  ⚠ Timed out waiting for exported files.")

    # ── Show what's in the Exports folder now ──
    print("\n── Export folder AFTER ──")
    scan_dir_recursive(EXPORTS_DIR)

    # ── Show diff ──
    after = snapshot_exports()
    new_files = after - before
    if new_files:
        print("\n── NEW items since export ──")
        for f in sorted(new_files):
            kind = "DIR " if f.is_dir() else "FILE"
            size = f"({f.stat().st_size:,} bytes)" if f.is_file() else ""
            print(f"  {kind}  {f.relative_to(EXPORTS_DIR)}  {size}")
    else:
        print("\n  ✗ No new items appeared.")

    # ── Open Finder to exports folder ──
    print("\n── Opening exports folder in Finder ──")
    client.send_raw("showfolder.exports")
    print("  Done. Check Finder for the actual location.")

    print("\n" + "=" * 60)
    print("  Test complete.")
    print("=" * 60)


if __name__ == "__main__":
    test_export()
