
import re
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def read_ltspice_steps(filename):

    data = {}
    current_run = None

    number = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

    # Frequency followed by (magnitude, phase)
    pattern = re.compile(
        rf"^\s*({number})\s+"
        rf"\(\s*({number})\s*(?:dB)?\s*,\s*"
        rf"({number})"
    )

    step_pattern = re.compile(r"Run\s*=\s*(\d+)", re.IGNORECASE)

    with open(filename, "r", encoding="utf-8-sig",
              errors="replace") as file:

        for line in file:

            step_match = step_pattern.search(line)

            if step_match:
                current_run = int(step_match.group(1))
                data[current_run] = {
                    "frequency": [],
                    "magnitude": [],
                    "phase": []
                }
                continue

            if current_run is None:
                continue

            match = pattern.match(line)

            if match:
                frequency, magnitude, phase = map(
                    float, match.groups()
                )

                data[current_run]["frequency"].append(frequency)
                data[current_run]["magnitude"].append(magnitude)
                data[current_run]["phase"].append(phase)

    return data


def plot_bode(data, filename):

    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "legend.fontsize": 10,
        "figure.dpi": 120,
        "savefig.dpi": 300,
    })

    fig, (ax_mag, ax_phase) = plt.subplots(
        2, 1,
        figsize=(11, 8),
        sharex=True
    )

    valid_runs = 0

    for run, values in data.items():

        frequency = np.asarray(values["frequency"])
        magnitude = np.asarray(values["magnitude"])
        phase = np.asarray(values["phase"])

        if len(frequency) == 0:
            continue

        # Sort points by frequency
        order = np.argsort(frequency)

        frequency = frequency[order]
        magnitude = magnitude[order]
        phase = phase[order]

        ax_mag.semilogx(
            frequency, magnitude,
            linewidth=0.8, alpha=0.35
        )

        ax_phase.semilogx(
            frequency, phase,
            linewidth=0.8, alpha=0.35
        )

        valid_runs += 1

    if valid_runs == 0:
        print("ERROR: No valid simulation data found.")
        return

    ax_mag.set_title(
        f"Monte Carlo Bode Diagram ({valid_runs} runs)"
    )
    ax_mag.set_ylabel("Magnitude [dB]")
    ax_mag.grid(True, which="both", linestyle="--", alpha=0.5)

    ax_phase.set_xlabel("Frequency [Hz]")
    ax_phase.set_ylabel("Phase [degrees]")
    ax_phase.grid(True, which="both", linestyle="--", alpha=0.5)

    fig.tight_layout()

    output_dir = Path(filename).resolve().parent
    output_name = Path(filename).stem

    fig.savefig(output_dir / f"{output_name}_bode.png", dpi=300)
    fig.savefig(output_dir / f"{output_name}_bode.pdf")

    plt.show()


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python montecarlo_bode.py <input_file.txt>")
        sys.exit(1)

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(f"File not found: {input_file}")
        sys.exit(1)

    results = read_ltspice_steps(input_file)

    print(f"\nSimulation runs found: {len(results)}")

    for run, values in results.items():
        print(
            f"Run {run}: "
            f"{len(values['frequency'])} data points"
        )

    plot_bode(results, input_file)
