"""Generates .specify/memory/architecture/dependencies.md."""

from __future__ import annotations

from ..models import ArchitectureDiagnostic, FileNode


class DependenciesGenerator:
    """Generates module dependency coupling, hotspots, and blast radius documentation."""

    def generate(
        self,
        files: dict[str, FileNode],
        file_deps: dict[str, list[str]],
        diagnostics: list[ArchitectureDiagnostic] | None = None,
    ) -> str:
        # Compute reverse dependencies (in-degree: who imports this file)
        dependents: dict[str, list[str]] = {}
        for src, dsts in file_deps.items():
            for dst in dsts:
                dependents.setdefault(dst, []).append(src)

        # Sort files by in-degree (most depended-on files = highest blast radius)
        coupling_table: list[dict[str, object]] = []
        for fpath in files.keys():
            in_deg = len(dependents.get(fpath, []))
            out_deg = len(file_deps.get(fpath, []))
            if in_deg >= 5:
                risk = "🔴 HIGH"
            elif in_deg >= 2:
                risk = "🟡 MEDIUM"
            else:
                risk = "🟢 LOW"

            coupling_table.append({
                "file": fpath,
                "in_deg": in_deg,
                "out_deg": out_deg,
                "risk": risk,
                "callers": dependents.get(fpath, []),
            })

        coupling_table.sort(key=lambda x: (int(x["in_deg"]), int(x["out_deg"])), reverse=True)

        lines = [
            "# Dependencies, Coupling & Blast Radius Guide",
            "",
            "> [!NOTE]",
            "> Documents inter-module dependencies and assesses blast radius for safe refactoring and changes.",
            "",
            "## 1. Coupling Hotspots & Blast Radius Risk",
            "Files with high inbound dependencies carry high blast radius: modifications may impact many callers across the codebase.",
            "",
            "| Module / File Path | Inbound Callers (Blast Radius) | Outbound Dependencies | Risk Rating |",
            "| :--- | :--- | :--- | :--- |",
        ]

        if not coupling_table:
            lines.append("| *None* | 0 | 0 | 🟢 LOW |")
        else:
            for row in coupling_table[:40]:
                lines.append(
                    f"| `{row['file']}` | **{row['in_deg']} callers** | {row['out_deg']} | {row['risk']} |"
                )

        lines.extend([
            "",
            "## 2. High-Impact Refactoring Targets",
            "",
        ])

        high_impact = [r for r in coupling_table if int(r["in_deg"]) >= 3]
        if not high_impact:
            lines.append("*No severe coupling hotspots detected.*")
        else:
            for r in high_impact[:10]:
                lines.append(f"### `{r['file']}` ({r['risk']})")
                lines.append(f"- **Directly Depended on By ({r['in_deg']} files):**")
                for c in sorted(r["callers"])[:10]:
                    lines.append(f"  - `{c}`")
                if len(r["callers"]) > 10:
                    lines.append(f"  - *(+{len(r['callers']) - 10} more callers)*")
                lines.append("")

        active_diags = [d for d in (diagnostics or []) if not d.suppressed]
        lines.extend([
            "",
            "## 3. Depth & Abstraction Diagnostics (Deletion Test & Two-Adapter Rule)",
            "",
        ])
        if not active_diags:
            lines.append("*No active shallow pass-through or premature abstraction warnings detected.*")
        else:
            for d in active_diags[:40]:
                lines.append(f"- **[{d.code}]** `{d.file_path}:{d.line}` (`{d.symbol_name}`): {d.message}")

        return "\n".join(lines)
