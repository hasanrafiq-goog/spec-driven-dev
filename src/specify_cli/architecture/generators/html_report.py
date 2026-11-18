"""Self-contained, 100% offline HTML dashboard generator for ArchitectureEngine."""

from __future__ import annotations

import html
from datetime import datetime, timezone

from ..models import ArchitectureDiagnostic, FileNode


class HtmlReportGenerator:
    """Generates a zero-dependency, air-gap resilient HTML architecture dashboard."""

    def generate(
        self,
        files: dict[str, FileNode],
        file_deps: dict[str, list[str]],
        diagnostics: list[ArchitectureDiagnostic],
    ) -> str:
        dependents: dict[str, list[str]] = {}
        for src, dsts in file_deps.items():
            for dst in dsts:
                dependents.setdefault(dst, []).append(src)

        total_files = len(files)
        total_symbols = sum(len(f.symbols) for f in files.values())
        active_diags = [d for d in diagnostics if not d.suppressed]

        top_modules = sorted(
            files.keys(),
            key=lambda p: (len(dependents.get(p, [])), len(file_deps.get(p, []))),
            reverse=True,
        )[:12]

        svg_nodes = []
        svg_edges = []
        node_coords: dict[str, tuple[int, int]] = {}
        cols = 3
        for idx, mod in enumerate(top_modules):
            col = idx % cols
            row = idx // cols
            x = 40 + col * 270
            y = 30 + row * 85
            node_coords[mod] = (x, y)
            label = html.escape(mod.split("/")[-1])
            in_deg = len(dependents.get(mod, []))
            fill = "#fee2e2" if in_deg >= 5 else ("#fef3c7" if in_deg >= 2 else "#dcfce7")
            stroke = "#dc2626" if in_deg >= 5 else ("#d97706" if in_deg >= 2 else "#16a34a")
            svg_nodes.append(
                f'<g><rect x="{x}" y="{y}" width="220" height="46" rx="8" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
                f'<text x="{x + 110}" y="{y + 21}" text-anchor="middle" '
                f'font-family="monospace" font-size="12" fill="#0f172a">{label}</text>'
                f'<text x="{x + 110}" y="{y + 37}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="10" fill="#475569">{in_deg} callers</text></g>'
            )

        for src in top_modules:
            if src not in node_coords:
                continue
            sx, sy = node_coords[src]
            for dst in file_deps.get(src, []):
                if dst in node_coords and src != dst:
                    dx, dy = node_coords[dst]
                    svg_edges.append(
                        f'<line x1="{sx + 110}" y1="{sy + 46}" x2="{dx + 110}" y2="{dy}" '
                        f'stroke="#94a3b8" stroke-width="1.2" marker-end="url(#arrow)"/>'
                    )

        svg_height = max(140, ((len(top_modules) + cols - 1) // cols) * 85 + 40)

        diag_rows = []
        for d in active_diags:
            badge_bg = "#fef2f2" if d.code == "SHALLOW_PASS_THROUGH" else "#fffbeb"
            badge_fg = "#b91c1c" if d.code == "SHALLOW_PASS_THROUGH" else "#b45309"
            diag_rows.append(
                f"<tr>"
                f'<td><span class="badge" style="background:{badge_bg};color:{badge_fg}">{html.escape(d.code)}</span></td>'
                f"<td><code>{html.escape(d.file_path)}:{d.line}</code></td>"
                f"<td><code>{html.escape(d.symbol_name)}</code></td>"
                f"<td>{html.escape(d.message)}</td>"
                f"</tr>"
            )
        if not diag_rows:
            diag_rows.append(
                '<tr><td colspan="4" style="text-align:center;color:#15803d;">No active Deletion Test or Two-Adapter warnings detected.</td></tr>'
            )

        coupling_rows = []
        for mod in top_modules:
            in_deg = len(dependents.get(mod, []))
            out_deg = len(file_deps.get(mod, []))
            coupling_rows.append(
                f"<tr><td><code>{html.escape(mod)}</code></td><td>{in_deg}</td><td>{out_deg}</td></tr>"
            )

        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Spec Kit Offline Architecture Dashboard</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; background: #f8fafc; color: #0f172a; }}
    .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px; margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px; }}
    .stat {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; }}
    .stat-num {{ font-size: 24px; font-weight: 700; color: #0f172a; }}
    .stat-label {{ font-size: 12px; color: #64748b; text-transform: uppercase; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }}
    th {{ background: #f1f5f9; font-weight: 600; }}
    .badge {{ padding: 3px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }}
    code {{ background: #f1f5f9; padding: 2px 5px; border-radius: 4px; font-size: 12px; }}
  </style>
</head>
<body>
  <h1>Spec Kit Architecture Dashboard (Offline)</h1>
  <p style="color:#475569;">Generated {html.escape(generated_at)} &bull; Zero external dependencies &bull; Air-gap resilient</p>
  <div class="grid">
    <div class="stat"><div class="stat-num">{total_files}</div><div class="stat-label">Source Files</div></div>
    <div class="stat"><div class="stat-num">{total_symbols}</div><div class="stat-label">Indexed Symbols</div></div>
    <div class="stat"><div class="stat-num">{len(active_diags)}</div><div class="stat-label">Depth Warnings</div></div>
  </div>
  <div class="card">
    <h2>Component Coupling Graph (Top Modules)</h2>
    <svg width="100%" viewBox="0 0 860 {svg_height}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill="#94a3b8" />
        </marker>
      </defs>
      {"".join(svg_edges)}
      {"".join(svg_nodes)}
    </svg>
  </div>
  <div class="card">
    <h2>Deletion Test &amp; Two-Adapter Diagnostics</h2>
    <table>
      <thead><tr><th>Rule</th><th>Location</th><th>Symbol</th><th>Guidance</th></tr></thead>
      <tbody>{"".join(diag_rows)}</tbody>
    </table>
  </div>
  <div class="card">
    <h2>Coupling Hotspots</h2>
    <table>
      <thead><tr><th>Module</th><th>Inbound Callers</th><th>Outbound Deps</th></tr></thead>
      <tbody>{"".join(coupling_rows)}</tbody>
    </table>
  </div>
</body>
</html>
"""
