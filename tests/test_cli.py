import subprocess
import sys


def test_cli_unknown_app_exits_cleanly(tmp_path):
    (tmp_path / "apps").mkdir()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "flatpak_packages",
            "--root",
            str(tmp_path),
            "prepare",
            "org.example.Missing",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "found 0" in result.stderr
    assert "Traceback" not in result.stderr
