"""plotter_app_icons.py — Chart-type icon drawing functions for Claude Plotter sidebar."""

SB_ITEM_H    = 56
SB_ICON_SIZE = 28
SB_WIDTH     = 160


def icon_bar(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    heights = [18, 10, 14]
    xs = [6, 13, 20]
    for x, h in zip(xs, heights):
        c.create_rectangle(x, 26 - h, x + 5, 26, fill=fg_color, outline=fg_color)


def icon_line(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 4, 4, fill=fg_color, width=1)
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    pts = [(5, 20), (10, 12), (16, 16), (22, 6)]
    for i in range(len(pts) - 1):
        c.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], fill=fg_color, width=1)
    for x, y in pts:
        c.create_oval(x-2, y-2, x+2, y+2, fill=fg_color, outline=fg_color)


def icon_grouped_bar(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    pairs = [(5, 14), (14, 8)]
    offsets = [0, 5]
    colors = [fg_color, "#aaaaaa"]
    for px, h in pairs:
        for i, (off, col) in enumerate(zip(offsets, colors)):
            c.create_rectangle(px + off, 26 - h - (i * 4), px + off + 4, 26,
                                fill=col, outline=col)


def icon_box(canvas, fg_color, bg_color):
    c = canvas
    groups = [(5, 8, 18, 14, 22), (16, 6, 16, 12, 20)]
    for x, wh_top, box_top, med, box_bot in groups:
        c.create_line(x, wh_top, x, box_top, fill=fg_color, width=1)
        c.create_line(x-2, wh_top, x+2, wh_top, fill=fg_color, width=1)
        c.create_rectangle(x-3, box_top, x+3, box_bot, outline=fg_color)
        c.create_line(x-3, med, x+3, med, fill=fg_color, width=2)
        c.create_line(x, box_bot, x, 24, fill=fg_color, width=1)
        c.create_line(x-2, 24, x+2, 24, fill=fg_color, width=1)


def icon_scatter(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 4, 4, fill=fg_color, width=1)
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    dots = [(7,22),(10,14),(13,18),(16,10),(19,8),(22,14),(8,8),(20,20),(14,6)]
    for x, y in dots:
        c.create_oval(x-1, y-1, x+1, y+1, fill=fg_color, outline=fg_color)


def icon_violin(canvas, fg_color, bg_color):
    c = canvas
    pts_right = [14,4, 18,8, 20,14, 18,20, 14,24]
    pts_left  = [14,4, 10,8, 8,14, 10,20, 14,24]
    c.create_line(*pts_right, fill=fg_color, width=1, smooth=True)
    c.create_line(*pts_left,  fill=fg_color, width=1, smooth=True)
    c.create_line(8, 14, 20, 14, fill=fg_color, width=2)


def icon_survival(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 4, 4, fill=fg_color, width=1)
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    steps = [(4,6),(10,6),(10,12),(16,12),(16,18),(22,18),(22,24)]
    for i in range(len(steps)-1):
        c.create_line(steps[i][0], steps[i][1], steps[i+1][0], steps[i+1][1],
                      fill=fg_color, width=1)


def icon_heatmap(canvas, fg_color, bg_color):
    c = canvas
    shades = [
        ["#444444", "#888888", fg_color],
        ["#888888", fg_color, "#cccccc"],
        [fg_color, "#cccccc", "#eeeeee"],
    ]
    for row in range(3):
        for col in range(3):
            x0 = 4 + col * 8
            y0 = 4 + row * 8
            c.create_rectangle(x0, y0, x0+7, y0+7, fill=shades[row][col], outline=bg_color)


def icon_two_way(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    bars = [(5, 16, fg_color), (10, 10, "#aaaaaa"), (15, 14, fg_color), (20, 8, "#aaaaaa")]
    for x, h, col in bars:
        c.create_rectangle(x, 26-h, x+4, 26, fill=col, outline=col)


def icon_before_after(canvas, fg_color, bg_color):
    c = canvas
    pairs = [(6, 18, 14), (14, 20, 10), (22, 16, 8)]
    for x, y1, y2 in pairs:
        c.create_line(x, y1, x, y2, fill=fg_color, width=1)
        c.create_oval(x-2, y1-2, x+2, y1+2, fill=fg_color, outline=fg_color)
        c.create_oval(x-2, y2-2, x+2, y2+2, fill=bg_color, outline=fg_color)


def icon_histogram(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    heights = [8, 14, 18, 14, 10, 6]
    for i, h in enumerate(heights):
        x = 4 + i * 4
        c.create_rectangle(x, 26-h, x+4, 26, fill=fg_color, outline=bg_color)


def icon_subcolumn(canvas, fg_color, bg_color):
    c = canvas
    groups = [(7, [20, 14, 18]), (14, [10, 16, 12]), (21, [8, 14, 10])]
    for gx, ys in groups:
        c.create_line(gx-2, sum(ys)//len(ys), gx+2, sum(ys)//len(ys), fill=fg_color, width=2)
        for y in ys:
            c.create_oval(gx-1, y-1, gx+1, y+1, fill=fg_color, outline=fg_color)


def icon_curve_fit(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 4, 4, fill=fg_color, width=1)
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    c.create_line(5, 24, 8, 22, 12, 16, 16, 10, 20, 7, 24, 6,
                  fill=fg_color, width=1, smooth=True)
    dots = [(6, 23), (10, 18), (15, 11), (20, 7), (23, 6)]
    for x, y in dots:
        c.create_oval(x-2, y-2, x+2, y+2, fill=bg_color, outline=fg_color)


def icon_col_stats(canvas, fg_color, bg_color):
    c = canvas
    c.create_rectangle(4, 4, 24, 10, fill=fg_color, outline=fg_color)
    for row in range(3):
        y = 11 + row * 5
        c.create_rectangle(4, y, 24, y+4, outline=fg_color)


def icon_contingency(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    bars = [(5, 14, fg_color), (12, 10, "#aaaaaa"), (19, 18, fg_color)]
    for x, h, col in bars:
        c.create_rectangle(x, 26-h, x+6, 26, fill=col, outline=col)


def icon_repeated(canvas, fg_color, bg_color):
    c = canvas
    subjects = [(6, [20, 12, 8]), (14, [16, 8, 14]), (22, [18, 14, 6])]
    timepoints = [6, 14, 22]
    # draw lines connecting each subject across timepoints
    all_dots = [(6, 20), (14, 12), (22, 8),
                (6, 16), (14, 8), (22, 14),
                (6, 18), (14, 14), (22, 6)]
    for s in subjects:
        gx, ys = s
        for i, y in enumerate(ys):
            c.create_oval(gx-2, y-2, gx+2, y+2, fill=fg_color, outline=fg_color)
    # connect same subject across time
    for row in range(3):
        pts = [(subjects[t][0], subjects[t][1][row]) for t in range(3)]
        for i in range(len(pts)-1):
            c.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                          fill=fg_color, width=1)


def icon_chi_square_gof(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    bars = [(5, 14), (12, 10), (19, 16)]
    for x, h in bars:
        c.create_rectangle(x, 26-h, x+6, 26, fill=fg_color, outline=fg_color)
    c.create_line(4, 12, 26, 12, fill=fg_color, width=1, dash=(3, 2))


def icon_stacked_bar(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    bars = [(5, 10, 8), (12, 8, 10), (19, 12, 6)]
    for x, h1, h2 in bars:
        c.create_rectangle(x, 26-h1, x+6, 26, fill=fg_color, outline=fg_color)
        c.create_rectangle(x, 26-h1-h2, x+6, 26-h1, fill="#aaaaaa", outline="#aaaaaa")


def icon_bubble(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 4, 4, fill=fg_color, width=1)
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    bubbles = [(8, 20, 3), (14, 12, 5), (20, 18, 2), (22, 8, 4)]
    for x, y, r in bubbles:
        c.create_oval(x-r, y-r, x+r, y+r, outline=fg_color, fill="")


def icon_dot_plot(canvas, fg_color, bg_color):
    c = canvas
    groups = [(8, [8, 12, 16, 14, 10]), (20, [6, 10, 14, 12, 8])]
    for gx, ys in groups:
        mean_y = sum(ys) // len(ys)
        c.create_line(gx-3, mean_y, gx+3, mean_y, fill=fg_color, width=2)
        for i, y in enumerate(ys):
            jx = gx + (i % 2) * 2 - 1
            c.create_oval(jx-1, y-1, jx+1, y+1, fill=fg_color, outline=fg_color)


def icon_bland_altman(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 4, 4, fill=fg_color, width=1)
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    c.create_line(4, 14, 26, 14, fill=fg_color, width=1)
    c.create_line(4, 8, 26, 8, fill=fg_color, width=1, dash=(3, 2))
    c.create_line(4, 20, 26, 20, fill=fg_color, width=1, dash=(3, 2))
    dots = [(8, 12), (12, 16), (16, 10), (20, 18), (22, 14)]
    for x, y in dots:
        c.create_oval(x-2, y-2, x+2, y+2, fill=fg_color, outline=fg_color)


def icon_forest_plot(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(14, 4, 14, 26, fill=fg_color, width=1, dash=(2, 2))
    rows = [(8, 10, 18), (6, 12, 20), (9, 13, 17)]
    ys = [8, 14, 20]
    for (lo, mid, hi), y in zip(rows, ys):
        c.create_line(lo, y, hi, y, fill=fg_color, width=1)
        c.create_rectangle(mid-2, y-2, mid+2, y+2, fill=fg_color, outline=fg_color)
    c.create_polygon(11, 25, 14, 23, 17, 25, 14, 27, fill=fg_color, outline=fg_color)


def icon_wiki(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(14, 6, 14, 24, fill=fg_color, width=1)
    c.create_rectangle(4, 6, 14, 24, outline=fg_color)
    c.create_rectangle(14, 6, 24, 24, outline=fg_color)
    for y in [10, 14, 18]:
        c.create_line(6, y, 12, y, fill=fg_color, width=1)
        c.create_line(16, y, 22, y, fill=fg_color, width=1)


def icon_area_chart(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 4, 4, fill=fg_color, width=1)
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    pts = [4, 26, 4, 18, 10, 12, 16, 8, 22, 14, 26, 26]
    c.create_polygon(*pts, fill=fg_color, outline=fg_color, stipple="")
    c.create_line(4, 18, 10, 12, 16, 8, 22, 14, 26, 22, fill=bg_color, width=1)


def icon_raincloud(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(14, 4, 18, 8, 20, 14, 18, 20, 14, 24,
                  fill=fg_color, width=1, smooth=True)
    c.create_line(14, 4, 14, 24, fill=fg_color, width=1)
    dots = [(8, 10), (7, 15), (9, 20), (11, 12), (10, 18)]
    for x, y in dots:
        c.create_oval(x-1, y-1, x+1, y+1, fill=fg_color, outline=fg_color)


def icon_qq_plot(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 4, 4, fill=fg_color, width=1)
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    c.create_line(5, 25, 25, 5, fill=fg_color, width=1, dash=(3, 2))
    dots = [(7, 22), (10, 17), (14, 13), (18, 9), (22, 6)]
    for x, y in dots:
        jx, jy = x + (1 if x % 2 else -1), y + (1 if y % 3 else -1)
        c.create_oval(jx-2, jy-2, jx+2, jy+2, fill=bg_color, outline=fg_color)


def icon_lollipop(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    lollipops = [(7, 18), (12, 10), (17, 14), (22, 8)]
    for x, y in lollipops:
        c.create_line(x, 26, x, y + 2, fill=fg_color, width=1)
        c.create_oval(x-2, y-2, x+2, y+2, fill=bg_color, outline=fg_color)


def icon_waterfall(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    bars = [(5, 20, 14, True), (10, 14, 10, False), (15, 10, 16, True), (20, 16, 12, False)]
    for x, base, top, going_up in bars:
        col = fg_color if going_up else "#aaaaaa"
        c.create_rectangle(x, top, x+4, base, fill=col, outline=col)
    c.create_line(9, 14, 10, 14, fill=fg_color, width=1)
    c.create_line(14, 10, 15, 10, fill=fg_color, width=1)
    c.create_line(19, 16, 20, 16, fill=fg_color, width=1)


def icon_pyramid(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(14, 4, 14, 26, fill=fg_color, width=1)
    rows = [(6, 8), (4, 6), (3, 4)]
    ys = [8, 14, 20]
    for (lw, rw), y in zip(rows, ys):
        c.create_rectangle(14-lw, y, 14, y+4, fill=fg_color, outline=fg_color)
        c.create_rectangle(14, y, 14+rw, y+4, fill="#aaaaaa", outline="#aaaaaa")


def icon_ecdf(canvas, fg_color, bg_color):
    c = canvas
    c.create_line(4, 26, 4, 4, fill=fg_color, width=1)
    c.create_line(4, 26, 26, 26, fill=fg_color, width=1)
    steps = [(4, 24), (8, 24), (8, 20), (12, 20), (12, 14), (16, 14), (16, 10), (20, 10), (20, 6), (26, 6)]
    for i in range(0, len(steps)-1, 2):
        c.create_line(steps[i][0], steps[i][1], steps[i+1][0], steps[i+1][1],
                      fill=fg_color, width=1)
    for i in range(1, len(steps)-1, 2):
        c.create_line(steps[i][0], steps[i][1], steps[i+1][0], steps[i+1][1],
                      fill=fg_color, width=1)


ICON_FN = {
    "bar": icon_bar,
    "line": icon_line,
    "grouped_bar": icon_grouped_bar,
    "box": icon_box,
    "scatter": icon_scatter,
    "violin": icon_violin,
    "kaplan_meier": icon_survival,
    "heatmap": icon_heatmap,
    "two_way_anova": icon_two_way,
    "before_after": icon_before_after,
    "histogram": icon_histogram,
    "subcolumn_scatter": icon_subcolumn,
    "curve_fit": icon_curve_fit,
    "column_stats": icon_col_stats,
    "contingency": icon_contingency,
    "repeated_measures": icon_repeated,
    "chi_square_gof": icon_chi_square_gof,
    "stacked_bar": icon_stacked_bar,
    "bubble": icon_bubble,
    "dot_plot": icon_dot_plot,
    "bland_altman": icon_bland_altman,
    "forest_plot": icon_forest_plot,
    "wiki": icon_wiki,
    "area_chart": icon_area_chart,
    "raincloud": icon_raincloud,
    "qq_plot": icon_qq_plot,
    "lollipop": icon_lollipop,
    "waterfall": icon_waterfall,
    "pyramid": icon_pyramid,
    "ecdf": icon_ecdf,
}
