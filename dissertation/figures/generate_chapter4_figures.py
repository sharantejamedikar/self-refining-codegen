"""Generate the vector figures used in dissertation Chapter 4."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUTPUT_DIR = Path(__file__).resolve().parent

STANDARD_LABELS = [
    "Qwen\nHumanEval",
    "Qwen\nMBPP",
    "CodeLlama\nHumanEval",
    "CodeLlama\nMBPP",
]
PRO_LABELS = [
    "Qwen\nHumanEval Pro",
    "Qwen\nMBPP Pro",
    "CodeLlama\nHumanEval Pro",
    "CodeLlama\nMBPP Pro",
]
METHODS = ["Single-pass", "Best-of-5", "Adaptive refinement"]
HATCHES = ["", "///", "..."]
GREYS = ["0.72", "0.38", "0.90"]


def _style() -> None:
    """Apply a compact, grayscale-friendly academic plotting style."""

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 10,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
        }
    )


def _grouped_accuracy(filename: str, labels: list[str], values: np.ndarray) -> None:
    """Draw a grouped pass@1 chart for three inference policies."""

    x = np.arange(len(labels))
    width = 0.24
    fig, ax = plt.subplots(figsize=(7.0, 3.7))
    for index, method in enumerate(METHODS):
        bars = ax.bar(
            x + (index - 1) * width,
            values[:, index] * 100,
            width,
            label=method,
            color=GREYS[index],
            edgecolor="black",
            linewidth=0.7,
            hatch=HATCHES[index],
        )
        ax.bar_label(bars, fmt="%.1f", padding=2, fontsize=7)
    ax.set_ylabel("Tasks solved (%)")
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 20))
    ax.grid(axis="y", color="0.88", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(ncol=3, frameon=False, loc="upper center")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, bbox_inches="tight")
    plt.close(fig)


def standard_accuracy() -> None:
    """Generate the standard-benchmark pass@1 figure."""

    values = np.array(
        [
            [142 / 164, 152 / 164, 148 / 164],
            [307 / 427, 337 / 427, 352 / 427],
            [68 / 164, 102 / 164, 87 / 164],
            [192 / 427, 263 / 427, 257 / 427],
        ]
    )
    _grouped_accuracy("figure_4_1_standard_pass_at_1.pdf", STANDARD_LABELS, values)


def accuracy_calls() -> None:
    """Generate the standard-benchmark accuracy/model-call trade-off figure."""

    accuracy = (
        np.array(
            [
                [142 / 164, 152 / 164, 148 / 164],
                [307 / 427, 337 / 427, 352 / 427],
                [68 / 164, 102 / 164, 87 / 164],
                [192 / 427, 263 / 427, 257 / 427],
            ]
        )
        * 100
    )
    calls = np.array(
        [
            [164, 820, 199],
            [427, 2135, 647],
            [164, 820, 311],
            [427, 2135, 821],
        ]
    )
    markers = ["o", "s", "^"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.45), sharey=True)
    for panel, (ax, indices, title) in enumerate(
        [(axes[0], [0, 1], "Qwen"), (axes[1], [2, 3], "CodeLlama")]
    ):
        for method_index, method in enumerate(METHODS):
            for local_index, condition_index in enumerate(indices):
                face = "white" if local_index == 0 else GREYS[method_index]
                ax.scatter(
                    calls[condition_index, method_index],
                    accuracy[condition_index, method_index],
                    marker=markers[method_index],
                    s=52,
                    facecolor=face,
                    edgecolor="black",
                    linewidth=0.8,
                    label=method if local_index == 0 else None,
                    zorder=3,
                )
            ax.plot(
                calls[indices, method_index],
                accuracy[indices, method_index],
                color="0.65",
                linewidth=0.6,
                zorder=1,
            )
        ax.set_title(title)
        ax.set_xlabel("Recorded model calls")
        ax.grid(color="0.90", linewidth=0.6)
        ax.set_axisbelow(True)
        if panel == 0:
            ax.set_ylabel("Tasks solved (%)")
            ax.text(
                0.03,
                0.04,
                "Open: HumanEval\nFilled: MBPP",
                transform=ax.transAxes,
                fontsize=7,
            )
    axes[1].legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_4_2_accuracy_calls.pdf", bbox_inches="tight")
    plt.close(fig)


def pro_accuracy() -> None:
    """Generate the Pro-benchmark pass@1 figure."""

    values = np.array(
        [
            [107 / 164, 129 / 164, 115 / 164],
            [228 / 378, 289 / 378, 257 / 378],
            [47 / 164, 71 / 164, 55 / 164],
            [143 / 378, 206 / 378, 175 / 378],
        ]
    )
    _grouped_accuracy("figure_4_3_pro_pass_at_1.pdf", PRO_LABELS, values)


def convergence() -> None:
    """Generate the adaptive/fixed call and final-regression comparison."""

    labels = [
        "Qwen\nHE",
        "Qwen\nMBPP",
        "CodeLlama\nHE",
        "CodeLlama\nMBPP",
        "Qwen\nHE Pro",
        "Qwen\nMBPP Pro",
        "CodeLlama\nHE Pro",
        "CodeLlama\nMBPP Pro",
    ]
    adaptive_calls = np.array([199, 647, 311, 821, 256, 620, 340, 718])
    fixed_calls = np.array([820, 2135, 820, 2135, 820, 1890, 820, 1890])
    regression_rates = (
        np.array(
            [5 / 148, 18 / 352, 9 / 87, 46 / 257, 1 / 115, 4 / 257, 1 / 55, 11 / 175]
        )
        * 100
    )
    x = np.arange(len(labels))
    width = 0.36
    fig, (ax_calls, ax_reg) = plt.subplots(
        2,
        1,
        figsize=(7.2, 5.1),
        gridspec_kw={"height_ratios": [1.35, 1]},
        constrained_layout=True,
    )
    ax_calls.bar(
        x - width / 2,
        adaptive_calls,
        width,
        label="Adaptive",
        color="0.78",
        edgecolor="black",
    )
    ax_calls.bar(
        x + width / 2,
        fixed_calls,
        width,
        label="Fixed-k=5",
        color="0.38",
        edgecolor="black",
        hatch="///",
    )
    ax_calls.set_ylabel("Recorded model calls")
    ax_calls.set_xticks(x, [])
    ax_calls.grid(axis="y", color="0.88", linewidth=0.6)
    ax_calls.set_axisbelow(True)
    ax_calls.legend(frameon=False, ncol=2)
    reg_bars = ax_reg.bar(
        x, regression_rates, width=0.58, color="0.72", edgecolor="black", hatch="..."
    )
    ax_reg.bar_label(reg_bars, fmt="%.1f%%", padding=2, fontsize=7)
    ax_reg.set_ylabel("Ever-solved tasks\nregressing at iteration 5 (%)")
    ax_reg.set_xticks(x, labels, fontsize=6.5)
    ax_reg.set_ylim(0, 20)
    ax_reg.grid(axis="y", color="0.88", linewidth=0.6)
    ax_reg.set_axisbelow(True)
    fig.savefig(
        OUTPUT_DIR / "figure_4_4_convergence_regressions.pdf", bbox_inches="tight"
    )
    plt.close(fig)


def sensitivity() -> None:
    """Generate feedback-length and temperature sensitivity panels."""

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.35), sharey=True)
    panels = [
        (
            axes[0],
            [100, 200, 300],
            [93, 93, 93],
            [52, 52, 52],
            "Feedback ceiling (words)",
        ),
        (
            axes[1],
            [0.0, 0.4, 0.8],
            [92, 91, 91],
            [50, 52, 50],
            "Refinement temperature",
        ),
    ]
    for ax, x, qwen, codellama, xlabel in panels:
        ax.plot(x, qwen, marker="o", color="black", linewidth=1.2, label="Qwen")
        ax.plot(
            x,
            codellama,
            marker="s",
            color="0.45",
            linestyle="--",
            linewidth=1.2,
            label="CodeLlama",
        )
        for x_value, y_value in zip(x, qwen, strict=False):
            ax.annotate(
                f"{y_value}%",
                (x_value, y_value),
                xytext=(0, 5),
                textcoords="offset points",
                ha="center",
                fontsize=7,
            )
        for x_value, y_value in zip(x, codellama, strict=False):
            ax.annotate(
                f"{y_value}%",
                (x_value, y_value),
                xytext=(0, -11),
                textcoords="offset points",
                ha="center",
                fontsize=7,
            )
        ax.set_xlabel(xlabel)
        ax.set_xticks(x)
        ax.set_ylim(40, 100)
        ax.grid(color="0.90", linewidth=0.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Tasks solved on fixed HumanEval subset (%)")
    axes[1].legend(frameon=False, loc="center right")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_4_5_sensitivity.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """Generate all Chapter 4 figures."""

    _style()
    standard_accuracy()
    accuracy_calls()
    pro_accuracy()
    convergence()
    sensitivity()


if __name__ == "__main__":
    main()
