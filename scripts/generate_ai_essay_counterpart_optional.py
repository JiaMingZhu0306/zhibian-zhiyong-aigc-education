"""可选：生成 AI 作文对照集。

默认不在主流程中运行。用途是后续构造 synthetic AI counterpart，不能冒充真实学生作文。

执行示例：
    python scripts/generate_ai_essay_counterpart_optional.py --limit 20
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "student_essay_external_validation.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ai_essay_counterpart_optional.csv"


def get_config() -> Dict[str, str]:
    try:
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env")
    except Exception:
        pass
    return {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "base_url": os.getenv("OPENAI_BASE_URL", ""),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }


def call_model(prompt: str, config: Dict[str, str]) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"] or None)
    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {
                "role": "system",
                "content": "你是作文生成助手。生成内容必须标注为 AI 生成样例，不得冒充真实学生作文。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content or ""


def build_prompt(row: pd.Series) -> str:
    text = str(row.get("text", ""))
    sample = text[:240].replace("\n", " ")
    grade = row.get("grade", "未记录")
    category = row.get("category", "未记录")
    return (
        "请生成一篇 synthetic AI counterpart 作文，用于模型研究对照。"
        "不得声称是真实学生作文，开头必须写“【AI 生成样例】”。\n\n"
        f"年级：{grade}\n"
        f"文体/类别：{category}\n"
        f"参考主题片段：{sample}\n\n"
        "要求：中文，结构完整，避免出现真实姓名、学校和班级。"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="最多生成多少条对照样本")
    args = parser.parse_args()

    config = get_config()
    if not config["api_key"]:
        print("未配置 OPENAI_API_KEY，跳过 AI 作文对照集生成。")
        print("该脚本为可选增强，不影响当前 formal_public 模型结果。")
        return 0
    if not INPUT_PATH.exists():
        print(f"未找到学生作文外部验证集：{INPUT_PATH}")
        print("请先运行 python scripts/prepare_student_essay_external_validation.py")
        return 0

    df = pd.read_csv(INPUT_PATH)
    rows: List[Dict[str, object]] = []
    for _, row in df.head(args.limit).iterrows():
        prompt = build_prompt(row)
        try:
            generated = call_model(prompt, config)
        except Exception as exc:
            print(f"生成失败，跳过 essay_id={row.get('essay_id')}：{exc}")
            continue
        rows.append(
            {
                "original_essay_id": row.get("essay_id"),
                "prompt": prompt,
                "generated_text": generated,
                "model_name": config["model"],
                "label": "ai_synthetic",
                "source_dataset": "ai_generated_counterpart",
            }
        )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"已生成可选 AI 作文对照集：{OUTPUT_PATH}")
    print("注意：这是 synthetic AI counterpart，不是真实学生作文，不参与当前正式模型训练。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

