"""班级分析看板组件。"""

from __future__ import annotations

import html
import math
from typing import Iterable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.report_generator import generate_class_report, write_demo_class_report
from src.storage import dashboard_stats, load_submissions
from src.ui_components import go_to_page, notice_card, render_header, warning_card


RISK_DISPLAY_ORDER = ["低风险", "中风险", "高风险", "高参考风险"]
RISK_SOURCE_KEYS = {
    "低风险": ["低风险"],
    "中风险": ["中风险"],
    "高风险": ["高风险"],
    "高参考风险": ["高参考风险", "高置信高风险"],
}
RISK_COLORS = {
    "低风险": "#16A34A",
    "中风险": "#D97706",
    "高风险": "#EA580C",
    "高参考风险": "#DC2626",
}
ASSIGNMENT_ORDER = ["作文", "读后感", "学习总结", "研究性学习报告", "其他"]


def clean_label(value: object, default: str = "未记录") -> str:
    if value is None:
        return default
    if isinstance(value, float) and math.isnan(value):
        return default
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "undefined", "null"}:
        return default
    return text


def to_int(value: object) -> int:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return 0
        return int(value)
    except Exception:
        return 0


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def apply_plotly_style(fig: go.Figure, height: int = 270, showlegend: bool = False) -> go.Figure:
    """统一 Plotly 白底主题，避免黑底图表和 undefined 标题。"""
    fig.update_layout(
        template="plotly_white",
        title_text="",
        height=height,
        margin=dict(l=18, r=22, t=8, b=18),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#1F2937", size=13),
        showlegend=showlegend,
        legend=dict(font=dict(color="#4B5563"), orientation="h", yanchor="bottom", y=-0.16),
    )
    fig.update_xaxes(
        showgrid=False,
        gridcolor="#E5E7EB",
        zeroline=False,
        tickfont=dict(color="#4B5563"),
        title_text="",
        tickmode="linear",
        dtick=1,
        tickformat=",d",
        showticklabels=False,
        ticks="",
    )
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        tickfont=dict(color="#4B5563"),
        title_text="",
    )
    return fig


def count_medium_high(risk_distribution: dict[str, int]) -> int:
    return sum(
        to_int(risk_distribution.get(key, 0))
        for key in ["中风险", "高风险", "高参考风险", "高置信高风险"]
    )


def statement_counts(df: pd.DataFrame) -> dict[str, int]:
    if df.empty or "has_ai_statement" not in df.columns:
        return {"已填写": 0, "未填写": 0, "不确定/未记录": 0}
    normalized = df["has_ai_statement"].astype(str).str.strip().str.lower()
    yes = normalized.isin(["true", "1", "yes", "y", "是", "已填写"]).sum()
    no = normalized.isin(["false", "0", "no", "n", "否", "未填写"]).sum()
    unknown = len(df) - int(yes) - int(no)
    return {"已填写": int(yes), "未填写": int(no), "不确定/未记录": max(int(unknown), 0)}


def assignment_type_count(stats: dict[str, object]) -> int:
    return len([k for k, v in stats.get("type_distribution", {}).items() if to_int(v) > 0])


def render_kpi_cards(stats: dict[str, object], df: pd.DataFrame) -> None:
    risk_distribution = stats.get("risk_distribution", {})
    cards = [
        ("本地分析记录", stats.get("total", 0), "匿名文本记录", "01"),
        ("中高风险记录", count_medium_high(risk_distribution), "需教师结合过程材料关注", "02"),
        ("使用声明提交率", f"{float(stats.get('statement_ratio', 0)) * 100:.1f}%", "已填写 AIGC 使用声明", "03"),
        ("覆盖作业类型", assignment_type_count(stats), "作文/读后感/学习总结等", "04"),
    ]
    html_cards = []
    for title, value, desc, mark in cards:
        html_cards.append(
            f"""
<div class="kpi-card">
  <div class="kpi-top">
    <div class="kpi-title">{escape(title)}</div>
    <div class="kpi-mark">{escape(mark)}</div>
  </div>
  <div class="kpi-value">{escape(value)}</div>
  <div class="kpi-desc">{escape(desc)}</div>
</div>
"""
        )
    st.markdown(f'<div class="dashboard-kpi-grid">{"".join(html_cards)}</div>', unsafe_allow_html=True)


def render_observation_summary(stats: dict[str, object]) -> None:
    total = to_int(stats.get("total", 0))
    medium_high = count_medium_high(stats.get("risk_distribution", {}))
    ratio = float(stats.get("statement_ratio", 0)) * 100
    image_ocr = to_int(stats.get("image_ocr_count", 0))
    batch_ocr = to_int(stats.get("batch_ocr_count", 0))
    if total == 0:
        body = "当前暂无本地分析记录。可先在“作业文本分析”模块保存匿名演示样例，再查看班级看板效果。"
    else:
        body = (
            f"当前共汇总 {total} 条匿名文本记录，其中中高风险记录 {medium_high} 条，"
            f"使用声明提交率为 {ratio:.1f}%。建议教师优先关注未提交使用声明且风险等级较高的文本，"
            "并通过草稿、访谈和声明材料进行过程性沟通。"
            f"当前记录包含 {image_ocr} 条单张图片识别记录、{batch_ocr} 条批量图片导入记录。"
        )
    st.markdown(
        f"""
<div class="observation-card">
  <h3>班级观察摘要</h3>
  <p>{escape(body)}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_source_distribution(stats: dict[str, object]) -> None:
    label_map = {
        "manual_analysis": "手动文本输入",
        "image_ocr_manual": "单张图片识别",
        "batch_image_ocr": "批量图片导入",
        "public_dataset_demo": "公开语料演示",
        "demo_seed": "系统演示样例",
    }
    distribution = stats.get("source_distribution", {}) or {}
    rows = []
    for key, count in distribution.items():
        label = label_map.get(clean_label(key), clean_label(key))
        rows.append(
            f"""
<div class="issue-row">
  <div class="issue-name">{escape(label)}</div>
  <div class="issue-count">{to_int(count)} 条</div>
</div>
"""
        )
    if not rows:
        rows.append('<div class="issue-row"><div class="issue-name">暂无来源记录</div><div class="issue-count">0 条</div></div>')
    st.markdown(
        f"""
<div class="dashboard-card">
  <h3>记录来源分布</h3>
  <p>区分手动文本输入、图片识别、批量导入和演示记录。</p>
  {''.join(rows)}
</div>
""",
        unsafe_allow_html=True,
    )


def render_sample_size_notice(total: int) -> None:
    if total == 0:
        return
    if total == 1:
        notice_card("当前仅有 1 条匿名记录，建议保存更多样例后查看趋势。当前图表仅用于演示页面效果。")
    elif total <= 3:
        notice_card("当前记录较少，图表仅用于演示布局。建议保存更多匿名样例后再观察班级趋势。")
    else:
        notice_card("当前看板基于本地匿名记录生成，记录较少时仅用于演示页面效果。")


def normalized_risk_distribution(stats: dict[str, object]) -> pd.DataFrame:
    raw = {clean_label(k): to_int(v) for k, v in stats.get("risk_distribution", {}).items()}
    rows = []
    for display_name in RISK_DISPLAY_ORDER:
        count = sum(raw.get(clean_label(key), 0) for key in RISK_SOURCE_KEYS[display_name])
        rows.append({"风险等级": display_name, "数量": count})
    return pd.DataFrame(rows)


def x_axis_range(max_count: int, total: int) -> list[float]:
    if total <= 3:
        return [0, max(3, max_count + 1)]
    return [0, max(1, max_count) * 1.35]


def plot_risk_distribution(stats: dict[str, object]) -> go.Figure:
    total = to_int(stats.get("total", 0))
    df = normalized_risk_distribution(stats)
    fig = px.bar(
        df,
        x="数量",
        y="风险等级",
        orientation="h",
        text="数量",
        color="风险等级",
        color_discrete_map=RISK_COLORS,
        category_orders={"风险等级": list(reversed(RISK_DISPLAY_ORDER))},
    )
    fig.update_traces(textposition="outside", cliponaxis=False, marker_line_width=0)
    max_count = max(to_int(df["数量"].max()), 1)
    fig.update_xaxes(range=x_axis_range(max_count, total))
    return apply_plotly_style(fig, height=260, showlegend=False)


def plot_statement_status(df: pd.DataFrame) -> go.Figure:
    counts = statement_counts(df)
    labels = [clean_label(label) for label in counts.keys()]
    values = [to_int(value) for value in counts.values()]
    if sum(values) == 0:
        labels = ["暂无数据"]
        values = [1]
        colors = ["#CBD5E1"]
    else:
        colors = ["#2563EB", "#D97706", "#9CA3AF"]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                marker=dict(colors=colors, line=dict(color="white", width=2)),
                textinfo="label+percent",
                hovertemplate="%{label}: %{value} 条<extra></extra>",
            )
        ]
    )
    fig.add_annotation(
        text=f"总数<br><b>{0 if labels == ['暂无数据'] else sum(values)}</b>",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(color="#111827", size=15),
    )
    return apply_plotly_style(fig, height=260, showlegend=True)


def plot_assignment_type_distribution(stats: dict[str, object]) -> go.Figure:
    total = to_int(stats.get("total", 0))
    raw = {clean_label(k): to_int(v) for k, v in stats.get("type_distribution", {}).items()}
    rows = [{"作业类型": key, "数量": raw.get(key, 0)} for key in ASSIGNMENT_ORDER if raw.get(key, 0) > 0]
    rows.extend(
        {"作业类型": key, "数量": value}
        for key, value in raw.items()
        if key not in ASSIGNMENT_ORDER and value > 0
    )
    if not rows:
        rows = [{"作业类型": "暂无记录", "数量": 0}]
    df = pd.DataFrame(rows).sort_values("数量", ascending=True)
    fig = px.bar(df, x="数量", y="作业类型", orientation="h", text="数量", color_discrete_sequence=["#60A5FA"])
    fig.update_traces(textposition="outside", cliponaxis=False, marker_line_width=0)
    max_count = max(to_int(df["数量"].max()), 1)
    fig.update_xaxes(range=x_axis_range(max_count, total))
    return apply_plotly_style(fig, height=260, showlegend=False)


def render_chart_intro(title: str, desc: str) -> None:
    st.markdown(
        f"""
<div class="dashboard-card">
  <h3>{escape(title)}</h3>
  <p>{escape(desc)}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_chart_card(title: str, desc: str, fig: go.Figure) -> None:
    render_chart_intro(title, desc)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def render_common_issues(common_issues: Iterable[tuple[str, int]]) -> None:
    items = [(clean_label(issue, "暂无常见问题记录"), to_int(count)) for issue, count in list(common_issues)[:5]]
    if not items:
        items = [("暂无常见问题记录", 0)]
    rows = []
    for issue, count in items:
        count_text = "待积累" if count == 0 else f"{count} 次"
        rows.append(
            f"""
<div class="issue-row">
  <div class="issue-name">{escape(issue)}</div>
  <div class="issue-count">{escape(count_text)}</div>
</div>
"""
        )
    st.markdown(
        f"""
<div class="dashboard-card">
  <h3>常见问题统计</h3>
  <p>展示可解释反馈中出现较多的问题。</p>
  {''.join(rows)}
</div>
""",
        unsafe_allow_html=True,
    )


def render_action_suggestions() -> None:
    cards = [
        ("过程核对", "对中高风险文本，建议核对草稿、修改记录和学生使用声明。"),
        ("班级教育", "如果同类问题集中出现，可开展 AIGC 规范使用主题班会。"),
        ("持续记录", "建议使用匿名记录持续观察，不公开展示学生原文。"),
    ]
    html_cards = []
    for title, body in cards:
        html_cards.append(
            f"""
<div class="action-card">
  <h3>{escape(title)}</h3>
  <p>{escape(body)}</p>
</div>
"""
        )
    st.markdown(f'<div class="action-grid">{"".join(html_cards)}</div>', unsafe_allow_html=True)


def render_empty_state(pages: list[tuple[str, str]]) -> None:
    st.markdown(
        """
<div class="empty-dashboard">
  <h3>暂无本地分析记录</h3>
  <p>当前看板尚未读取到匿名文本分析记录。可先进入“作业文本分析”模块，保存 3–5 条匿名演示样例，再返回本页面查看统计效果。</p>
</div>
""",
        unsafe_allow_html=True,
    )
    if st.button("前往作业文本分析模块", use_container_width=True):
        go_to_page("作业文本分析", pages)
    warning_card("匿名演示记录仅用于系统展示，不代表真实学生数据。")


def render_dashboard_page(pages: list[tuple[str, str]]) -> None:
    """渲染班级分析看板。"""
    render_header(
        "班级分析看板",
        "汇总本地匿名作业文本分析记录，辅助教师了解班级 AIGC 使用声明填写情况与文本风险分布。",
        "📊",
    )
    notice_card("本看板基于本地匿名分析记录生成，仅用于教师开展过程性反馈和班级 AI 素养教育。")

    df = load_submissions()
    stats = dashboard_stats(df)
    total = to_int(stats.get("total", 0))

    render_kpi_cards(stats, df)
    render_sample_size_notice(total)
    render_observation_summary(stats)

    if total == 0:
        render_empty_state(pages)
        return

    if "demo_flag" in df.columns and df["demo_flag"].astype(str).str.lower().isin(["true", "1", "yes"]).any():
        warning_card("当前看板包含匿名演示记录或公开语料演示记录，仅用于系统展示；正式应用时请替换为真实匿名化试用记录。")

    col1, col2 = st.columns(2, gap="large")
    with col1:
        render_chart_card(
            "风险等级分布",
            "横向展示不同风险等级文本数量。",
            plot_risk_distribution(stats),
        )
    with col2:
        render_chart_card(
            "使用声明填写情况",
            "展示学生是否提交 AIGC 使用声明。",
            plot_statement_status(df),
        )

    col3, col4 = st.columns(2, gap="large")
    with col3:
        render_chart_card(
            "作业类型分布",
            "展示当前匿名记录覆盖的作业类型。",
            plot_assignment_type_distribution(stats),
        )
    with col4:
        render_common_issues(stats.get("common_issues", []))

    render_source_distribution(stats)

    st.markdown("### 建议操作")
    render_action_suggestions()

    report_text = generate_class_report(stats, df)
    st.markdown("### 导出报告")
    left, right = st.columns(2)
    if left.button("导出班级分析报告 Markdown", type="primary", use_container_width=True):
        report_path = write_demo_class_report(stats, df)
        st.success(f"已导出：{report_path}")
    right.download_button(
        "下载班级分析报告",
        data=report_text,
        file_name="class_aigc_usage_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
