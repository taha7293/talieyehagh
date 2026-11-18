import math
from typing import List, Tuple, Optional


def eslimi_rosette_svg(color_primary: str = "#0d9488", color_secondary: str = "#16a34a") -> str:
    """گل شمسه کوچک اسلیمی برای کنار تیتر بخش‌ها"""
    return f"""
    <svg width="20" height="20" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg" style="vertical-align: middle; margin-left: 6px;">
        <g transform="translate(20,20)">
            <circle r="17" fill="none" stroke="{color_primary}" stroke-width="1.5" stroke-dasharray="3,2"/>
            <path d="M0,-15 Q6,-6 15,0 Q6,6 0,15 Q-6,6 -15,0 Q-6,-6 0,-15 Z" fill="{color_primary}" fill-opacity="0.18" stroke="{color_primary}" stroke-width="1.6"/>
            <path d="M-11,-11 Q0,-6 11,-11 Q6,0 11,11 Q0,6 -11,11 Q-6,0 -11,-11 Z" fill="{color_secondary}" fill-opacity="0.18" stroke="{color_secondary}" stroke-width="1.3"/>
            <circle r="4.2" fill="{color_primary}"/>
            <circle r="1.8" fill="#ffffff"/>
        </g>
    </svg>
    """


def eslimi_corner_svg(flip_x: bool = False, flip_y: bool = False) -> str:
    """گوشواره اسلیمی برای زینت گوشه‌های کادر صفحه"""
    sx = -1 if flip_x else 1
    sy = -1 if flip_y else 1
    return f"""
    <svg width="52" height="52" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg">
        <g transform="translate(30,30) scale({sx},{sy}) translate(-30,-30)">
            <path d="M4,4 L54,4 M4,4 L4,54" stroke="#0e7490" stroke-width="2" stroke-opacity="0.45"/>
            <path d="M8,8 C22,8 30,14 34,26 C26,22 20,22 14,26 C18,18 16,12 8,8 Z" fill="#14b8a6" fill-opacity="0.22" stroke="#0d9488" stroke-width="1.2"/>
            <path d="M8,8 C8,22 14,30 26,34 C22,26 22,20 26,14 C18,18 12,16 8,8 Z" fill="#16a34a" fill-opacity="0.22" stroke="#15803d" stroke-width="1.2"/>
            <path d="M10,10 Q28,10 38,4 M10,10 Q10,28 4,38" fill="none" stroke="#0284c7" stroke-width="1.1" stroke-opacity="0.55"/>
            <circle cx="10" cy="10" r="2.8" fill="#0e7490"/>
        </g>
    </svg>
    """


def svg_radar_chart(
    labels: List[str],
    values: List[float],
    max_val: float,
    color: str = "#0e7490",
    fill_opacity: float = 0.24,
    width: int = 370,
    height: int = 275,
    rings: int = 5,
) -> str:
    n = len(labels)
    cx, cy = width / 2.0, height / 2.0
    radius = min(width, height) * 0.30

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="font-family: Vazirmatn, Noto Sans Arabic, Nazli, Tahoma, sans-serif;">'
    ]

    for r_idx in range(1, rings + 1):
        r = radius * (r_idx / rings)
        pts = []
        for i in range(n):
            angle = -math.pi / 2 + (2 * math.pi * i / n)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            pts.append(f"{x:.1f},{y:.1f}")
        parts.append(
            f'<polygon points="{" ".join(pts)}" fill="none" stroke="#cbd5e1" stroke-width="0.9"/>'
        )
        ring_val = round(max_val * r_idx / rings)
        parts.append(
            f'<text x="{cx + 4:.1f}" y="{cy - r + 4:.1f}" font-size="8.5" fill="#64748b">{ring_val}</text>'
        )

    for i, label in enumerate(labels):
        angle = -math.pi / 2 + (2 * math.pi * i / n)
        x_end = cx + radius * math.cos(angle)
        y_end = cy + radius * math.sin(angle)
        parts.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x_end:.1f}" y2="{y_end:.1f}" '
            f'stroke="#cbd5e1" stroke-width="0.9"/>'
        )

        lx = cx + (radius + 22) * math.cos(angle)
        ly = cy + (radius + 17) * math.sin(angle)
        cos_a = math.cos(angle)
        if abs(cos_a) < 0.2:
            anchor = "middle"
        elif cos_a > 0:
            anchor = "start"
        else:
            anchor = "end"

        parts.append(
            f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="{anchor}" '
            f'font-size="10.2" font-weight="700" fill="#0f4c5c">{label}</text>'
        )

    data_pts = []
    dots = []
    for i, val in enumerate(values):
        ratio = max(0.0, min(1.0, val / max_val)) if max_val > 0 else 0
        angle = -math.pi / 2 + (2 * math.pi * i / n)
        x = cx + radius * ratio * math.cos(angle)
        y = cy + radius * ratio * math.sin(angle)
        data_pts.append(f"{x:.1f},{y:.1f}")
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{color}" stroke="#ffffff" stroke-width="1.3"/>')

    parts.append(
        f'<polygon points="{" ".join(data_pts)}" fill="{color}" fill-opacity="{fill_opacity}" '
        f'stroke="{color}" stroke-width="2.3"/>'
    )
    parts.extend(dots)
    parts.append("</svg>")
    return "\n".join(parts)


def svg_bar_chart(
    labels: List[str],
    values: List[float],
    max_val: float,
    colors: Optional[List[str]] = None,
    width: int = 440,
    height: int = 225,
) -> str:
    if colors is None:
        colors = ["#0e7490", "#0284c7", "#0d9488", "#16a34a", "#059669", "#0f766e"]

    pad_left, pad_right, pad_top, pad_bottom = 34, 16, 22, 46
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    n = max(len(labels), 1)
    step = plot_w / n
    bar_w = min(36, step * 0.56)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="font-family: Vazirmatn, Noto Sans Arabic, Nazli, Tahoma, sans-serif;">'
    ]

    for tick in range(0, int(max_val) + 1, 10):
        y = pad_top + plot_h * (1 - tick / max_val)
        parts.append(f'<line x1="{pad_left}" y1="{y:.1f}" x2="{width - pad_right}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(f'<text x="{pad_left - 6}" y="{y + 3:.1f}" text-anchor="end" font-size="9" fill="#64748b">{tick}</text>')

    parts.append(f'<line x1="{pad_left}" y1="{pad_top + plot_h}" x2="{width - pad_right}" y2="{pad_top + plot_h}" stroke="#94a3b8" stroke-width="1.2"/>')

    for i, (label, val) in enumerate(zip(labels, values)):
        bh = (val / max_val) * plot_h if max_val > 0 else 0
        x = pad_left + i * step + (step - bar_w) / 2
        y = pad_top + plot_h - bh
        c = colors[i % len(colors)]
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="5" fill="{c}"/>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 5:.1f}" text-anchor="middle" font-size="10.5" font-weight="800" fill="#0f172a">{val}</text>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{pad_top + plot_h + 18}" text-anchor="middle" font-size="10" font-weight="700" fill="#0f4c5c">{label}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def svg_line_chart(
    labels: List[str],
    values: List[float],
    min_val: float,
    max_val: float,
    color: str = "#0e7490",
    normal_band: Optional[Tuple[float, float]] = None,
    width: int = 660,
    height: int = 215,
    y_step: int = 1,
) -> str:
    pad_left, pad_right, pad_top, pad_bottom = 34, 20, 18, 42
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    n = len(labels)

    def y_pos(v: float) -> float:
        ratio = (v - min_val) / max(max_val - min_val, 1)
        return pad_top + plot_h * (1 - ratio)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="font-family: Vazirmatn, Noto Sans Arabic, Nazli, Tahoma, sans-serif;">'
    ]

    if normal_band is not None:
        y_top = y_pos(normal_band[1])
        y_bot = y_pos(normal_band[0])
        parts.append(
            f'<rect x="{pad_left}" y="{y_top:.1f}" width="{plot_w}" height="{y_bot - y_top:.1f}" '
            f'fill="#99f6e4" fill-opacity="0.45"/>'
        )

    v = int(min_val)
    while v <= int(max_val):
        y = y_pos(v)
        parts.append(f'<line x1="{pad_left}" y1="{y:.1f}" x2="{width - pad_right}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="0.9"/>')
        parts.append(f'<text x="{pad_left - 6}" y="{y + 3:.1f}" text-anchor="end" font-size="9" fill="#64748b">{v}</text>')
        v += y_step

    step_x = plot_w / max(n - 1, 1)
    pts = []
    for i, (label, val) in enumerate(zip(labels, values)):
        x = pad_left + i * step_x
        y = y_pos(val)
        pts.append((x, y, val, label))
        parts.append(f'<line x1="{x:.1f}" y1="{pad_top}" x2="{x:.1f}" y2="{pad_top + plot_h}" stroke="#f1f5f9" stroke-width="0.9"/>')

    poly_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in pts)
    parts.append(f'<polyline points="{poly_pts}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round"/>')

    for x, y, val, label in pts:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.3" fill="{color}" stroke="#ffffff" stroke-width="1.5"/>')
        parts.append(f'<text x="{x:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="9.5" font-weight="800" fill="#0f172a">{val}</text>')
        parts.append(f'<text x="{x:.1f}" y="{pad_top + plot_h + 17}" text-anchor="middle" font-size="9.5" font-weight="700" fill="#0f4c5c">{label}</text>')

    parts.append("</svg>")
    return "\n".join(parts)