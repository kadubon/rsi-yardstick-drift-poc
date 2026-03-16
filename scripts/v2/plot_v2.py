from __future__ import annotations

import argparse
import csv
import pathlib


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a simple SVG plot for PoC v2 held-out results.")
    parser.add_argument("--summary-csv", required=True, type=pathlib.Path)
    parser.add_argument("--flip-analysis", required=True, type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    return parser.parse_args()


def scale_bar(value: float, maximum: float, width: float) -> float:
    if maximum <= 0:
        return 0.0
    return round((value / maximum) * width, 2)


def main() -> None:
    args = parse_args()
    with args.summary_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["split"] == "evaluation"]
    if not rows:
        raise SystemExit("No evaluation rows found in summary CSV.")
    output_path = args.output or args.summary_csv.with_suffix(".svg")

    max_challenge = max(float(row["challenge_failure_count"]) for row in rows) or 1.0
    left = 230
    bar_width = 150
    row_height = 72
    width = 980
    height = 120 + len(rows) * row_height + 100
    panel_x = [left, left + 200, left + 400]
    colors = ["#2b6cb0", "#c05621", "#2f855a"]
    titles = ["Strict score", "Proxy score", "Challenge failures"]

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fffaf0" />',
        '<text x="24" y="34" font-size="22" font-family="Georgia, serif" fill="#1a202c">RSI yardstick drift PoC v2</text>',
    ]
    for index, title in enumerate(titles):
        svg_lines.append(
            f'<text x="{panel_x[index]}" y="68" font-size="14" font-family="Verdana, sans-serif" fill="#2d3748">{title}</text>'
        )

    for row_index, row in enumerate(rows):
        y = 96 + row_index * row_height
        label = f"{row['condition']} / {row['proxy_profile']}"
        strict_score = float(row["strict_score"])
        proxy_score = float(row["proxy_score"])
        challenge = float(row["challenge_failure_count"])
        svg_lines.append(
            f'<text x="24" y="{y + 16}" font-size="12" font-family="Verdana, sans-serif" fill="#1a202c">{label}</text>'
        )
        for index, (value, maximum) in enumerate([(strict_score, 1.0), (proxy_score, 1.0), (challenge, max_challenge)]):
            width_scaled = scale_bar(value, maximum, bar_width)
            svg_lines.append(f'<rect x="{panel_x[index]}" y="{y}" width="{bar_width}" height="22" fill="#e2e8f0" rx="4" />')
            svg_lines.append(f'<rect x="{panel_x[index]}" y="{y}" width="{width_scaled}" height="22" fill="{colors[index]}" rx="4" />')
            svg_lines.append(
                f'<text x="{panel_x[index] + bar_width + 10}" y="{y + 16}" font-size="12" font-family="Verdana, sans-serif" fill="#2d3748">{value}</text>'
            )

    flip_lines = args.flip_analysis.read_text(encoding="utf-8").splitlines()
    eval_flip_line = next(line for line in flip_lines if '"record_type": "flip_split_summary"' in line and '"split": "evaluation"' in line)
    svg_lines.append(
        f'<text x="24" y="{height - 36}" font-size="13" font-family="Verdana, sans-serif" fill="#2d3748">Held-out ruler-drift flip summary: {eval_flip_line}</text>'
    )
    svg_lines.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(svg_lines) + "\n", encoding="utf-8", newline="\n")
    print(output_path)


if __name__ == "__main__":
    main()
