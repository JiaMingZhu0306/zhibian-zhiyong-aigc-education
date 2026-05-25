"""Streamlit 参赛级 UI 组件。

本模块只负责视觉、导航和可复用展示组件，不参与模型概率计算。
"""

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def inject_global_css() -> None:
    """注入全局 CSS，统一页面为智慧教育信息系统风格。"""
    st.markdown(
        """
<style>
:root {
  --primary: #2563EB;
  --secondary: #7C3AED;
  --accent: #06B6D4;
  --success: #16A34A;
  --warning: #F59E0B;
  --danger: #EF4444;
  --bg: #F6F8FC;
  --card: #FFFFFF;
  --text: #1E293B;
  --muted: #64748B;
  --line: #E2E8F0;
  --shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
}

#MainMenu, footer, header { visibility: hidden; }
section[data-testid="stSidebar"] { display: none; }

.stApp {
  background:
    radial-gradient(circle at 8% 4%, rgba(37, 99, 235, 0.10), transparent 26%),
    radial-gradient(circle at 86% 8%, rgba(124, 58, 237, 0.10), transparent 28%),
    linear-gradient(180deg, #F8FAFC 0%, #F6F8FC 52%, #EEF5FF 100%);
  color: var(--text);
}

.block-container {
  max-width: 1360px;
  padding-top: 1.2rem;
  padding-bottom: 2.4rem;
}

h1, h2, h3, h4, p, li, label, span {
  letter-spacing: 0;
}

h1, h2, h3, h4 {
  color: var(--text);
}

.stApp,
.stMarkdown,
.stMarkdown p,
.stMarkdown li,
div[data-testid="stWidgetLabel"],
div[data-testid="stWidgetLabel"] p,
div[data-testid="stRadio"] p,
div[data-testid="stRadio"] span,
div[data-testid="stCheckbox"] p,
div[data-testid="stCheckbox"] span,
div[data-testid="stSelectbox"] p,
div[data-testid="stTextInput"] p,
div[data-testid="stTextArea"] p,
label,
label p,
label span {
  color: var(--text) !important;
}

.stTextArea textarea,
.stTextInput input {
  color: var(--text) !important;
  caret-color: var(--primary) !important;
}

.stTextArea textarea::placeholder,
.stTextInput input::placeholder {
  color: #94A3B8 !important;
  opacity: 1 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
  border: 1px solid rgba(226, 232, 240, 0.92) !important;
  border-radius: 18px !important;
  box-shadow: var(--shadow);
  background: rgba(255, 255, 255, 0.96);
}

div[data-testid="stMetric"] {
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 18px;
  padding: 16px 18px;
  box-shadow: var(--shadow);
}

div[data-testid="stMetricValue"] {
  color: var(--text);
  font-weight: 850;
}

.stTextArea textarea,
.stTextInput input,
div[data-baseweb="select"] > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
  border-radius: 14px !important;
  border: 1px solid var(--line) !important;
  box-shadow: none !important;
  background: #fff !important;
}

div[data-baseweb="select"] {
  background-color: #FFFFFF !important;
  color: #111827 !important;
}

div[data-baseweb="select"] > div {
  background-color: #FFFFFF !important;
  border: 1px solid #D1D5DB !important;
  border-radius: 12px !important;
  color: #111827 !important;
}

div[data-baseweb="select"] *,
div[data-baseweb="select"] span,
div[data-baseweb="select"] div,
div[data-baseweb="select"] input {
  color: #111827 !important;
  -webkit-text-fill-color: #111827 !important;
}

div[data-baseweb="select"] svg {
  fill: #4B5563 !important;
  color: #4B5563 !important;
}

ul[role="listbox"],
div[role="listbox"],
div[data-baseweb="popover"] {
  background-color: #FFFFFF !important;
  color: #111827 !important;
}

ul[role="listbox"] li,
div[role="option"] {
  color: #111827 !important;
  -webkit-text-fill-color: #111827 !important;
  background-color: #FFFFFF !important;
}

div[role="option"]:hover,
li[role="option"]:hover {
  background-color: #EFF6FF !important;
  color: #111827 !important;
  -webkit-text-fill-color: #111827 !important;
}

div[data-testid="stSelectbox"] label,
div[data-testid="stSelectbox"] label p,
div[data-testid="stWidgetLabel"] label,
div[data-testid="stWidgetLabel"] p {
  color: #1F2937 !important;
  -webkit-text-fill-color: #1F2937 !important;
  font-weight: 600 !important;
}

.stTextArea textarea:focus,
.stTextInput input:focus,
div[data-baseweb="select"] > div:focus-within {
  border-color: rgba(37, 99, 235, 0.72) !important;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12) !important;
}

div[data-baseweb="tab-list"] {
  gap: 8px !important;
  border-bottom: 1px solid #E5E7EB !important;
  background: transparent !important;
}

button[data-baseweb="tab"] {
  color: #1F2937 !important;
  -webkit-text-fill-color: #1F2937 !important;
  background-color: #FFFFFF !important;
  font-weight: 700 !important;
  font-size: 16px !important;
  padding: 12px 20px !important;
  border-radius: 10px 10px 0 0 !important;
  border: 1px solid #E5E7EB !important;
  border-bottom: none !important;
  opacity: 1 !important;
  box-shadow: none !important;
}

button[data-baseweb="tab"] p,
button[data-baseweb="tab"] span,
button[data-baseweb="tab"] div {
  color: #1F2937 !important;
  -webkit-text-fill-color: #1F2937 !important;
  opacity: 1 !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
  color: #1D4ED8 !important;
  -webkit-text-fill-color: #1D4ED8 !important;
  background-color: #EFF6FF !important;
  border-color: #BFDBFE !important;
  border-bottom: 3px solid #2563EB !important;
}

button[data-baseweb="tab"][aria-selected="true"] p,
button[data-baseweb="tab"][aria-selected="true"] span,
button[data-baseweb="tab"][aria-selected="true"] div {
  color: #1D4ED8 !important;
  -webkit-text-fill-color: #1D4ED8 !important;
  opacity: 1 !important;
}

button[data-baseweb="tab"]:hover {
  background-color: #F3F4F6 !important;
  color: #1D4ED8 !important;
  -webkit-text-fill-color: #1D4ED8 !important;
}

button[data-baseweb="tab"]:hover p,
button[data-baseweb="tab"]:hover span,
button[data-baseweb="tab"]:hover div {
  color: #1D4ED8 !important;
  -webkit-text-fill-color: #1D4ED8 !important;
}

button[data-baseweb="tab"]:focus,
button[data-baseweb="tab"]:focus-visible {
  outline: none !important;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14) !important;
}

div[data-baseweb="tab-border"] {
  background-color: #2563EB !important;
}

.input-mode-intro {
  margin: 0 0 14px;
  padding: 14px 16px;
  background: #F8FAFC;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
}

.input-mode-intro h3 {
  margin: 0 0 6px;
  color: #111827;
  font-size: 17px;
  font-weight: 850;
}

.input-mode-intro p {
  margin: 0;
  color: #4B5563;
  line-height: 1.7;
}

.stButton > button,
.stDownloadButton > button {
  border: none !important;
  border-radius: 999px !important;
  background: linear-gradient(135deg, var(--primary), var(--secondary)) !important;
  color: #fff !important;
  font-weight: 760 !important;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.20);
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 28px rgba(37, 99, 235, 0.26);
}

.stButton > button:focus,
.stDownloadButton > button:focus,
label:focus,
textarea:focus,
input:focus {
  outline: none !important;
}

div[data-testid="stExpander"] {
  background: #FFFFFF !important;
  border: 1px solid #E5E7EB !important;
  border-radius: 14px !important;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05) !important;
  overflow: hidden !important;
}

div[data-testid="stExpander"] details {
  background: #FFFFFF !important;
  color: #1E293B !important;
}

div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] details > summary {
  background: #FFFFFF !important;
  color: #1E293B !important;
  border: none !important;
  border-color: #E5E7EB !important;
  border-bottom: 1px solid #E5E7EB !important;
  box-shadow: none !important;
  outline: none !important;
  min-height: 48px !important;
  padding: 12px 16px !important;
}

div[data-testid="stExpander"] summary:hover,
div[data-testid="stExpander"] details > summary:hover {
  background: #F8FAFC !important;
}

div[data-testid="stExpander"] summary *,
div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span {
  color: #1E293B !important;
  -webkit-text-fill-color: #1E293B !important;
  font-weight: 700 !important;
}

div[data-testid="stExpander"] summary svg {
  color: #2563EB !important;
  fill: #2563EB !important;
}

div[data-testid="stExpander"] [data-testid="stMarkdownContainer"],
div[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
div[data-testid="stExpander"] [data-testid="stMarkdownContainer"] li,
div[data-testid="stExpander"] [data-testid="stMarkdownContainer"] h1,
div[data-testid="stExpander"] [data-testid="stMarkdownContainer"] h2,
div[data-testid="stExpander"] [data-testid="stMarkdownContainer"] h3 {
  color: #1E293B !important;
  background: transparent !important;
}

.top-menu {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.84);
  border-radius: 14px;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.045);
  padding: 0 16px;
  margin-bottom: 18px;
}

.top-menu-item {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 48px;
  padding: 0 14px;
  color: #1F2937 !important;
  text-decoration: none !important;
  border-bottom: 3px solid transparent;
  font-weight: 720;
  font-size: 15px;
  white-space: nowrap;
  transition: color 0.14s ease, background 0.14s ease, border-color 0.14s ease;
}

.top-menu-item:hover {
  color: #1D4ED8 !important;
  background: #F8FAFC;
  border-bottom-color: #BFDBFE;
}

.top-menu-item.active {
  color: #1D4ED8 !important;
  background: #EFF6FF;
  border-bottom-color: #2563EB;
  font-weight: 860;
}

.top-menu-icon {
  font-size: 16px;
  line-height: 1;
}

div[role="radiogroup"] {
  gap: 10px;
}

div[data-testid="stRadio"] label {
  border-radius: 10px;
}

.app-shell {
  margin-bottom: 18px;
}

.hero-grid {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 28px;
  align-items: center;
  padding: 34px;
  border-radius: 26px;
  color: #fff;
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.96), rgba(124, 58, 237, 0.92)),
    radial-gradient(circle at 82% 24%, rgba(6, 182, 212, 0.45), transparent 34%);
  box-shadow: 0 22px 54px rgba(37, 99, 235, 0.26);
  overflow: hidden;
}

.hero-kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.24);
  font-size: 14px;
  margin-bottom: 14px;
}

.hero-grid h1 {
  color: #fff;
  font-size: 54px;
  line-height: 1.05;
  margin: 0 0 12px;
  font-weight: 900;
}

.hero-grid h2 {
  color: rgba(255, 255, 255, 0.96);
  font-size: 24px;
  margin: 0 0 16px;
  font-weight: 760;
}

.hero-grid p {
  color: rgba(255, 255, 255, 0.90);
  font-size: 17px;
  line-height: 1.8;
  margin: 0;
}

.hero-action-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 22px;
}

.fake-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 999px;
  font-weight: 800;
  background: #fff;
  color: var(--primary);
  text-decoration: none !important;
  border: 1px solid rgba(255,255,255,0.42);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.12);
  transition: transform 0.14s ease, box-shadow 0.14s ease, background 0.14s ease;
}

.fake-button.secondary {
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.28);
}

.fake-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 26px rgba(15, 23, 42, 0.16);
  background: #F8FAFC;
  color: var(--primary);
}

.fake-button.secondary:hover {
  background: rgba(255, 255, 255, 0.24);
  color: #fff;
}

.fake-button:focus {
  outline: none !important;
  box-shadow: 0 0 0 4px rgba(255,255,255,0.22);
}

.svg-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
}

.svg-wrap img {
  width: 100%;
  max-height: 310px;
}

.section-title {
  margin: 28px 0 12px;
}

.section-title .eyebrow {
  color: var(--primary);
  font-weight: 820;
  font-size: 13px;
  margin-bottom: 4px;
}

.section-title h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 860;
}

.section-title p {
  margin: 6px 0 0;
  color: var(--muted);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin: 14px 0 20px;
}

.metric-card,
.info-card,
.flow-step,
.risk-card,
.notice-card,
.redline-card {
  background: var(--card);
  border: 1px solid rgba(226, 232, 240, 0.86);
  border-radius: 18px;
  box-shadow: var(--shadow);
}

.metric-card {
  padding: 18px;
  min-height: 126px;
}

.metric-icon {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(37,99,235,0.12), rgba(124,58,237,0.12));
  font-size: 22px;
  margin-bottom: 12px;
}

.metric-label {
  color: var(--muted);
  font-size: 13px;
  font-weight: 720;
  margin-bottom: 5px;
}

.metric-value {
  color: var(--text);
  font-size: 28px;
  font-weight: 900;
  line-height: 1.1;
}

.metric-subtitle {
  color: var(--muted);
  font-size: 12px;
  margin-top: 8px;
  line-height: 1.5;
}

.info-card {
  padding: 18px;
  height: 100%;
}

.info-card h3 {
  font-size: 17px;
  margin: 0 0 8px;
}

.info-card p {
  color: var(--muted);
  margin: 0;
  line-height: 1.75;
}

.flow-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin: 16px 0 20px;
}

.flow-step {
  padding: 18px 14px;
  text-align: center;
  position: relative;
}

.flow-step .icon {
  width: 42px;
  height: 42px;
  margin: 0 auto 10px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(37,99,235,0.13), rgba(6,182,212,0.15));
  font-size: 22px;
}

.flow-step .title {
  font-weight: 820;
  color: var(--text);
}

.notice-card {
  padding: 16px 18px;
  margin: 16px 0;
  border-left: 5px solid var(--accent);
  background: linear-gradient(135deg, #ECFEFF, #FFFFFF);
  color: #155E75;
  line-height: 1.75;
}

.warning-card {
  border-left-color: var(--warning);
  background: linear-gradient(135deg, #FFFBEB, #FFFFFF);
  color: #92400E;
}

.risk-card {
  padding: 22px;
  overflow: hidden;
}

.risk-topline {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.risk-index {
  font-size: 58px;
  font-weight: 950;
  line-height: 1;
  background: linear-gradient(135deg, var(--primary), var(--secondary));
  -webkit-background-clip: text;
  color: transparent;
}

.risk-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 8px 13px;
  font-weight: 850;
  white-space: nowrap;
}

.risk-low { background: #DCFCE7; color: #166534; }
.risk-medium { background: #FEF3C7; color: #92400E; }
.risk-high { background: #FFEDD5; color: #C2410C; }
.risk-very-high { background: #FEE2E2; color: #B91C1C; }

.risk-bar {
  width: 100%;
  height: 13px;
  border-radius: 999px;
  background: linear-gradient(90deg, #22C55E 0%, #22C55E 35%, #F59E0B 35%, #F59E0B 75%, #FB7185 75%, #FB7185 90%, #EF4444 90%, #EF4444 100%);
  margin: 16px 0 8px;
  overflow: hidden;
  position: relative;
}

.risk-marker {
  position: absolute;
  top: -4px;
  width: 4px;
  height: 21px;
  border-radius: 999px;
  background: #0F172A;
  box-shadow: 0 0 0 4px rgba(255,255,255,0.75);
}

.threshold-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.threshold-item {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px;
  background: #fff;
}

.threshold-item strong {
  display: block;
  margin-bottom: 4px;
}

.mini-list {
  display: grid;
  gap: 10px;
}

.mini-card {
  padding: 12px 14px;
  border-radius: 14px;
  background: #F8FAFC;
  border: 1px solid var(--line);
  color: var(--text);
  line-height: 1.65;
}

.redline-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.redline-card {
  padding: 16px;
  background: linear-gradient(135deg, #FFF7ED, #FFFFFF);
  border-color: #FED7AA;
}

.redline-card .icon {
  color: var(--danger);
  font-size: 24px;
  margin-bottom: 10px;
}

.footer-note {
  color: var(--muted);
  font-size: 13px;
  text-align: center;
  margin-top: 28px;
  padding: 16px;
}

.dashboard-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin: 16px 0 18px;
}

.kpi-card {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
  min-height: 126px;
}

.kpi-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.kpi-title {
  color: #6B7280;
  font-size: 13px;
  font-weight: 760;
}

.kpi-mark {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: #EFF6FF;
  color: #2563EB;
  font-weight: 860;
  font-size: 13px;
}

.kpi-value {
  color: #111827;
  font-size: 32px;
  line-height: 1.1;
  font-weight: 900;
  margin-top: 14px;
}

.kpi-desc {
  color: #6B7280;
  font-size: 13px;
  margin-top: 8px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin: 18px 0;
}

.dashboard-card {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}

.dashboard-card h3 {
  margin: 0 0 6px;
  color: #111827;
  font-size: 18px;
}

.dashboard-card p {
  margin: 0 0 10px;
  color: #6B7280;
  line-height: 1.65;
}

.observation-card {
  background: linear-gradient(135deg, #FFFFFF, #F8FAFC);
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
  margin: 16px 0;
}

.observation-card h3 {
  margin: 0 0 8px;
  color: #111827;
}

.observation-card p {
  margin: 0;
  color: #374151;
  line-height: 1.8;
}

.issue-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  background: #F8FAFC;
  border: 1px solid #E5E7EB;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  color: #1F2937;
}

.issue-name {
  color: #1F2937;
  line-height: 1.55;
}

.issue-count {
  color: #2563EB;
  font-weight: 850;
  white-space: nowrap;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin: 18px 0;
}

.action-card {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
}

.action-card h3 {
  margin: 0 0 8px;
  font-size: 17px;
  color: #111827;
}

.action-card p {
  margin: 0;
  color: #4B5563;
  line-height: 1.7;
}

.empty-dashboard {
  background: #FFFFFF;
  border: 1px dashed #CBD5E1;
  border-radius: 18px;
  padding: 30px;
  text-align: center;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
}

.empty-dashboard h3 {
  margin: 0 0 8px;
  color: #111827;
}

.empty-dashboard p {
  color: #4B5563;
  line-height: 1.8;
}

@media (max-width: 1000px) {
  .hero-grid { grid-template-columns: 1fr; }
  .card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .flow-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .redline-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .dashboard-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .dashboard-grid { grid-template-columns: 1fr; }
  .action-grid { grid-template-columns: 1fr; }
  .hero-grid h1 { font-size: 40px; }
}
</style>
""",
        unsafe_allow_html=True,
    )


def apply_global_style() -> None:
    """兼容旧 app.py 的函数名。"""
    inject_global_css()


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def svg_image(path: str | Path, width: str = "100%", alt: str = "") -> str:
    """返回本地 SVG 的 HTML img 标签。"""
    svg_path = Path(path)
    if not svg_path.is_absolute():
        svg_path = PROJECT_ROOT / svg_path
    if not svg_path.exists():
        return ""
    raw = svg_path.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    return f'<img src="data:image/svg+xml;base64,{encoded}" width="{_escape(width)}" alt="{_escape(alt)}" />'


def render_top_nav(pages: list[tuple[str, str]]) -> str:
    """渲染顶部管理系统菜单，返回页面名称。"""
    page_aliases = {
        "home": "首页总览",
        "analysis": "作业文本分析",
        "statement": "使用声明管理",
        "dashboard": "班级分析看板",
        "meeting": "素养教育资源",
        "privacy": "隐私与使用边界",
        "文本风险分析": "作业文本分析",
        "AI 使用声明": "使用声明管理",
        "AI 素养班会": "素养教育资源",
        "隐私与边界": "隐私与使用边界",
    }
    pending_page = st.session_state.pop("nav_pending_page", None)
    query_page = st.query_params.get("page", "")
    if isinstance(query_page, list):
        query_page = query_page[0] if query_page else ""
    query_page = page_aliases.get(query_page, query_page)
    pending_page = page_aliases.get(pending_page, pending_page)
    valid_names = [name for name, _ in pages]
    current_page = page_aliases.get(st.session_state.get("current_page", ""), st.session_state.get("current_page", ""))
    active_page = page_aliases.get(st.session_state.get("active_page", ""), st.session_state.get("active_page", ""))
    page_name = pending_page or query_page or current_page or active_page or pages[0][0]
    if page_name not in valid_names:
        page_name = pages[0][0]

    links = []
    for name, icon in pages:
        active = " active" if name == page_name else ""
        links.append(
            f'<a class="top-menu-item{active}" href="?page={quote(name)}">'
            f'<span class="top-menu-icon">{_escape(icon)}</span><span>{_escape(name)}</span></a>'
        )
    st.markdown(f'<nav class="top-menu app-shell">{"".join(links)}</nav>', unsafe_allow_html=True)
    st.session_state["active_page"] = page_name
    st.session_state["current_page"] = page_name
    return page_name


def go_to_page(page_name: str, pages: list[tuple[str, str]]) -> None:
    """设置导航目标并触发刷新。"""
    if any(name == page_name for name, _ in pages):
        st.session_state["active_page"] = page_name
        st.session_state["current_page"] = page_name
        st.session_state["nav_pending_page"] = page_name
        st.query_params["page"] = page_name
        st.rerun()


def render_header(title: str, subtitle: str = "", icon: str = "") -> None:
    safe_title = _escape(title)
    safe_subtitle = _escape(subtitle)
    safe_icon = _escape(icon)
    st.markdown(
        f"""
<div class="section-title">
  <div class="eyebrow">{safe_icon} 智慧教育信息系统</div>
  <h2>{safe_title}</h2>
  <p>{safe_subtitle}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def section_title(title: str, subtitle: str = "", eyebrow: str = "功能模块") -> None:
    st.markdown(
        f"""
<div class="section-title">
  <div class="eyebrow">{_escape(eyebrow)}</div>
  <h2>{_escape(title)}</h2>
  <p>{_escape(subtitle)}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def metric_card(title: str, value: str, subtitle: str = "", icon: str = "📌") -> str:
    return f"""
<div class="metric-card">
  <div class="metric-icon">{_escape(icon)}</div>
  <div class="metric-label">{_escape(title)}</div>
  <div class="metric-value">{_escape(value)}</div>
  <div class="metric-subtitle">{_escape(subtitle)}</div>
</div>
"""


def metric_cards(cards: Iterable[tuple[str, str, str, str]]) -> None:
    html_cards = "".join(metric_card(title, value, subtitle, icon) for title, value, subtitle, icon in cards)
    st.markdown(f'<div class="card-grid">{html_cards}</div>', unsafe_allow_html=True)


def info_card(title: str, desc: str, icon: str = "✨") -> str:
    return f"""
<div class="info-card">
  <div class="metric-icon">{_escape(icon)}</div>
  <h3>{_escape(title)}</h3>
  <p>{_escape(desc)}</p>
</div>
"""


def info_card_grid(cards: Iterable[tuple[str, str, str]], columns: int = 4) -> None:
    html_cards = "".join(info_card(title, desc, icon) for title, desc, icon in cards)
    st.markdown(f'<div class="card-grid" style="grid-template-columns: repeat({columns}, minmax(0, 1fr));">{html_cards}</div>', unsafe_allow_html=True)


def notice_card(text: str, kind: str = "info") -> None:
    extra = " warning-card" if kind == "warning" else ""
    st.markdown(f'<div class="notice-card{extra}">{_escape(text)}</div>', unsafe_allow_html=True)


def warning_card(text: str) -> None:
    notice_card(text, kind="warning")


def safety_notice() -> None:
    notice_card(
        "本系统不是作弊判定工具。AIGC 风险指数仅表示模型参考概率，不代表 AI 内容占比，不作为纪律处分依据。",
        kind="warning",
    )


def render_flow_steps(steps: list[tuple[str, str]]) -> None:
    items = []
    for icon, title in steps:
        items.append(
            f"""
<div class="flow-step">
  <div class="icon">{_escape(icon)}</div>
  <div class="title">{_escape(title)}</div>
</div>
"""
        )
    st.markdown(f'<div class="flow-row">{"".join(items)}</div>', unsafe_allow_html=True)


def risk_badge_class(level: str) -> str:
    if "低" in level:
        return "risk-low"
    if "中" in level:
        return "risk-medium"
    if "高置信" in level or "高参考" in level:
        return "risk-very-high"
    if "高" in level:
        return "risk-high"
    return "risk-medium"


def risk_badge(level: str) -> str:
    return f'<span class="risk-badge {risk_badge_class(level)}">{_escape(level)}</span>'


def risk_card(probability: float, risk_level: str, process_transparency: str, model_source: str = "") -> None:
    pct = max(0, min(float(probability), 1.0)) * 100
    st.markdown(
        f"""
<div class="risk-card">
  <div class="risk-topline">
    <div>
      <div class="metric-label">AIGC 风险指数</div>
      <div class="risk-index">{pct:.0f}%</div>
    </div>
    <div>{risk_badge(risk_level)}</div>
  </div>
  <div class="risk-bar"><div class="risk-marker" style="left: calc({pct:.2f}% - 2px);"></div></div>
  <div class="metric-subtitle">模型参考概率：{pct:.2f}%</div>
  <div class="metric-subtitle">过程透明度：{_escape(process_transparency)}</div>
  <div class="metric-subtitle">模型来源：{_escape(model_source)}</div>
  <div class="notice-card warning-card" style="margin-top:14px;">
    AIGC 风险指数不是 AI 内容占比，不作为纪律处分依据。教师需结合草稿、访谈和 AI 使用声明综合判断。
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def threshold_legend() -> None:
    st.markdown(
        """
<div class="threshold-grid">
  <div class="threshold-item"><strong style="color:#166534;">0-35%</strong>低风险</div>
  <div class="threshold-item"><strong style="color:#92400E;">35-75%</strong>中风险</div>
  <div class="threshold-item"><strong style="color:#C2410C;">75-90%</strong>高风险</div>
  <div class="threshold-item"><strong style="color:#B91C1C;">90%+</strong>高置信高风险</div>
</div>
""",
        unsafe_allow_html=True,
    )


def mini_cards(items: Iterable[str]) -> None:
    cards = "".join(f'<div class="mini-card">{_escape(item)}</div>' for item in items)
    st.markdown(f'<div class="mini-list">{cards}</div>', unsafe_allow_html=True)


def redline_cards(items: Iterable[tuple[str, str]]) -> None:
    cards = []
    for icon, text in items:
        cards.append(
            f"""
<div class="redline-card">
  <div class="icon">{_escape(icon)}</div>
  <div>{_escape(text)}</div>
</div>
"""
        )
    st.markdown(f'<div class="redline-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_footer_note() -> None:
    st.markdown(
        '<div class="footer-note">本系统为教学辅助工具，所有结果仅供教师参考。</div>',
        unsafe_allow_html=True,
    )
