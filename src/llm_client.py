"""OpenAI-compatible 大模型接口。

未配置 API Key 时，系统会自动使用本地模板，保证演示流程不中断。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


def _load_local_env() -> None:
    """显式读取项目根目录 .env，兼容未安装 python-dotenv 的本地环境。"""
    try:
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH)
    except Exception:
        pass

    if not ENV_PATH.exists():
        return
    for raw_line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


try:
    _load_local_env()
except Exception:
    pass


def get_llm_config() -> Dict[str, Optional[str]]:
    """读取 OpenAI-compatible 环境变量配置。"""
    return {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL"),
        "model": os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
    }


def is_llm_configured() -> bool:
    """判断是否配置了可调用的大模型接口。"""
    return bool(get_llm_config().get("api_key"))


def _call_openai_compatible(prompt: str) -> Optional[str]:
    config = get_llm_config()
    if not config.get("api_key"):
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=config["api_key"], base_url=config.get("base_url") or None)
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {
                    "role": "system",
                    "content": "你是面向中学教师的 AI 素养教学助手。输出必须谨慎、中文、可执行，并标注 AI 辅助生成，仅供教师参考。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        return response.choices[0].message.content
    except Exception as exc:
        return f"当前大模型调用失败，系统使用本地模板生成演示反馈。错误摘要：{exc}"


def generate_teacher_feedback(context: str) -> str:
    """生成教师反馈；未配置 API 时返回模板。"""
    prompt = f"请基于以下文本分析上下文，生成一段教学反馈，避免绝对化判断：\n{context}"
    content = _call_openai_compatible(prompt)
    if content and not content.startswith("当前大模型调用失败"):
        return f"{content}\n\nAI 辅助生成，仅供教师参考。"
    fallback = (
        "当前未配置大模型 API，系统使用本地模板生成演示反馈。\n\n"
        "建议教师将风险提示作为课堂讨论材料，引导学生说明资料来源、写作过程和 AI 辅助使用情况。"
        "对文本中较概括、较模板化的段落，可要求学生补充真实经历、草稿证据和个人修改说明。\n\n"
        "AI 辅助生成，仅供教师参考。"
    )
    if content:
        fallback = f"{content}\n\n{fallback}"
    return fallback


def generate_class_meeting_plan(stats_summary: str) -> str:
    """根据班级统计摘要生成 AI 素养班会方案。"""
    prompt = (
        "请根据以下班级统计摘要，生成一份中学生生成式 AI 规范使用班会课方案，"
        "包括教学目标、导入问题、正反案例、小组讨论题、学生承诺语、教师总结语。"
        f"\n\n班级统计摘要：\n{stats_summary}"
    )
    content = _call_openai_compatible(prompt)
    if content and not content.startswith("当前大模型调用失败"):
        return f"{content}\n\n本内容由 AI 辅助生成，仅供教师参考。"
    return (
        "本内容由 AI 辅助生成，仅供教师参考。\n\n"
        "# 《我可以用 AI 写作业吗？——中学生生成式 AI 规范使用课》\n\n"
        "## 一、教学目标\n"
        "1. 了解生成式 AI 在学习中的常见用途和可能风险。\n"
        "2. 学会区分资料辅助、语言润色和直接替代个人思考。\n"
        "3. 能够填写 AI 使用声明，形成透明、规范、负责任的学习习惯。\n\n"
        "## 二、导入问题\n"
        "如果 AI 帮你写出一段很流畅的文字，这段文字能不能直接作为自己的作业提交？为什么？\n\n"
        "## 三、正反案例\n"
        "正向案例：学生先完成提纲，再请 AI 提供资料核对方向，最后用自己的经历和课堂笔记重写。\n\n"
        "反向案例：学生直接复制 AI 输出，未核实事实，也未说明使用过程，导致观点空泛、资料来源不清。\n\n"
        "## 四、小组讨论题\n"
        "1. 哪些环节可以合理使用 AI？\n"
        "2. 哪些内容必须体现自己的思考？\n"
        "3. 如果 AI 输出有错误，我们应该如何核实？\n"
        "4. 怎样填写一份清楚的 AI 使用声明？\n\n"
        "## 五、学生承诺语\n"
        "我可以把 AI 作为学习助手，但不直接复制 AI 结果作为个人原创成果；我会说明使用过程，核实重要信息，保留自己的思考和修改记录。\n\n"
        "## 六、教师总结语\n"
        "规范使用 AI 不是拒绝技术，而是学会透明、负责地使用技术，让 AI 帮助我们学习，而不是替代我们思考。"
    )
