"""
InboxPilot AI — Combined smoke test runner

Starts Streamlit on port 8502, runs the Playwright smoke tests,
captures screenshots to docs/screenshots/, then shuts down.

Usage:
    python e2e/run_smoke_test.py

Requirements:
    pip install playwright pytest-playwright
    python -m playwright install chromium
"""
import subprocess
import sys
import os
import time
import socket

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8502


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=1):
            return True
    except OSError:
        return False


def main():
    print("=" * 55)
    print("InboxPilot AI — Playwright Smoke Test Runner")
    print("=" * 55)

    # 1. Start Streamlit
    already_running = port_open(PORT)
    proc = None

    if already_running:
        print(f"\nStreamlit already running on port {PORT} — using it.")
    else:
        print(f"\nStarting Streamlit on port {PORT}...")
        cmd = [
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", str(PORT),
            "--server.headless", "true",
            "--server.runOnSave", "false",
            "--browser.gatherUsageStats", "false",
        ]
        proc = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        deadline = time.time() + 30
        while time.time() < deadline:
            if port_open(PORT):
                time.sleep(1.5)  # let Streamlit finish initialising
                print(f"    Streamlit ready at http://localhost:{PORT}")
                break
            time.sleep(0.5)
        else:
            if proc:
                proc.terminate()
            print("ERROR: Streamlit did not start within 30s")
            sys.exit(1)

    # 2. Run Playwright tests
    print("\nRunning Playwright smoke tests...")
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "e2e/test_app_smoke.py",
            "-v", "--timeout=60",
            "--tb=short",
        ],
        cwd=PROJECT_ROOT,
    )

    # 3. Shut down Streamlit
    if proc:
        print("\nStopping Streamlit...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    # 4. Report screenshot locations
    screenshots_dir = os.path.join(PROJECT_ROOT, "docs", "screenshots")
    pngs = [f for f in os.listdir(screenshots_dir) if f.endswith(".png")]
    if pngs:
        print(f"\nScreenshots saved ({len(pngs)}):")
        for f in sorted(pngs):
            print(f"    docs/screenshots/{f}")
    else:
        print("\nNo screenshots saved — check test output above.")

    print("\n" + "=" * 55)
    if result.returncode == 0:
        print("SMOKE TESTS PASSED")
    else:
        print(f"SMOKE TESTS FAILED (exit code {result.returncode})")
    print("=" * 55)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
