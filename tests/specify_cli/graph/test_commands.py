"""Tests for specify graph CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typer.testing import CliRunner
from specify_cli import app

runner = CliRunner()


def test_cli_graph_help():
    result = runner.invoke(app, ["graph", "--help"])
    assert result.exit_code == 0
    assert "Universal Codebase Knowledge Graph" in result.output
    assert "build" in result.output
    assert "summary" in result.output
    assert "blast-radius" in result.output
    assert "routes" in result.output
    assert "models" in result.output
    assert "query" in result.output


def test_cli_graph_lifecycle(tmp_path: Path):
    # Setup a sample repository
    (tmp_path / "models.py").write_text(
        "from pydantic import BaseModel\nclass Customer(BaseModel):\n    name: str\n",
        encoding="utf-8",
    )
    (tmp_path / "server.py").write_text(
        "from fastapi import FastAPI\nimport models\napp = FastAPI()\n@app.get('/api/customers')\ndef list_customers(): pass\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_server.py").write_text(
        "import server\ndef test_customers(): pass\n",
        encoding="utf-8",
    )

    # 1. specify graph build --path <tmp_path>
    res_build = runner.invoke(app, ["graph", "build", "-p", str(tmp_path)])
    assert res_build.exit_code == 0
    assert "Code graph updated successfully" in res_build.output

    # 2. specify graph summary --path <tmp_path>
    res_summary = runner.invoke(app, ["graph", "summary", "-p", str(tmp_path)])
    assert res_summary.exit_code == 0
    assert "Summary" in res_summary.output

    # 2b. specify graph summary --json
    res_sum_json = runner.invoke(app, ["graph", "summary", "-p", str(tmp_path), "--json"])
    assert res_sum_json.exit_code == 0
    data = json.loads(res_sum_json.output)
    assert data["total_files"] == 3
    assert data["total_routes"] == 1
    assert data["total_models"] == 1

    # 3. specify graph routes -p <tmp_path>
    res_routes = runner.invoke(app, ["graph", "routes", "-p", str(tmp_path)])
    assert res_routes.exit_code == 0
    assert "/api/customers" in res_routes.output

    # 4. specify graph models -p <tmp_path>
    res_models = runner.invoke(app, ["graph", "models", "-p", str(tmp_path)])
    assert res_models.exit_code == 0
    assert "Customer" in res_models.output

    # 5. specify graph blast-radius models.py -p <tmp_path>
    res_br = runner.invoke(app, ["graph", "blast-radius", "models.py", "-p", str(tmp_path)])
    assert res_br.exit_code == 0
    assert "server.py" in res_br.output

    # 5b. specify graph blast-radius --json
    res_br_json = runner.invoke(app, ["graph", "blast-radius", "models.py", "-p", str(tmp_path), "--json"])
    assert res_br_json.exit_code == 0
    br_data = json.loads(res_br_json.output)
    assert br_data["target"] == "models.py"
    assert "server.py" in br_data["directly_impacted_files"]

    # 6. specify graph query Customer -p <tmp_path>
    res_query = runner.invoke(app, ["graph", "query", "Customer", "-p", str(tmp_path)])
    assert res_query.exit_code == 0
    assert "Customer" in res_query.output

    # 7. specify graph export --format mermaid -p <tmp_path>
    res_export = runner.invoke(app, ["graph", "export", "-p", str(tmp_path)])
    assert res_export.exit_code == 0
    assert "flowchart TD" in res_export.output
    assert "models.py" in res_export.output

