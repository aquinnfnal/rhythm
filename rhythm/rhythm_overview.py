import os
import re
from datetime import datetime
import matplotlib.pyplot as plt


def generate_results_overview(label_to_file, title=None):


    if title == None:
        title = "Specification Summary Dashboard"
    
    # --------------------------------------------------
    # Create safe folder name
    # --------------------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r"[^\w\-]+", "_", title).strip("_")
    outdir = f"overviews/{safe_title}"
    os.makedirs(outdir, exist_ok=True)

    merged_txt_path = os.path.join(outdir, "merged_results.txt")
    dashboard_png_path = os.path.join(outdir, "dashboard.png")

    # --------------------------------------------------
    # Regex patterns
    # --------------------------------------------------
    overall_pattern = re.compile(r"Overall Result:\s*(PASS|FAIL|N/A)")
    worst_pattern = re.compile(
        r"\(Worst Corner was (.*?) with ([A-Za-z0-9_]+)=([^\)]+)\)"
    )
    timestamp_pattern = re.compile(
        r"Record generated at ([0-9\-:\s]+)"
    )
    corners_pattern = re.compile(
        r"for corners matching (.*)", re.IGNORECASE
    )

    dashboard_rows = []

    # --------------------------------------------------
    # Merge + parse
    # --------------------------------------------------
    with open(merged_txt_path, "w") as merged_file:

        for label, filepath in label_to_file.items():

            if not os.path.exists(filepath):
                print(f"Warning: {filepath} not found")
                continue

            with open(filepath, "r") as f:
                content = f.read()

            # Header
            merged_file.write(
                "\n" + "=" * 80 + "\n"
                + f"FILE: {label} ({filepath})\n"
                + "=" * 80 + "\n\n"
            )
            merged_file.write(content + "\n\n")

            # Timestamp
            ts_match = timestamp_pattern.search(content)
            file_timestamp = ts_match.group(1) if ts_match else "Unknown"
            file_timestamp = file_timestamp[:-1] # Strip out the newline.
            
            # Split specs
            blocks = re.split(r"Specification:", content)[1:]

            for block in blocks:
                lines = block.strip().split("\n")
                spec_line = lines[0].strip()

                # Corners
                corners_match = corners_pattern.search(spec_line)
                corners = corners_match.group(1).strip() if corners_match else "All Corners"

                # Clean spec text
                spec_clean = re.sub(
                    r"\s*for corners matching .*", "", spec_line, flags=re.IGNORECASE
                ).strip()

                # Result
                overall_match = overall_pattern.search(block)
                overall = overall_match.group(1) if overall_match else "UNKNOWN"

                # Worst case
                worst_match = worst_pattern.search(block)
                if worst_match:
                    corner = worst_match.group(1)
                    metric = worst_match.group(2)
                    value = worst_match.group(3)
                    worst_value = f"{metric}={value}"
                else:
                    corner = "-"
                    worst_value = "-"

                dashboard_rows.append([
                    label,
                    spec_clean,
                    corners,
                    overall,
                    worst_value,
                    corner,
                    file_timestamp
                ])

    # --------------------------------------------------
    # Generate dashboard
    # --------------------------------------------------
    if not dashboard_rows:
        print("No data found for dashboard.")
        return

    n_rows = len(dashboard_rows)

    # Better height heuristic (less bloated than before)
    fig_height = 0.35 * n_rows + 1.5
    fig, ax = plt.subplots(figsize=(1,1))
    ax.axis("off")

    columns = [
        "Simulation",
        "Spec",
        "Corners",
        "Result",
        "Worst Value",
        "Worst Corner",
        "Sim Timestamp"
    ]

    table = ax.table(
        cellText=dashboard_rows,
        colLabels=columns,
        loc="upper center",
        cellLoc="left"
    )

    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.auto_set_column_width(col=list(range(len(columns))))

    # Color coding
    for i, row in enumerate(dashboard_rows, start=1):
        result = row[3]

        if result == "PASS":
            color = "#c8e6c9"
        elif result == "FAIL":
            color = "#ffcdd2"
        else:
            color = "#eeeeee"

        for j in range(len(columns)):
            table[(i, j)].set_facecolor(color)

    # Header styling
    for j in range(len(columns)):
        table[(0, j)].set_facecolor("#90caf9")
        table[(0, j)].set_text_props(weight='bold')

    ax.set_title(title, pad=6)

    plt.savefig(dashboard_png_path, bbox_inches="tight", pad_inches=0.05)
    plt.close()

    print(f"\nOutputs written to: {outdir}")
    print(f"- Merged text: {merged_txt_path}")
    print(f"- Dashboard:   {dashboard_png_path}")
