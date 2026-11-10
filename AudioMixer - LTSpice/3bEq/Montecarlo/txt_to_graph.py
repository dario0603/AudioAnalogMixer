
import re
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


# ---------------------------------------------------------
# REGULAR EXPRESSIONS
# ---------------------------------------------------------

NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

# AC data: frequency (magnitude, phase)
AC_PATTERN = re.compile(
    rf"^\s*({NUMBER})\s+"
    rf"\(\s*({NUMBER})\s*(?:dB)?\s*,\s*"
    rf"({NUMBER})\s*(?:°|deg)?\s*\)",
    re.IGNORECASE
)

STEP_PATTERN = re.compile(
    r"Run\s*=\s*(\d+)",
    re.IGNORECASE
)


# ---------------------------------------------------------
# UNITS
# ---------------------------------------------------------

def get_axis_unit(label):

    label = label.lower().strip()

    if "freq" in label:
        return "Frequency [Hz]"

    if "time" in label:
        return "Time [s]"

    if label.startswith("v(") or label == "voltage":
        return "Voltage [V]"

    if label.startswith("i(") or label == "current":
        return "Current [A]"

    if "temp" in label:
        return "Temperature [°C]"

    return label


def get_signal_unit(label):

    label = label.lower().strip()

    if label.startswith("v("):
        return "Voltage [V]"

    if label.startswith("i("):
        return "Current [A]"

    return label


# ---------------------------------------------------------
# READ LTSPICE FILE
# ---------------------------------------------------------

def read_ltspice_file(filename):

    with open(filename, "r", encoding="utf-8-sig",
              errors="replace") as file:
        lines = file.readlines()

    # Find header
    header_index = None

    for i, line in enumerate(lines):
        if re.search(r"Freq\.?|Time", line, re.IGNORECASE):
            header_index = i
            break

    if header_index is None:
        raise ValueError("Could not identify the file header.")

    header = lines[header_index].strip()

    # LTspice headers are generally tab-separated
    columns = re.split(r"\t+|\s{2,}", header)

    if len(columns) < 2:
        columns = header.split()

    x_label = columns[0]
    y_labels = columns[1:]

    data = {}
    current_run = 1
    data[current_run] = []

    ac_mode = None

    for line in lines[header_index + 1:]:

        # Detect Monte Carlo iteration
        step_match = STEP_PATTERN.search(line)

        if step_match:
            current_run = int(step_match.group(1))
            data[current_run] = []
            continue

        line = line.strip()

        if not line:
            continue

        # Detect AC format
        ac_match = AC_PATTERN.match(line)

        if ac_match:

            if ac_mode is False:
                raise ValueError(
                    "Mixed AC and normal data formats detected."
                )

            ac_mode = True

            frequency, magnitude, phase = map(
                float, ac_match.groups()
            )

            data[current_run].append(
                (frequency, magnitude, phase)
            )

            continue

        # Detect normal numerical format
        if "(" in line:
            continue

        values = re.findall(NUMBER, line)

        if len(values) >= 2:

            if ac_mode is True:
                continue

            ac_mode = False

            values = [float(v) for v in values]

            data[current_run].append(values)

    if ac_mode is None:
        raise ValueError("No valid numerical data found.")

    return x_label, y_labels, data, ac_mode


# ---------------------------------------------------------
# PLOT AC / BODE DATA
# ---------------------------------------------------------

def plot_bode(data, title, filename):

    fig, (ax_mag, ax_phase) = plt.subplots(
        2, 1,
        figsize=(11, 8),
        sharex=True
    )

    for run, rows in data.items():

        if not rows:
            continue

        values = np.array(rows)

        frequency = values[:, 0]
        magnitude = values[:, 1]
        phase = values[:, 2]

        order = np.argsort(frequency)

        frequency = frequency[order]
        magnitude = magnitude[order]
        phase = phase[order]

        label = f"Run {run}" if len(data) <= 15 else None

        ax_mag.semilogx(
            frequency, magnitude,
            linewidth=0.9,
            alpha=0.55,
            label=label
        )

        ax_phase.semilogx(
            frequency, phase,
            linewidth=0.9,
            alpha=0.55,
            label=label
        )

    ax_mag.set_title(title)
    ax_mag.set_ylabel("Magnitude [dB]")
    ax_mag.grid(True, which="both", linestyle="--", alpha=0.5)

    ax_phase.set_xlabel("Frequency [Hz]")
    ax_phase.set_ylabel("Phase [degrees]")
    ax_phase.grid(True, which="both", linestyle="--", alpha=0.5)

    if len(data) <= 15:
        ax_mag.legend(fontsize=8)

    fig.tight_layout()

    save_plot(fig, filename)


# ---------------------------------------------------------
# PLOT NORMAL DATA
# ---------------------------------------------------------

def plot_normal(data, title, x_label, y_labels, filename):

    fig, ax = plt.subplots(figsize=(11, 6))

    for run, rows in data.items():

        if not rows:
            continue

        values = np.array(rows)

        if values.ndim != 2 or values.shape[1] < 2:
            continue

        x = values[:, 0]

        for column in range(1, values.shape[1]):

            y = values[:, column]

            order = np.argsort(x)

            label = (
                f"{y_labels[column - 1]} - Run {run}"
                if len(data) <= 10
                else f"{y_labels[column - 1]}"
            )

            ax.plot(
                x[order],
                y[order],
                linewidth=0.9,
                alpha=0.6,
                label=label
            )

    ax.set_title(title)
    ax.set_xlabel(get_axis_unit(x_label))
    ax.set_ylabel(
        ", ".join(get_signal_unit(y) for y in y_labels)
    )

    ax.grid(True, linestyle="--", alpha=0.5)

    if len(data) <= 10:
        ax.legend(fontsize=8)

    fig.tight_layout()

    save_plot(fig, filename)


# ---------------------------------------------------------
# SAVE PLOTS
# ---------------------------------------------------------

def save_plot(fig, filename):

    output_dir = filename.parent
    output_name = filename.stem

    png_path = output_dir / f"{output_name}.png"
    pdf_path = output_dir / f"{output_name}.pdf"

    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")

    print("\nPlots saved:")
    print(png_path)
    print(pdf_path)

    plt.show()


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 50)
    print("          LTspice Universal Plotter")
    print("=" * 50)

    file_path = Path(
        input("\nEnter LTspice TXT file path: ").strip().strip('"')
    )

    if not file_path.exists():
        print("ERROR: File not found.")
        return

    try:
        x_label, y_labels, data, ac_mode = read_ltspice_file(
            file_path
        )

        # Count valid runs
        valid_runs = {
            run: rows for run, rows in data.items() if rows
        }

        print("\nFile successfully analyzed.")
        print(f"Detected runs: {len(valid_runs)}")
        print(f"X-axis: {x_label}")
        print(f"Y-axis: {', '.join(y_labels)}")

        for run, rows in valid_runs.items():
            print(f"Run {run}: {len(rows)} points")

        # Ask for graph title
        title = input("\nEnter graph title: ").strip()

        if not title:
            title = file_path.stem

        # Generate plot
        if ac_mode:

            print("\nDetected format: AC / Bode analysis")

            plot_bode(
                valid_runs,
                title,
                file_path
            )

        else:

            print("\nDetected format: Normal numerical data")

            plot_normal(
                valid_runs,
                title,
                x_label,
                y_labels,
                file_path
            )

    except Exception as error:
        print(f"\nERROR: {error}")


if __name__ == "__main__":
    main()
