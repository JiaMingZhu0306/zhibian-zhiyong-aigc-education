"""声明模板、班级报告与配套文本生成。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"


def generate_ai_statement_template() -> str:
    """生成学生 AI 使用声明模板。"""
    return (
        "AI 辅助生成，仅供教师参考。\n\n"
        "# 学生 AI 使用声明\n\n"
        "作业名称：__________\n"
        "年级：__________\n"
        "日期：__________\n\n"
        "1. 我是否使用了生成式 AI：□ 是  □ 否\n\n"
        "2. 我在哪些环节使用了 AI：\n"
        "□ 选题  □ 提纲  □ 查资料  □ 润色  □ 翻译  □ 改写  □ 其他：__________\n\n"
        "3. 我使用的提示词是：\n"
        "____________________________________________\n\n"
        "4. 哪些内容由我自己完成：\n"
        "____________________________________________\n\n"
        "5. 哪些内容经过我修改：\n"
        "____________________________________________\n\n"
        "6. 我是否理解 AI 可能产生错误：□ 是  □ 否\n\n"
        "7. 我的承诺：\n"
        "我承诺不直接复制 AI 结果作为个人原创成果；如使用 AI，我会说明使用过程、核实重要信息，并保留自己的思考和修改记录。\n"
    )


def generate_reflection_questions() -> str:
    """生成学生反思问题。"""
    return (
        "AI 辅助生成，仅供教师参考。\n\n"
        "1. AI 给出的内容中哪些地方需要核实？\n"
        "2. 你对 AI 输出做了哪些修改？\n"
        "3. 哪一部分最能体现你自己的思考？\n"
        "4. 你保留了哪些草稿或修改记录？\n"
        "5. 下次你会如何更规范地使用 AI？"
    )


def generate_class_report(stats: Dict[str, object], df: pd.DataFrame) -> str:
    """根据仪表盘统计生成班级分析报告 Markdown。"""
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    risk_lines = "\n".join([f"- {k}：{v}" for k, v in stats.get("risk_distribution", {}).items()]) or "- 暂无记录"
    type_lines = "\n".join([f"- {k}：{v}" for k, v in stats.get("type_distribution", {}).items()]) or "- 暂无记录"
    issue_lines = "\n".join([f"- {k}：{v} 次" for k, v in stats.get("common_issues", [])]) or "- 暂无记录"
    topic_lines = "\n".join([f"- {topic}" for topic in stats.get("suggested_topics", [])]) or "- 暂无建议"

    return (
        "# 班级 AIGC 作业规范使用分析报告\n\n"
        f"生成时间：{generated_at}\n\n"
        "本报告仅供教师参考，风险提示需结合草稿、访谈、学生 AI 使用声明综合判断，"
        "不作为纪律处分依据。示例数据和导出记录应保持匿名化。\n\n"
        "## 一、总体情况\n"
        f"- 总提交数量：{stats.get('total', 0)}\n"
        f"- 已填写 AI 使用声明比例：{float(stats.get('statement_ratio', 0)) * 100:.1f}%\n\n"
        "## 二、风险分布\n"
        f"{risk_lines}\n\n"
        "## 三、作业类型分布\n"
        f"{type_lines}\n\n"
        "## 四、常见问题频次\n"
        f"{issue_lines}\n\n"
        "## 五、建议开展的班会主题\n"
        f"{topic_lines}\n\n"
        "## 六、教师后续建议\n"
        "- 选择 2-3 篇匿名文本进行课堂讨论，重点分析资料来源、草稿证据和个人表达。\n"
        "- 引导学生填写 AI 使用声明，把技术使用从隐性行为转为可讨论的学习过程。\n"
        "- 对中高风险文本开展温和访谈，了解写作过程，不作单一结论。\n\n"
        "AI 辅助生成，仅供教师参考。"
    )


def write_demo_class_report(stats: Dict[str, object], df: pd.DataFrame) -> Path:
    """写入演示班级报告。"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORTS_DIR / "demo_class_report.md"
    output_path.write_text(generate_class_report(stats, df), encoding="utf-8")
    return output_path

