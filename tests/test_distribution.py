import json
from pathlib import Path
import subprocess
import tomllib


ROOT = Path(__file__).parents[1]


def test_setup_dry_run_reports_only_d_drive_runtime_paths():
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "setup-demo.ps1"),
            "-DryRun",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    paths = json.loads(result.stdout)
    assert paths == {
        "venv": r"D:\codex\venvs\quiz-assistant-demo",
        "pipCache": r"D:\codex\cache\pip",
        "temp": r"D:\codex\tmp\quiz-window-assistant-demo",
    }


def test_launcher_check_confirms_installed_gui_entry():
    result = subprocess.run(
        ["cmd", "/d", "/c", str(ROOT / "run-demo.cmd"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "READY"


def test_package_declares_a_windows_gui_script_not_a_console_script():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["gui-scripts"] == {
        "quiz-window-assistant": "quiz_assistant.app:main"
    }
    assert "scripts" not in metadata["project"]
