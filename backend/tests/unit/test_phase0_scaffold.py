"""Phase 0 scaffold smoke tests."""

from pathlib import Path

import app


def test_package_version() -> None:
    assert app.__version__ == "0.1.0"


def test_scaffold_boundaries_exist() -> None:
    root = Path(__file__).resolve().parents[3]
    expected = [
        root / "backend" / "app" / "main.py",
        root / "backend" / "app" / "config.py",
        root / "backend" / "app" / "clients" / "grafana.py",
        root / "backend" / "app" / "validators" / "base.py",
        root / "backend" / "app" / "agent" / "orchestrator.py",
        root / ".env.example",
        root / "pyproject.toml",
        root / "docs" / "25_MVP_BOUNDARIES.md",
        root / "docs" / "26_CODING_STANDARDS.md",
        root / "docs" / "27_ENVIRONMENT_CONTRACT.md",
    ]
    missing = [str(path) for path in expected if not path.exists()]
    assert missing == []
