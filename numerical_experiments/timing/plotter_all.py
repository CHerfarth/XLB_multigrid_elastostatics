import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import argparse


def draw_loglog_slope(
    fig,
    ax,
    origin,
    width_inches,
    slope,
    color,
    inverted=False,
    polygon_kwargs=None,
    label=True,
    labelcolor=None,
    label_kwargs=None,
    zorder=None,
):
    """
    This function draws slopes or "convergence triangles" into loglog plots.

    @param fig: The figure
    @param ax: The axes object to draw to
    @param origin: The 2D origin (usually lower-left corner) coordinate of the triangle
    @param width_inches: The width in inches of the triangle
    @param slope: The slope of the triangle, i.e. order of convergence
    @param inverted: Whether to mirror the triangle around the origin, i.e. whether
        it indicates the slope towards the lower left instead of upper right (defaults to false)
    @param color: The color of the of the triangle edges (defaults to default color)
    @param polygon_kwargs: Additional kwargs to the Polygon draw call that creates the slope
    @param label: Whether to enable labeling the slope (defaults to true)
    @param labelcolor: The color of the slope labels (defaults to the edge color)
    @param label_kwargs: Additional kwargs to the Annotation draw call that creates the labels
    @param zorder: The z-order value of the triangle and labels, defaults to a high value
    """

    if polygon_kwargs is None:
        polygon_kwargs = {}
    if label_kwargs is None:
        label_kwargs = {}

    if color is not None:
        polygon_kwargs["color"] = color
    if "linewidth" not in polygon_kwargs:
        polygon_kwargs["linewidth"] = 0.75 * matplotlib.rcParams["lines.linewidth"]
    if labelcolor is not None:
        label_kwargs["color"] = labelcolor
    if "color" not in label_kwargs:
        label_kwargs["color"] = polygon_kwargs["color"]
    if "fontsize" not in label_kwargs:
        label_kwargs["fontsize"] = 0.75 * matplotlib.rcParams["font.size"]

    if inverted:
        width_inches = -width_inches
    if zorder is None:
        zorder = 10

    # For more information on coordinate transformations in Matplotlib see
    # https://matplotlib.org/3.1.1/tutorials/advanced/transforms_tutorial.html

    # Convert the origin into figure coordinates in inches
    origin_disp = ax.transData.transform(origin)
    origin_dpi = fig.dpi_scale_trans.inverted().transform(origin_disp)

    # Obtain the bottom-right corner in data coordinates
    corner_dpi = origin_dpi + width_inches * np.array([1.0, 0.0])
    corner_disp = fig.dpi_scale_trans.transform(corner_dpi)
    corner = ax.transData.inverted().transform(corner_disp)

    (x1, y1) = (origin[0], origin[1])
    x2 = corner[0]

    # The width of the triangle in data coordinates
    width = x2 - x1
    # Compute offset of the slope
    log_offset = y1 / (x1**slope)

    y2 = log_offset * ((x1 + width) ** slope)
    height = y2 - y1

    # The vertices of the slope
    a = origin
    b = corner
    c = [x2, y2]

    # Draw the slope triangle
    X = np.array([a, b, c])
    triangle = plt.Polygon(X[:3, :], fill=False, zorder=zorder, **polygon_kwargs)
    ax.add_patch(triangle)

    # Convert vertices into display space
    a_disp = ax.transData.transform(a)
    b_disp = ax.transData.transform(b)
    c_disp = ax.transData.transform(c)

    # Figure out the center of the triangle sides in display space
    bottom_center_disp = a_disp + 0.5 * (b_disp - a_disp)
    bottom_center = ax.transData.inverted().transform(bottom_center_disp)

    right_center_disp = b_disp + 0.5 * (c_disp - b_disp)
    right_center = ax.transData.inverted().transform(right_center_disp)

    # Label alignment depending on inversion parameter
    va_xlabel = "top" if not inverted else "bottom"
    ha_ylabel = "left" if not inverted else "right"

    # Label offset depending on inversion parameter
    offset_xlabel = (
        [0.0, -0.33 * label_kwargs["fontsize"]]
        if not inverted
        else [0.0, 0.33 * label_kwargs["fontsize"]]
    )
    offset_ylabel = (
        [0.33 * label_kwargs["fontsize"], 0.0]
        if not inverted
        else [-0.33 * label_kwargs["fontsize"], 0.0]
    )

    # Draw the slope labels
    ax.annotate(
        "$1$",
        bottom_center,
        xytext=offset_xlabel,
        textcoords="offset points",
        ha="center",
        va=va_xlabel,
        zorder=zorder,
        **label_kwargs,
    )
    ax.annotate(
        f"${slope}$",
        right_center,
        xytext=offset_ylabel,
        textcoords="offset points",
        ha=ha_ylabel,
        va="center",
        zorder=zorder,
        **label_kwargs,
    )


plt.rcParams.update({
    "xtick.labelsize": 18,
    "ytick.labelsize": 18,
    "axes.titlesize": 20,
    "legend.fontsize": 15,
})


# Load CSV data
data_1 = pd.read_csv("data/results_E_.2_nu_.3.csv")
data_2 = pd.read_csv("data/results_E_.2_nu_.6.csv")
data_3 = pd.read_csv("data/results_E_.5_nu_.3.csv")
data_4 = pd.read_csv("data/results_E_.5_nu_.6.csv")

# Filter only converged entries
data_1 = data_1[data_1["standard_converged_no_allocation"] == 1]
data_2 = data_2[data_2["standard_converged_no_allocation"] == 1]
data_3 = data_3[data_3["standard_converged_no_allocation"] == 1]
data_4 = data_4[data_4["standard_converged_no_allocation"] == 1]


runtimes_1 = data_1.groupby("dim")["standard_time_no_allocation"].agg(["mean", "std"]).reset_index()
runtimes_2 = data_2.groupby("dim")["standard_time_no_allocation"].agg(["mean", "std"]).reset_index()
runtimes_3 = data_3.groupby("dim")["standard_time_no_allocation"].agg(["mean", "std"]).reset_index()
runtimes_4 = data_4.groupby("dim")["standard_time_no_allocation"].agg(["mean", "std"]).reset_index()


# only plot standard runtimes
fig, ax = plt.subplots(figsize=(8, 6))

colors = plt.get_cmap("tab10").colors

ax.errorbar(
    runtimes_1["dim"],
    runtimes_1["mean"],
    yerr=runtimes_1["std"],
    fmt="s-",
    capsize=5,
    label=r"$\tilde{E} = 0.2, \nu = 0.3$",
    color=colors[0],
)
ax.errorbar(
    runtimes_2["dim"],
    runtimes_2["mean"],
    yerr=runtimes_2["std"],
    fmt="s-",
    capsize=5,
    label=r"$\tilde{E} = 0.2, \nu = 0.6$",
    color=colors[1],
)
ax.errorbar(
    runtimes_3["dim"],
    runtimes_3["mean"],
    yerr=runtimes_3["std"],
    fmt="s-",
    capsize=5,
    label=r"$\tilde{E} = 0.5, \nu = 0.3$",
    color=colors[2],
)
ax.errorbar(
    runtimes_4["dim"],
    runtimes_4["mean"],
    yerr=runtimes_4["std"],
    fmt="s-",
    capsize=5,
    label=r"$\tilde{E} = 0.5, \nu = 0.6$",
    color=colors[3],
)
# Add labels and legend
plt.xlabel("n", fontsize=19)
plt.ylabel("Runtime (seconds)", fontsize=19)
plt.xscale("log", base=2)
plt.yscale("log")
draw_loglog_slope(fig, ax, (64, 0.05), 1, 2, "black")
draw_loglog_slope(fig, ax, (300, 2), 1, 4, "black")
plt.legend()
# plt.title(title)
plt.grid(True)
plt.tight_layout()
plt.savefig("runtimes_only_standard_all.pdf")


# plot only standard iterations
iterations_1 = (
    data_1.groupby("dim")["standard_iterations_no_allocation"].agg(["mean", "std"]).reset_index()
)
iterations_2 = (
    data_2.groupby("dim")["standard_iterations_no_allocation"].agg(["mean", "std"]).reset_index()
)
iterations_3 = (
    data_3.groupby("dim")["standard_iterations_no_allocation"].agg(["mean", "std"]).reset_index()
)
iterations_4 = (
    data_4.groupby("dim")["standard_iterations_no_allocation"].agg(["mean", "std"]).reset_index()
)

fig, ax = plt.subplots(figsize=(8, 6))
colors = plt.get_cmap("tab10").colors

ax.errorbar(
    iterations_1["dim"],
    iterations_1["mean"],
    yerr=iterations_1["std"],
    fmt="s-",
    capsize=5,
    label=r"$\tilde{E} = 0.2, \nu = 0.3$",
    color=colors[0],
)
ax.errorbar(
    iterations_2["dim"],
    iterations_2["mean"],
    yerr=iterations_2["std"],
    fmt="s-",
    capsize=5,
    label=r"$\tilde{E} = 0.2, \nu = 0.6$",
    color=colors[1],
)
ax.errorbar(
    iterations_3["dim"],
    iterations_3["mean"],
    yerr=iterations_3["std"],
    fmt="s-",
    capsize=5,
    label=r"$\tilde{E} = 0.5, \nu = 0.3$",
    color=colors[2],
)
ax.errorbar(
    iterations_4["dim"],
    iterations_4["mean"],
    yerr=iterations_4["std"],
    fmt="s-",
    capsize=5,
    label=r"$\tilde{E} = 0.5, \nu = 0.6$",
    color=colors[3],
)
plt.xlabel("n", fontsize=19)
plt.ylabel("Timesteps", fontsize=19)
plt.xscale("log", base=2)
plt.yscale("log")
draw_loglog_slope(fig, ax, (64, 1000), 1, 2, "black")
plt.legend()
plt.tight_layout()
plt.savefig("iterations_all.pdf")
