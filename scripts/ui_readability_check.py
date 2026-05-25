"""UI 可读性专项检查。

重点检查浅色页面中的 tab、selectbox、图表和全局文字颜色，避免白字白底、
黑底图表、默认黑框等影响录屏展示的问题。
"""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "reports" / "ui_readability_check.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def has_tab_dark_rule(css: str) -> bool:
    return (
        'button[data-baseweb="tab"]' in css
        and "color: #1F2937" in css
        and "-webkit-text-fill-color: #1F2937" in css
    )


def has_tab_selected_rule(css: str) -> bool:
    return (
        'button[data-baseweb="tab"][aria-selected="true"]' in css
        and ("#1D4ED8" in css or "#DC2626" in css)
        and "border-bottom" in css
    )


def tab_white_hits(css: str) -> list[str]:
    hits: list[str] = []
    for block in re.findall(r"button\[data-baseweb=\"tab\"\][^{]*\{[^}]*\}", css, flags=re.IGNORECASE | re.DOTALL):
        if re.search(r"(^|[;{]\s*)(color|-webkit-text-fill-color)\s*:\s*(white|#fff|#ffffff)", block, flags=re.IGNORECASE):
            hits.append(block[:120].replace("\n", " "))
    return hits


def global_white_hits(css: str) -> list[str]:
    patterns = [
        r"(?m)^\s*span\s*\{[^}]*color\s*:\s*(#fff|#ffffff|white)",
        r"(?m)^\s*label\s*\{[^}]*color\s*:\s*(#fff|#ffffff|white)",
        r"(?m)^\s*div\s*\{[^}]*color\s*:\s*(#fff|#ffffff|white)",
        r"(?m)^\s*p\s*\{[^}]*color\s*:\s*(#fff|#ffffff|white)",
    ]
    return [pattern for pattern in patterns if re.search(pattern, css, flags=re.IGNORECASE | re.DOTALL)]


def low_opacity_tab_hits(css: str) -> list[str]:
    hits: list[str] = []
    for block in re.findall(r"button\[data-baseweb=\"tab\"\][^{]*\{[^}]*\}", css, flags=re.IGNORECASE | re.DOTALL):
        if re.search(r"opacity\s*:\s*(0|0\.[0-4])\b", block):
            hits.append(block[:120].replace("\n", " "))
    return hits


def black_border_hits(css: str) -> list[str]:
    patterns = [
        r"border\s*:\s*2px\s+solid\s+black",
        r"border-color\s*:\s*black",
        r"(input|select|textarea)[^{]*\{[^}]*border[^;}]*#000000",
    ]
    return [pattern for pattern in patterns if re.search(pattern, css, flags=re.IGNORECASE | re.DOTALL)]


def main() -> int:
    app_text = read(PROJECT_ROOT / "app.py")
    dashboard_text = read(PROJECT_ROOT / "src" / "dashboard_components.py")
    ui_text = read(PROJECT_ROOT / "src" / "ui_components.py")
    requirements = read(PROJECT_ROOT / "requirements.txt")
    combined = "\n".join([app_text, dashboard_text, ui_text])

    tab_white = tab_white_hits(ui_text)
    global_white = global_white_hits(ui_text)
    tab_opacity = low_opacity_tab_hits(ui_text)
    black_border = black_border_hits(ui_text)

    checks: list[tuple[str, bool, str]] = [
        ("未使用 st.bar_chart", "st.bar_chart" not in combined, "班级看板不应使用 Streamlit 默认条形图。"),
        ("未使用 st.dataframe 展示常见问题", "st.dataframe" not in dashboard_text, "常见问题应使用浅色卡片列表。"),
        ("未使用 matplotlib dark_background", "dark_background" not in combined, "禁止黑底 matplotlib 样式。"),
        ("Plotly 依赖已声明", "plotly" in requirements.lower(), "requirements.txt 应包含 plotly。"),
        ("Plotly 使用白底模板", "plotly_white" in dashboard_text, "看板图表应使用浅色主题。"),
        ("Plotly 纸面背景为白色", 'paper_bgcolor="white"' in dashboard_text, "图表外层背景应为白色。"),
        ("Plotly 坐标区背景为白色", 'plot_bgcolor="white"' in dashboard_text, "坐标区背景应为白色。"),
        ("存在 KPI 卡片样式", ".kpi-card" in ui_text, "看板应有管理后台式 KPI 卡片。"),
        ("存在常见问题卡片样式", ".issue-row" in ui_text, "常见问题应为浅色列表。"),
        ("Selectbox 已覆盖 BaseWeb 当前值样式", 'div[data-baseweb="select"]' in ui_text and "-webkit-text-fill-color: #111827" in ui_text, "下拉框选中项应为深色文字。"),
        ("Tab 未选中状态有明确深色文字", has_tab_dark_rule(ui_text), "button[data-baseweb=\"tab\"] 必须设置 #1F2937 深色文字。"),
        ("Tab 选中状态有明确高亮", has_tab_selected_rule(ui_text), "选中 tab 必须有文字高亮和底部强调线。"),
        ("Tab 未设置白色文字", not tab_white, f"疑似 tab 白字规则：{tab_white}"),
        ("未发现全局 span/div/label/p 白字覆盖", not global_white, f"疑似全局白字规则：{global_white}"),
        ("未发现 tab 低透明度规则", not tab_opacity, f"疑似 tab 透明度过低规则：{tab_opacity}"),
        ("未发现输入控件黑色粗边框规则", not black_border, f"疑似黑框规则：{black_border}"),
        ("页面包含作业导入方式说明", "选择作业导入方式" in app_text, "作业文本分析页应说明三种输入方式。"),
    ]

    dangerous_terms = [
        "判定" + "作弊",
        "确定" + "AI" + "生成",
        "AI" + "占比",
        "AIGC" + "率",
        "100%" + "准确",
    ]
    danger_hits = [term for term in dangerous_terms if term in combined]
    checks.append(("未发现危险表述", not danger_hits, f"命中：{danger_hits}"))

    passes = [name for name, ok, _ in checks if ok]
    failures = [(name, message) for name, ok, message in checks if not ok]

    lines = [
        "# UI 可读性专项检查报告",
        "",
        f"通过项：{len(passes)}",
        f"失败项：{len(failures)}",
        "",
        "## 通过项",
    ]
    lines.extend([f"- {name}" for name in passes] or ["- 无"])
    lines.extend(["", "## 失败项"])
    lines.extend([f"- {name}：{message}" for name, message in failures] or ["- 无"])

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"UI 可读性检查：通过 {len(passes)} 项，失败 {len(failures)} 项。")
    print(f"报告：{REPORT_PATH}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
