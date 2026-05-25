"""智辨·智用 Streamlit 应用入口。"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.explanation import build_feedback
from src.llm_client import generate_class_meeting_plan, generate_teacher_feedback, is_llm_configured
from src.dashboard_components import render_dashboard_page
from src.batch_processor import (
    analyze_text_record,
    batch_analyze_records,
    build_anonymous_id,
    process_single_image_upload,
    validate_batch_csv,
)
from src.ocr_utils import get_available_ocr_provider
from src.report_generator import (
    generate_ai_statement_template,
)
from src.risk_model import predict_risk
from src.storage import dashboard_stats, load_submissions, save_submission
from src.ui_components import (
    info_card_grid,
    inject_global_css,
    metric_cards,
    mini_cards,
    notice_card,
    redline_cards,
    render_flow_steps,
    render_footer_note,
    render_header,
    render_top_nav,
    risk_card,
    safety_notice,
    section_title,
    svg_image,
    threshold_legend,
    warning_card,
    go_to_page,
)


st.set_page_config(
    page_title="智辨·智用",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_global_css()


PAGES = [
    ("首页总览", "🏠"),
    ("作业文本分析", "📝"),
    ("使用声明管理", "📋"),
    ("班级分析看板", "📊"),
    ("素养教育资源", "🎓"),
    ("隐私与使用边界", "🛡️"),
]

RISK_INDEX_NOTICE = (
    "AIGC 风险指数表示模型认为文本具有 AI 生成或 AI 润色特征的参考概率，"
    "不代表文本中有多少比例由 AI 生成，也不作为学生违纪判定或纪律处分依据。"
)

ASSIGNMENT_TYPES = ["作文", "读后感", "学习总结", "研究性学习报告", "其他"]
GRADES = ["初一", "初二", "初三", "高一", "高二", "高三"]


def load_demo_examples() -> list[dict[str, str]]:
    """读取增强匿名演示样例，并可附加公开语料高风险样例。"""
    examples: list[dict[str, str]] = []
    enhanced_path = PROJECT_ROOT / "data" / "sample_seed" / "demo_texts_enhanced.csv"
    if enhanced_path.exists():
        try:
            df = pd.read_csv(enhanced_path)
            for _, row in df.iterrows():
                examples.append(
                    {
                        "demo_name": str(row.get("demo_name", "未命名演示样例")),
                        "text": str(row.get("text", "")),
                        "assignment_type": str(row.get("assignment_type", "其他")),
                        "note": str(row.get("note", "演示样例仅用于展示系统功能，不代表真实学生文本。")),
                    }
                )
        except Exception:
            examples = []

    pool_path = PROJECT_ROOT / "data" / "sample_seed" / "hc3_high_risk_demo_pool.csv"
    if pool_path.exists():
        try:
            pool_df = pd.read_csv(pool_path)
            if not pool_df.empty:
                row = pool_df.iloc[0]
                examples.append(
                    {
                        "demo_name": "公开语料高风险样例",
                        "text": str(row.get("text", "")),
                        "assignment_type": "其他",
                        "note": "公开语料演示样例，来自 Human-ChatGPT 对比语料，不是真实学生作文。",
                    }
                )
        except Exception:
            pass

    if not examples:
        examples.append(
            {
                "demo_name": "低风险演示样例 A",
                "text": "那天放学后，雨下得很急。我和同桌一起整理图书角，把破损的书角贴好，又按主题重新分类。这件小事让我觉得，责任感不是很大的口号，而是在别人可能看不见的地方多做一点。",
                "assignment_type": "作文",
                "note": "内置匿名演示样例，仅用于展示系统功能。",
            }
        )
    return examples


def set_analysis_demo(demo_name: str) -> None:
    examples = load_demo_examples()
    selected = next((item for item in examples if item["demo_name"] == demo_name), examples[0])
    st.session_state["analysis_text"] = selected["text"]
    if selected.get("assignment_type") in ASSIGNMENT_TYPES:
        st.session_state["analysis_assignment_type"] = selected["assignment_type"]
    st.session_state["analysis_demo_note"] = selected.get("note", "")
    st.session_state["analysis_demo_loaded_text"] = selected["text"]
    if "公开语料" in selected.get("demo_name", "") or "公开语料" in selected.get("note", ""):
        st.session_state["analysis_demo_source_type"] = "public_dataset_demo"
        st.session_state["analysis_demo_source_note"] = "公开语料演示样例，仅用于系统展示。"
    else:
        st.session_state["analysis_demo_source_type"] = "demo_seed"
        st.session_state["analysis_demo_source_note"] = "匿名演示样例，仅用于系统展示。"
    st.session_state.pop("last_analysis", None)
    st.session_state.pop("analysis_save_status", None)
    st.rerun()


def get_analysis_source_meta(text: str) -> tuple[str, bool, str]:
    """区分手动输入、匿名演示样例和公开语料演示样例。"""
    if text.strip() and text.strip() == str(st.session_state.get("analysis_demo_loaded_text", "")).strip():
        source_type = st.session_state.get("analysis_demo_source_type", "demo_seed")
        source_note = st.session_state.get("analysis_demo_source_note", "匿名演示样例，仅用于系统展示。")
        return str(source_type), True, str(source_note)
    return "manual_analysis", False, "用户手动输入"


def save_analysis_to_dashboard(
    text: str,
    result: dict,
    feedback: dict,
    source_type: str | None = None,
    source_note: str | None = None,
    demo_flag: bool | None = None,
    anonymous_student_id: str = "",
    ocr_confidence: float | None = None,
    ocr_status: str = "",
) -> bool:
    """分析成功后自动同步到班级分析看板，避免重复写入。"""
    text_hash = hashlib.sha256(
        f"{text.strip()}|{result['assignment_type']}|{result['grade']}".encode("utf-8")
    ).hexdigest()[:16]
    if st.session_state.get("last_saved_analysis_hash") == text_hash:
        st.session_state["analysis_save_status"] = "duplicate"
        return False

    if source_type is None or source_note is None or demo_flag is None:
        source_type, demo_flag, source_note = get_analysis_source_meta(text)
    _, saved = save_submission(
        {
            "text": text,
            "text_hash": text_hash,
            "assignment_type": result["assignment_type"],
            "grade": result["grade"],
            "has_ai_statement": "已填写" if result["has_ai_statement"] else "未填写",
            "aigc_risk_index": result["risk_index"],
            "ai_probability": result["ai_probability"],
            "risk_level": result["risk_level"],
            "process_transparency": result["process_transparency"],
            "reasons": "；".join(feedback["reasons"][:5]),
            "suggestions": "；".join(feedback["suggestions"][:5]),
            "source_type": source_type,
            "demo_flag": demo_flag,
            "source_note": source_note,
            "anonymous_student_id": anonymous_student_id,
            "ocr_confidence": ocr_confidence,
            "ocr_status": ocr_status,
        },
        dedupe=True,
    )
    st.session_state["last_saved_analysis_hash"] = text_hash
    st.session_state["analysis_save_status"] = "saved" if saved else "duplicate"
    return saved


def page_home() -> None:
    hero_svg = svg_image("assets/hero_aigc_education.svg", alt="AIGC education system")
    analysis_href = quote("作业文本分析")
    dashboard_href = quote("班级分析看板")
    st.markdown(
        f"""
<div class="hero-grid">
  <div>
    <div class="hero-kicker">🎓 智慧教育 · 智能信息系统</div>
    <h1>智辨·智用</h1>
    <h2>面向中学生的 AIGC 作业规范使用与 AI 素养培养系统</h2>
    <p>面向作文、读后感、学习总结、研究性学习报告等场景，提供 AIGC 风险提示、使用声明、班级分析看板和 AI 素养班会生成。</p>
    <div class="hero-action-row">
      <a class="fake-button" href="?page={analysis_href}">📝 开始文本分析</a>
      <a class="fake-button secondary" href="?page={dashboard_href}">📊 查看班级看板</a>
    </div>
  </div>
  <div class="svg-wrap">{hero_svg}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    section_title("系统数据概览", "公开数据指标用于模型原型验证，不代表对真实学生作文的绝对判断能力。", "数据支撑")
    metric_cards(
        [
            ("公开训练样本", "33,925", "HC3-Chinese 清洗后样本", "📚"),
            ("测试集 F1(ai)", "0.9753", "public_test 上的基线结果", "📈"),
            ("学生作文外部验证", "92,701", "human-only，用于观察误报风险", "🧾"),
            ("应用模块", "5 个", "风险分析、声明、仪表盘、班会、边界", "🧩"),
        ]
    )

    section_title("教师使用流程", "从匿名文本提交到班级层面 AI 素养教育，形成可演示、可复现的闭环。", "流程")
    render_flow_steps(
        [
            ("📝", "文本提交"),
            ("⚖️", "AIGC 风险提示"),
            ("📋", "AI 使用声明"),
            ("📊", "班级分析看板"),
            ("🎓", "AI 素养班会"),
        ]
    )
    safety_notice()

    section_title("适用教学场景", "服务中学真实课堂中的过程管理、反馈引导和规范使用教育。", "场景")
    info_card_grid(
        [
            ("作文批改前辅助筛查", "对匿名文本进行风险提示，帮助教师决定是否需要进一步了解写作过程。", "✍️"),
            ("研究性学习报告过程管理", "引导学生说明资料来源、AI 辅助环节和自己的修改记录。", "🔎"),
            ("班主任 AI 素养主题班会", "根据班级统计结果生成讨论题、案例和承诺语。", "🎓"),
            ("学生 AI 使用声明与反思", "把“偷偷使用”转化为透明、规范、负责任的学习过程。", "📋"),
        ]
    )

    if not is_llm_configured():
        warning_card("当前未配置大模型 API，系统使用本地模板生成演示反馈。")


def run_analysis(
    text: str,
    assignment_type: str,
    grade: str,
    has_ai_statement: bool,
    source_type: str | None = None,
    source_note: str | None = None,
    ocr_confidence: float | None = None,
    ocr_status: str = "",
) -> None:
    result = predict_risk(text, assignment_type=assignment_type, grade=grade, has_ai_statement=has_ai_statement)
    feedback = build_feedback(text, result)
    st.session_state["last_analysis"] = {"result": result, "feedback": feedback}
    save_analysis_to_dashboard(
        text,
        result,
        feedback,
        source_type=source_type,
        source_note=source_note,
        demo_flag=False if source_type else None,
        ocr_confidence=ocr_confidence,
        ocr_status=ocr_status,
    )


def render_analysis_result_panel() -> None:
    if "last_analysis" not in st.session_state:
        with st.container(border=True):
            st.markdown("### 结果总览")
            st.info("请在左侧输入文本、识别图片文字或完成批量导入后开始分析。")
            threshold_legend()
            notice_card("分析后将显示 AIGC 风险指数、风险等级、过程透明度、阈值解释、可解释原因和学生修改建议。")
        return

    result = st.session_state["last_analysis"]["result"]
    feedback = st.session_state["last_analysis"]["feedback"]
    risk_card(float(result["ai_probability"]), result["risk_level"], result["process_transparency"], result["model_source"])

    with st.container(border=True):
        st.markdown("### 阈值区间说明")
        threshold_legend()
        st.caption("阈值用于教学展示和风险分层，不是纪律判定线。")
        st.caption(
            "由于模型基于公开 Human-ChatGPT 对比语料训练，不同文体、不同生成方式的文本可能存在识别差异。"
            "AIGC 风险指数较低不等于文本一定未使用 AI，风险指数较高也不等于可直接认定违规，"
            "教师需结合草稿、访谈和使用声明综合判断。"
        )

    reason_col, suggestion_col = st.columns(2)
    with reason_col:
        with st.container(border=True):
            st.markdown("### 可解释原因")
            mini_cards(feedback["reasons"][:5])
    with suggestion_col:
        with st.container(border=True):
            st.markdown("### 修改建议")
            mini_cards([f"教师可引导学生：{item}" for item in feedback["suggestions"][:5]])

    llm_context = (
        f"年级：{result['grade']}；作业类型：{result['assignment_type']}；"
        f"风险等级：{result['risk_level']}；AIGC 风险指数：{result['risk_index']}。"
    )
    with st.container(border=True):
        st.markdown("### 教学反馈草稿")
        st.text_area("可复制反馈", generate_teacher_feedback(llm_context), height=130, label_visibility="collapsed")

    save_status = st.session_state.get("analysis_save_status")
    if save_status == "saved":
        st.success("本次分析结果已同步到班级分析看板。")
    elif save_status == "duplicate":
        st.info("当前结果已存在，本次未重复保存。")
    st.caption("看板记录仅保存文本摘要和分析结果，不保存完整学生原文。")
    if st.button("查看班级分析看板", use_container_width=True):
        go_to_page("班级分析看板", PAGES)


def render_text_input_tab() -> None:
    st.markdown("### 文本输入")
    notice_card("演示样例仅用于展示系统功能，不代表真实学生文本。公开语料样例也不是真实学生作文。")
    demo_examples = load_demo_examples()
    demo_names = [item["demo_name"] for item in demo_examples]
    selected_demo = st.selectbox("选择匿名演示样例", demo_names)
    if st.button("加载所选样例", use_container_width=True):
        set_analysis_demo(selected_demo)
    if st.session_state.get("analysis_demo_note"):
        st.caption(st.session_state["analysis_demo_note"])

    text = st.text_area(
        "匿名化文本",
        key="analysis_text",
        height=250,
        placeholder="请粘贴匿名化后的作文、读后感、学习总结或研究性学习报告，不填写学生真实姓名、学校和班级。",
    )
    c1, c2 = st.columns(2)
    with c1:
        assignment_type = st.selectbox("作业类型", ASSIGNMENT_TYPES, key="analysis_assignment_type")
    with c2:
        grade = st.selectbox("年级", GRADES, key="analysis_grade")
    has_statement_label = st.radio("是否填写 AI 使用声明", ["已填写", "未填写"], horizontal=True, key="analysis_statement")
    if st.button("开始分析", type="primary", use_container_width=True):
        if not text.strip():
            st.error("请先输入需要分析的匿名化文本。")
        else:
            run_analysis(text, assignment_type, grade, has_statement_label == "已填写")


def render_single_image_tab() -> None:
    st.markdown("### 单张图片识别")
    warning_card("请在上传前遮挡学生姓名、班级、学号等可识别信息。OCR 识别可能存在漏字、错字或段落顺序错误，分析前请教师确认和必要修正识别文本。")
    provider = get_available_ocr_provider()
    st.caption(f"当前 OCR 状态：{provider if provider != 'none' else '未检测到可用 OCR 依赖'}")

    uploaded = st.file_uploader("上传作文图片", type=["png", "jpg", "jpeg", "webp"], key="single_ocr_upload")
    if uploaded is not None:
        st.image(uploaded, caption="图片预览：系统默认不保存原图", use_container_width=True)
        if st.button("识别图片文字", use_container_width=True):
            ocr_result = process_single_image_upload(uploaded)
            st.session_state["single_ocr_result"] = ocr_result
            st.session_state["single_ocr_text"] = str(ocr_result.get("ocr_text", ""))

    ocr_result = st.session_state.get("single_ocr_result")
    if ocr_result:
        if ocr_result.get("ocr_status") == "success":
            conf = ocr_result.get("ocr_confidence")
            conf_text = "暂无" if conf is None else f"{float(conf) * 100:.1f}%"
            st.success(f"OCR 识别完成。提供器：{ocr_result.get('ocr_provider')}；平均置信度：{conf_text}")
        else:
            st.error(f"OCR 识别未成功：{ocr_result.get('error')}")
            st.info("可运行 pip install -r requirements_ocr.txt 安装可选 OCR 依赖。")
        corrected_text = st.text_area("请确认或修正识别文本", key="single_ocr_text", height=220)
        c1, c2 = st.columns(2)
        with c1:
            assignment_type = st.selectbox("作业类型", ASSIGNMENT_TYPES, key="single_ocr_assignment_type")
        with c2:
            grade = st.selectbox("年级", GRADES, key="single_ocr_grade")
        statement = st.radio("是否填写 AI 使用声明", ["已填写", "未填写"], horizontal=True, key="single_ocr_statement")
        if st.button("使用识别文本进行分析", type="primary", use_container_width=True):
            if len(corrected_text.strip()) < 20:
                st.error("识别文本过短，请先人工核对或补充后再分析。")
            else:
                run_analysis(
                    corrected_text,
                    assignment_type,
                    grade,
                    statement == "已填写",
                    source_type="image_ocr_manual",
                    source_note="图片 OCR 识别后人工确认分析",
                    ocr_confidence=ocr_result.get("ocr_confidence"),
                    ocr_status=str(ocr_result.get("ocr_status", "")),
                )
                st.success("图片识别文本已分析并同步到班级分析看板。")
    notice_card("系统仅保存文本摘要、hash 和分析结果，不默认保存原图。AIGC 风险指数不是 AI 内容占比，不作为纪律处分依据。")


def render_batch_image_tab() -> None:
    st.markdown("### 批量图片导入")
    warning_card("请先遮挡学生姓名、班级、学号等可识别信息。批量 OCR 结果仅供教师本地核对，分析前请确认识别质量。")
    c1, c2, c3 = st.columns(3)
    with c1:
        assignment_type = st.selectbox("统一作业类型", ASSIGNMENT_TYPES, key="batch_assignment_type")
    with c2:
        grade = st.selectbox("统一年级", GRADES, key="batch_grade")
    with c3:
        statement = st.selectbox("默认使用声明状态", ["已填写", "未填写", "不确定"], key="batch_statement")
    save_to_dashboard = st.checkbox("批量分析后同步到班级分析看板", value=True)
    force_review = st.checkbox("允许强制分析需人工复核的记录", value=False)

    files = st.file_uploader("上传多张作业图片", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="batch_ocr_uploads")
    if files:
        file_rows = [
            {"序号": idx, "匿名编号": build_anonymous_id(idx), "文件名": f.name, "文件大小KB": round(len(f.getvalue()) / 1024, 1), "识别状态": "待识别", "分析状态": "待分析"}
            for idx, f in enumerate(files, start=1)
        ]
        st.dataframe(pd.DataFrame(file_rows), use_container_width=True, hide_index=True)

        if st.button("开始批量识别", use_container_width=True):
            progress = st.progress(0)
            status = st.empty()
            rows = []
            for idx, uploaded in enumerate(files, start=1):
                status.info(f"正在识别第 {idx} / {len(files)} 张：{uploaded.name}")
                ocr_row = process_single_image_upload(uploaded)
                ocr_row.update(
                    {
                        "anonymous_student_id": build_anonymous_id(idx),
                        "assignment_type": assignment_type,
                        "grade": grade,
                        "has_ai_statement": statement,
                    }
                )
                rows.append(ocr_row)
                progress.progress(idx / len(files))
            st.session_state["batch_ocr_rows"] = rows
            status.success("批量 OCR 已完成。请下载 CSV 核对，或直接批量分析。")

    rows = st.session_state.get("batch_ocr_rows", [])
    if rows:
        ocr_df = pd.DataFrame(rows)
        st.markdown("#### OCR 识别结果")
        st.dataframe(
            ocr_df[["anonymous_student_id", "file_name", "ocr_status", "ocr_confidence", "ocr_text_preview", "need_manual_review"]],
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "下载 OCR 识别结果 CSV",
            data=ocr_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="batch_ocr_results.csv",
            mime="text/csv",
            use_container_width=True,
        )
        if st.button("批量分析并同步看板", type="primary", use_container_width=True):
            outputs = batch_analyze_records(rows, save_to_dashboard=save_to_dashboard, force_review_records=force_review)
            st.session_state["batch_analysis_outputs"] = outputs
            st.success("批量分析完成，符合条件的记录已同步到班级分析看板。")

    corrected_csv = st.file_uploader("上传修正后的 OCR CSV", type=["csv"], key="batch_corrected_csv")
    if corrected_csv is not None:
        corrected_df = pd.read_csv(corrected_csv)
        ok, errors = validate_batch_csv(corrected_df)
        if not ok:
            st.error("修正 CSV 字段不完整：" + "；".join(errors))
        else:
            st.success("修正 CSV 校验通过。")
            if st.button("分析修正后的 CSV 并同步看板", use_container_width=True):
                corrected_records = corrected_df.to_dict(orient="records")
                outputs = batch_analyze_records(corrected_records, save_to_dashboard=save_to_dashboard, force_review_records=True)
                st.session_state["batch_analysis_outputs"] = outputs
                st.success("修正 CSV 批量分析完成。")

    outputs = st.session_state.get("batch_analysis_outputs", [])
    if outputs:
        out_df = pd.DataFrame(outputs)
        st.markdown("#### 批量分析结果")
        display_cols = [
            col
            for col in ["anonymous_student_id", "assignment_type", "grade", "aigc_risk_index", "risk_level", "process_transparency", "reasons_summary", "saved_to_dashboard", "skip_reason"]
            if col in out_df.columns
        ]
        st.dataframe(out_df[display_cols], use_container_width=True, hide_index=True)
        st.download_button(
            "下载批量分析结果 CSV",
            data=out_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="batch_analysis_results.csv",
            mime="text/csv",
            use_container_width=True,
        )
    notice_card("批量记录默认不保存原图；看板只保存文本摘要、hash 和分析结果。")


def page_text_analysis() -> None:
    render_header(
        "作业文本分析",
        "支持文本输入、单张图片识别和批量图片导入，统一输出 AIGC 风险提示并同步班级分析看板。",
        "📝",
    )
    notice_card(RISK_INDEX_NOTICE)
    notice_card("支持上传作文、读后感、学习总结等图片，系统先进行 OCR 文字识别，教师确认识别结果后，再进行 AIGC 风险提示。")

    if "analysis_text" not in st.session_state:
        st.session_state["analysis_text"] = ""
    if "analysis_assignment_type" not in st.session_state:
        st.session_state["analysis_assignment_type"] = ASSIGNMENT_TYPES[0]

    left, right = st.columns([0.48, 0.52], gap="large")
    with left:
        with st.container(border=True):
            st.markdown(
                """
<div class="input-mode-intro">
  <h3>选择作业导入方式</h3>
  <p>可直接粘贴匿名文本，也可上传单张或多张作业图片，经 OCR 识别和教师确认后进入同一套分析流程。</p>
</div>
""",
                unsafe_allow_html=True,
            )
            tab_text, tab_single, tab_batch = st.tabs(["文本输入", "单张图片识别", "批量图片导入"])
            with tab_text:
                render_text_input_tab()
            with tab_single:
                render_single_image_tab()
            with tab_batch:
                render_batch_image_tab()

    with right:
        render_analysis_result_panel()


def build_statement(
    used_ai: str,
    steps: list[str],
    tool_name: str,
    prompt_text: str,
    revision: str,
    own_thinking: str,
    understands_error: bool,
) -> str:
    step_text = "、".join(steps) if steps else "未填写"
    error_text = "我理解 AI 可能产生错误，需要核实重要信息。" if understands_error else "我还需要进一步学习 AI 输出核验方法。"
    return f"""AI 辅助生成，仅供教师参考。

# 学生 AI 使用声明

我是否使用了生成式 AI：{used_ai}

我在哪些环节使用了 AI：{step_text}

我使用的工具名称：{tool_name or "未填写"}

我使用过的提示词：
{prompt_text or "未填写"}

哪些内容由我自己完成：
{own_thinking or "未填写"}

哪些内容经过我修改：
{revision or "未填写"}

我是否理解 AI 可能产生错误：
{error_text}

我的承诺：
我承诺不直接复制 AI 结果作为个人原创成果。若使用生成式 AI，我会说明使用环节、保留修改过程，并用自己的语言重写关键段落。
"""


def page_ai_statement() -> None:
    render_header("使用声明管理", "引导学生透明说明 AI 使用过程，而不是简单禁止或惩罚。", "📋")
    notice_card("AI 辅助生成，仅供教师参考。学生声明用于过程反思和教学沟通，不作为单一评价依据。")

    left, right = st.columns([0.48, 0.52], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("### 表单式声明生成器")
            used_ai = st.radio("是否使用生成式 AI", ["使用过", "未使用", "不确定，需要说明"], horizontal=True)
            st.markdown("**使用环节**")
            steps = []
            step_options = ["选题", "提纲", "查资料", "润色", "翻译", "改写", "生成初稿", "其他"]
            step_cols = st.columns(2)
            for idx, step in enumerate(step_options):
                if step_cols[idx % 2].checkbox(step, key=f"statement_step_{step}"):
                    steps.append(step)
            tool_name = st.text_input("使用的工具名称", placeholder="例如：通义千问、文心一言、DeepSeek 等，可留空")
            prompt_text = st.text_area("使用过的提示词", height=110)
            revision = st.text_area("自己修改了哪些内容", height=100)
            own_thinking = st.text_area("哪些部分体现自己的思考", height=100)
            understands_error = st.checkbox("我理解 AI 可能产生错误，需要核实重要信息", value=True)
            if st.button("一键生成声明", type="primary", use_container_width=True):
                st.session_state["statement_output"] = build_statement(
                    used_ai, steps, tool_name, prompt_text, revision, own_thinking, understands_error
                )
            if st.button("使用空白模板", use_container_width=True):
                st.session_state["statement_output"] = generate_ai_statement_template()

    with right:
        with st.container(border=True):
            st.markdown("### 生成结果")
            statement = st.session_state.get("statement_output", generate_ai_statement_template())
            st.text_area("学生 AI 使用声明", statement, height=340)
            if st.button("一键复制模板", use_container_width=True):
                st.toast("声明已生成在文本框中，可直接选中复制。")

        with st.container(border=True):
            st.markdown("### 反思问题")
            mini_cards(
                [
                    "AI 给出的内容中哪些地方需要核实？",
                    "你对 AI 输出做了哪些修改？",
                    "哪一部分最能体现你自己的思考？",
                    "下次你会如何更规范地使用 AI？",
                ]
            )
            st.caption("AI 辅助生成，仅供教师参考。")


def page_dashboard() -> None:
    render_dashboard_page(PAGES)


def build_meeting_sections(topic: str, stage: str, duration: str, focus: list[str], stats_summary: str) -> dict[str, str]:
    focus_text = "、".join(focus) if focus else "AI 使用边界"
    return {
        "教学目标": f"面向{stage}学生，围绕“{topic}”理解生成式 AI 的合理用途、风险边界和透明声明方法。",
        "导入问题": "如果 AI 帮你写出一段很流畅的文字，这段文字能不能直接作为自己的作业提交？为什么？",
        "正反案例": "正向案例：用 AI 辅助列提纲、核对资料后再用自己的语言改写。反向案例：直接复制 AI 输出，不说明来源，也不保留修改过程。",
        "小组讨论": f"围绕{focus_text}讨论：哪些环节可以合理使用 AI？哪些内容必须体现自己的思考？如何核实 AI 输出？",
        "学生承诺": "我可以把 AI 作为学习助手，但不直接复制 AI 结果作为个人原创成果；如使用 AI，我会说明过程并保留修改记录。",
        "教师总结": "规范使用 AI 不是拒绝技术，而是学会透明、负责地使用技术。风险提示只帮助我们发现需要进一步沟通的地方。",
        "延伸任务": f"课后完成一份 AI 使用声明，并任选一段 AI 输出进行核实、修改和反思。建议课时：{duration}。班级参考数据：{stats_summary}",
    }


def page_class_meeting() -> None:
    render_header("素养教育资源", "根据班级 AIGC 风险分布和使用声明情况，生成 AI 素养教育班会建议。", "🎓")
    notice_card("本内容由 AI 辅助生成，仅供教师参考，使用前需由教师审核。")

    df = load_submissions()
    stats = dashboard_stats(df)
    stats_summary = (
        f"总提交数量 {stats['total']}；风险分布 {stats['risk_distribution']}；"
        f"AI 使用声明比例 {float(stats['statement_ratio']) * 100:.1f}%。"
    )

    left, right = st.columns([0.38, 0.62], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("### 班会参数")
            topic = st.selectbox(
                "班会主题",
                [
                    "我可以用 AI 写作业吗？——中学生生成式 AI 规范使用课",
                    "AI 输出为什么需要核实？",
                    "从复制答案到表达自己：AI 时代的原创意识",
                ],
            )
            stage = st.radio("学段", ["初中", "高中"], horizontal=True)
            duration = st.radio("课时", ["20 分钟", "40 分钟"], horizontal=True)
            focus = st.multiselect(
                "班级关注点",
                ["作业诚信", "AI 使用边界", "提示词素养", "信息核验", "原创表达"],
                default=["AI 使用边界", "信息核验", "原创表达"],
            )
            if st.button("生成班会课方案", type="primary", use_container_width=True):
                st.session_state["meeting_sections"] = build_meeting_sections(topic, stage, duration, focus, stats_summary)
                st.session_state["meeting_plan_full"] = generate_class_meeting_plan(stats_summary)

    sections = st.session_state.get(
        "meeting_sections",
        build_meeting_sections(
            "我可以用 AI 写作业吗？——中学生生成式 AI 规范使用课",
            "初中",
            "40 分钟",
            ["AI 使用边界", "信息核验", "原创表达"],
            stats_summary,
        ),
    )
    with right:
        cols = st.columns(2)
        for idx, (title, body) in enumerate(sections.items()):
            with cols[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"### {title}")
                    st.write(body)
        with st.expander("查看完整生成文本"):
            st.markdown(st.session_state.get("meeting_plan_full", generate_class_meeting_plan(stats_summary)))


def page_privacy() -> None:
    render_header("隐私与使用边界", "以红线清单明确系统边界，增强参赛演示和真实试用的可信度。", "🛡️")
    privacy_svg = svg_image("assets/privacy_guard.svg", alt="privacy guard")
    left, right = st.columns([0.62, 0.38], gap="large")
    with left:
        redline_cards(
            [
                ("🚫", "不上传学生真实姓名、身份证、手机号等可识别信息"),
                ("📷", "不上传学生正脸照片"),
                ("⚖️", "不把风险指数作为纪律处分依据"),
                ("📝", "不公开展示学生原文"),
                ("✅", "AI 生成内容必须标注并由教师审核"),
            ]
        )
    with right:
        st.markdown(f'<div class="svg-wrap">{privacy_svg}</div>', unsafe_allow_html=True)

    section_title("合规使用流程", "匿名化文本进入系统后，教师保留最终教育判断权。", "流程")
    render_flow_steps(
        [
            ("🔒", "匿名化文本"),
            ("📊", "系统分析"),
            ("👩‍🏫", "教师复核"),
            ("🧠", "学生反思"),
            ("🎓", "班级教育"),
        ]
    )
    warning_card("系统输出的是教学辅助信息，不是司法、纪律或人格评价结论。所有结果仅供教师参考。")


PAGE_RENDERERS = {
    "首页总览": page_home,
    "作业文本分析": page_text_analysis,
    "使用声明管理": page_ai_statement,
    "班级分析看板": page_dashboard,
    "素养教育资源": page_class_meeting,
    "隐私与使用边界": page_privacy,
}


def main() -> None:
    current_page = render_top_nav(PAGES)
    PAGE_RENDERERS[current_page]()
    render_footer_note()


if __name__ == "__main__":
    main()
