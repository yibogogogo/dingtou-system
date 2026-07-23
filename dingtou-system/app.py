"""
Streamlit主应用 - v2.1 重新设计版
包含：实时评分、回测可视化、参数调优
"""
import sys
import os
import re

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from data.cache import DataCache
from engine.indicators import TechnicalIndicators
from engine.scoring import ScoringEngine
from engine.allocation import AllocationEngine
from engine.backtest import BacktestEngine
from engine.backtest_optimizer import RealisticDataGenerator
from engine.daily_signal import InvestmentCalendar
from ui.charts import ChartComponents
from config import INDICES, INVESTMENT


# 页面配置
st.set_page_config(
    page_title="量化定投择时系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================
# 主题系统 - CSS在main()中按主题动态生成
# ============================================
THEMES = {
    "深色暗夜": {
        "bg": "#0E1117", "bg2": "#1A1C23", "text": "#E0E0E0",
        "accent": "#00FF88", "border": "#333", "card_bg": "#1A1C23",
    },
    "浅色明亮": {
        "bg": "#FFFFFF", "bg2": "#F0F2F6", "text": "#1A1C23",
        "accent": "#0088FF", "border": "#DDD", "card_bg": "#FFFFFF",
    },
    "护眼绿色": {
        "bg": "#C7EDCC", "bg2": "#D5F0D9", "text": "#2D4A3E",
        "accent": "#2E7D32", "border": "#A5D6A7", "card_bg": "#E8F5E9",
    },
}


def apply_theme(theme_name: str):
    """应用主题CSS - 覆盖所有Streamlit元素"""
    t = THEMES.get(theme_name, THEMES["深色暗夜"])
    css = f"""
<style>
    /* ===== 全局 ===== */
    .main, .stApp {{ background-color: {t["bg"]} !important; }}
    html, body, #root {{ background-color: {t["bg"]} !important; }}
    *, .stMarkdown, p, li, span, div, label, .stText, .st-emotion-cache-1v0mbdj {{ color: {t["text"]} !important; }}
    h1, h2, h3, h4, h5, h6 {{ color: {t["text"]} !important; }}

    /* ===== 侧边栏 ===== */
    div[data-testid="stSidebar"],
    div[data-testid="stSidebarContent"] {{
        background-color: {t["bg2"]} !important;
    }}
    div[data-testid="stSidebar"] * {{
        color: {t["text"]} !important;
    }}

    /* ===== Metric卡片 ===== */
    .stMetric {{
        background-color: {t["card_bg"]} !important;
        border: 1px solid {t["border"]} !important;
        border-radius: 10px; padding: 10px;
    }}
    .stMetric label, div[data-testid="stMetricLabel"] {{ color: {t["text"]} !important; }}
    .stMetric .metric-value, div[data-testid="stMetricValue"] {{ color: {t["accent"]} !important; font-size: 24px !important; font-weight: bold !important; }}
    div[data-testid="stMetricDelta"] {{ color: {t["text"]} !important; }}

    /* ===== 按钮 ===== */
    .stButton>button {{
        background-color: {t["bg2"]} !important;
        color: {t["text"]} !important;
        border: 1px solid {t["border"]} !important;
    }}
    .stButton>button:hover {{ background-color: {t["border"]} !important; border-color: {t["accent"]} !important; }}

    /* ===== 标签页 ===== */
    .stTabs [data-baseweb="tab-list"] {{ background-color: {t["bg2"]} !important; border-radius: 10px; padding: 5px; }}
    .stTabs [data-baseweb="tab"] {{ color: {t["text"]} !important; background-color: transparent !important; }}
    .stTabs [aria-selected="true"] {{ background-color: {t["border"]} !important; border-radius: 8px !important; }}
    div[data-baseweb="tab-panel"] {{ background-color: transparent !important; }}

    /* ===== 展开面板 ===== */
    div[data-testid="stExpander"], details {{
        border-color: {t["border"]} !important;
        background-color: transparent !important;
    }}
    div[data-testid="stExpander"] * {{ color: {t["text"]} !important; }}
    div[data-testid="stExpander"] svg {{ fill: {t["text"]} !important; }}

    /* ===== 选择框/滑块/输入框 ===== */
    .stSelectbox label, .stSlider label, .stNumberInput label,
    div[data-testid="stSelectbox"] *, div[data-testid="stNumberInput"] * {{
        color: {t["text"]} !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: {t["card_bg"]} !important;
        border-color: {t["border"]} !important;
        color: {t["text"]} !important;
    }}
    div[data-baseweb="input"] > input {{
        background-color: {t["card_bg"]} !important;
        border-color: {t["border"]} !important;
        color: {t["text"]} !important;
    }}
    div[data-baseweb="slider"] div[role="slider"] {{ background-color: {t["accent"]} !important; }}
    div[data-baseweb="slider"] div[data-testid="stThumb"] {{ border-color: {t["accent"]} !important; }}

    /* ===== 多选框/单选框 ===== */
    div[role="radiogroup"] label, div[role="group"] label,
    div[data-testid="stCheckbox"] label {{ color: {t["text"]} !important; }}

    /* ===== 提示框 ===== */
    .stAlert, div[data-testid="stAlert"] {{
        background-color: {t["bg2"]} !important;
        color: {t["text"]} !important;
        border-color: {t["border"]} !important;
    }}

    /* ===== 数据表格 ===== */
    .stDataFrame, div[data-testid="stDataFrame"] {{
        background-color: {t["card_bg"]} !important;
    }}
    .stDataFrame * {{ color: {t["text"]} !important; }}

    /* ===== 进度条 ===== */
    div[role="progressbar"] {{ background-color: {t["border"]} !important; }}
    div[role="progressbar"] > div {{ background-color: {t["accent"]} !important; }}

    /* ===== 分割线 ===== */
    hr {{ border-color: {t["border"]} !important; }}

    /* ===== 下拉菜单 ===== */
    div[data-baseweb="popover"] {{
        background-color: {t["card_bg"]} !important;
        border-color: {t["border"]} !important;
    }}
    div[data-baseweb="popover"] li {{ background-color: transparent !important; color: {t["text"]} !important; }}
    div[data-baseweb="popover"] li:hover {{ background-color: {t["border"]} !important; }}

    /* ===== 工具提示 ===== */
    div[role="tooltip"] {{
        background-color: {t["card_bg"]} !important;
        color: {t["text"]} !important;
        border: 1px solid {t["border"]} !important;
    }}

    /* ===== 其他 ===== */
    .st-bd, .st-bb, .st-bc {{ border-color: {t["border"]} !important; }}
    .stProgress {{ background-color: {t["border"]} !important; }}
    .st-cx, .st-cy {{ color: {t["text"]} !important; }}
    svg {{ fill: {t["text"]} !important; }}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


# Excel文件映射（数据主源）
EXCEL_FILES = {
    "kc50": "000688perf科创50.xlsx",
    "zxhl": "000922perf中证红利.xlsx",
    "hldb": "H30269perf红利低波.xlsx",
}


def load_filtered_data(force_refresh: bool = False):
    """
    加载数据：Excel为主源（含代码过滤），缓存为速度辅助
    
    Args:
        force_refresh: True=忽略缓存强制从Excel重新加载
    """
    cache = DataCache()
    data = {}
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # D:\红利

    for key, info in INDICES.items():
        try:
            filename = EXCEL_FILES.get(key)
            if not filename:
                data[key] = None
                continue
            file_path = os.path.join(base_dir, filename)

            # 检查缓存是否有效（比Excel文件更新）
            use_cache = (not force_refresh and cache.exists(key)
                         and os.path.exists(file_path)
                         and os.path.getmtime(file_path) < os.path.getmtime(cache._get_cache_path(key)))

            if use_cache:
                df = cache.load(key)
                print(f"[CACHE] 从缓存加载 {key} ({len(df)} 条)")
            else:
                # 从Excel加载并过滤
                print(f"[EXCEL] 从文件加载 {key} ...")
                raw = pd.read_excel(file_path)
                columns = raw.columns.tolist()
                if len(columns) < 13:
                    raise ValueError(f"格式异常，仅{len(columns)}列")

                # 按文件名中的指数代码过滤
                code_col = columns[1]
                raw[code_col] = raw[code_col].astype(str)
                code_match = re.match(r'([A-Z0-9]+)', os.path.basename(file_path).split('perf')[0])
                correct_code = code_match.group(1).lstrip('0') or '0' if code_match else None
                if correct_code:
                    before = len(raw)
                    raw = raw[raw[code_col] == correct_code].copy()
                    print(f"  [FILTER] 代码={correct_code}, {before}→{len(raw)} 行")

                raw['date'] = pd.to_datetime(raw[columns[0]].astype(str))
                raw['close'] = raw[columns[9]]
                raw['open'] = raw[columns[6]].fillna(raw['close'])
                raw['high'] = raw[columns[7]].fillna(raw['close'])
                raw['low'] = raw[columns[8]].fillna(raw['close'])
                raw['volume'] = raw[columns[12]].fillna(0)

                df = raw[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
                cache.save(key, df)
                print(f"  [OK] {key} 缓存已更新 ({len(df)} 条)")

            df = TechnicalIndicators.calculate_all(df)
            data[key] = df

        except Exception as e:
            print(f"[ERROR] 加载 {info['name']}: {e}")
            # 兜底：尝试缓存
            try:
                if cache.exists(key):
                    df = cache.load(key)
                    df = TechnicalIndicators.calculate_all(df)
                    data[key] = df
                    print(f"[FALLBACK] 使用过期缓存 {key}")
                else:
                    data[key] = None
            except:
                data[key] = None

    return data


def calculate_scores(data, weights=None):
    """计算评分（支持每指数独立权重）"""
    scores = {}
    for key, df in data.items():
        if df is None or len(df) == 0:
            continue

        # 获取最新数据
        latest = df.iloc[-1]

        # 获取权重配置：未指定权重时使用每指数独立优化的权重
        if weights is not None:
            current_weights = weights
        else:
            current_weights = INDICES[key].get("weights", {})

        # 创建评分引擎
        engine = ScoringEngine(weights=current_weights)
        score_result = engine.calculate_total_score(latest)

        scores[key] = {
            "name": INDICES[key]["name"],
            "score": score_result["total"],
            "technical": score_result["technical"],
            "valuation": score_result["valuation"],
            "momentum": score_result["momentum"],
            "sentiment": score_result["sentiment"],
            "fundflow": score_result["fundflow"],
            "grade": engine.get_grade(score_result["total"]),
        }

    return scores


def run_backtest(data_dict, weights, min_score, base_amount=2000):
    """运行回测"""
    from engine.allocation import AllocationEngine
    
    def score_func(row):
        engine = ScoringEngine(weights=weights)
        result = engine.calculate_total_score(row)
        return result["total"]

    def allocation_func(scores):
        engine = AllocationEngine(
            base_amount=base_amount,
            min_score=min_score,
            max_single_ratio=0.6,
        )
        return engine.allocate(scores)

    bt = BacktestEngine(
        initial_capital=100000,
        monthly_invest=base_amount,
        fee_rate=0.0005,
    )

    result = bt.run(
        data_dict=data_dict,
        score_func=score_func,
        allocation_func=allocation_func,
        start_date=data_dict[list(data_dict.keys())[0]]["date"].min().strftime("%Y%m%d"),
        end_date=data_dict[list(data_dict.keys())[0]]["date"].max().strftime("%Y%m%d"),
    )

    return result


def generate_mock_data():
    """生成模拟数据用于演示"""
    generator = RealisticDataGenerator()
    data = {}
    for key, info in INDICES.items():
        df = generator.generate(
            symbol=key,
            start_date="20220101",
            end_date="20260721",
            base_price=1000 if key == "kc50" else (2000 if key == "zxhl" else 1500),
            trend=0.05 if key == "kc50" else (0.02 if key == "zxhl" else 0.03),
            volatility=0.30 if key == "kc50" else (0.18 if key == "zxhl" else 0.15),
            mean_reversion=0.08 if key == "kc50" else (0.12 if key == "zxhl" else 0.15),
        )
        df = TechnicalIndicators.calculate_all(df)
        data[key] = df
    return data


def main():
    """主应用"""
    # 初始化主题CSS（最先执行，确保所有元素渲染时已有正确样式）
    if "theme" not in st.session_state:
        st.session_state.theme = "深色暗夜"
    apply_theme(st.session_state.theme)
    
    # 标题
    st.title("🔬 量化定投择时系统 v2.1")
    st.markdown(f"<p style='font-size: 0.85em; opacity: 0.6;'>最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>", unsafe_allow_html=True)

    # 侧边栏
    with st.sidebar:
        # 主题选择
        theme = st.selectbox("🎨 界面主题", list(THEMES.keys()), 
                            index=list(THEMES.keys()).index(st.session_state.theme))
        if theme != st.session_state.theme:
            st.session_state.theme = theme
            st.rerun()
        ChartComponents.set_theme(st.session_state.theme, THEMES.get(st.session_state.theme))
        
        st.header("⚙️ 配置")
        
        # 基础参数
        st.subheader("基础参数")
        base_amount = st.number_input("月定投金额", value=INVESTMENT["base_amount"], step=100, min_value=1000)
        min_score = st.slider("最低投资阈值", 0, 50, INVESTMENT["min_score"])
        
        # 参数调优
        st.markdown("---")
        st.subheader(" 参数调优")
        
        with st.expander("评分权重", expanded=False):
            technical_weight = st.slider("技术指标权重", 0.0, 1.0, 0.35, 0.05)
            valuation_weight = st.slider("估值因子权重", 0.0, 1.0, 0.25, 0.05)
            momentum_weight = st.slider("动量因子权重", 0.0, 1.0, 0.15, 0.05)
            sentiment_weight = st.slider("情绪因子权重", 0.0, 1.0, 0.10, 0.05)
            fundflow_weight = st.slider("资金因子权重", 0.0, 1.0, 0.15, 0.05)
            
            # 归一化权重
            weight_sum = technical_weight + valuation_weight + momentum_weight + sentiment_weight + fundflow_weight
            if weight_sum > 0:
                custom_weights = {
                    "technical": technical_weight / weight_sum,
                    "valuation": valuation_weight / weight_sum,
                    "momentum": momentum_weight / weight_sum,
                    "sentiment": sentiment_weight / weight_sum,
                    "fundflow": fundflow_weight / weight_sum,
                }
            else:
                custom_weights = {
                    "technical": 0.35,
                    "valuation": 0.25,
                    "momentum": 0.15,
                    "sentiment": 0.10,
                    "fundflow": 0.15,
                }
        
        with st.expander("技术指标参数", expanded=False):
            rsi_oversold = st.slider("RSI超卖阈值", 10, 40, 30, 1)
            kdj_oversold = st.slider("KDJ超卖阈值", 10, 40, 20, 1)
            bias_extreme = st.slider("BIAS极端偏离", -20, -5, -10, 1)
        
        with st.expander("估值参数", expanded=False):
            pe_cheap = st.slider("PE便宜阈值", 5, 25, 15, 1)
            pb_cheap = st.slider("PB便宜阈值", 0.5, 3.0, 1.5, 0.1)
            dividend_high = st.slider("高股息率", 1.0, 6.0, 3.5, 0.1)
        
        st.markdown("---")
        if st.button("🔄 刷新数据（重新从Excel加载）"):
            cache = DataCache()
            cache.clear()
            st.session_state.force_refresh = True
            st.rerun()

    # 加载数据（Excel为主源，缓存辅助）
    force = st.session_state.pop('force_refresh', False)
    with st.spinner("正在加载数据..."):
        data = load_filtered_data(force_refresh=force)

    # 显示数据更新信息
    for key, info in INDICES.items():
        if data.get(key) is not None and not data[key].empty:
            last_date = data[key]['date'].max()
            st.sidebar.markdown(f"<small>{info['name']}: {last_date.strftime('%Y-%m-%d')}</small>", unsafe_allow_html=True)

    # 如果数据加载失败，使用模拟数据
    if not data or all(v is None for v in data.values()):
        st.warning("使用模拟数据进行演示...")
        data = generate_mock_data()

    # 检查数据时效性
    for key, info in INDICES.items():
        if data.get(key) is not None and not data[key].empty:
            last_date = data[key]['date'].max()
            days_old = (datetime.now() - pd.to_datetime(last_date)).days
            if days_old > 3:
                st.sidebar.warning(f"⚠️ {info['name']} 数据已过期 {days_old} 天，建议刷新")

    if not data or all(v is None for v in data.values()):
        st.error("数据加载失败，请检查网络连接或稍后重试")
        return

    # 计算评分
    scores = calculate_scores(data, weights=custom_weights)

    # 资金分配
    allocation_engine = AllocationEngine(base_amount=base_amount, min_score=min_score)
    score_dict = {k: v["score"] for k, v in scores.items()}
    allocation = allocation_engine.allocate(score_dict)

    # ==================== 今日操作信号（主视觉） ====================
    st.markdown("---")
    st.header("📊 今日操作信号")
    
    latest_dates = []
    for key in scores:
        if data.get(key) is not None and not data[key].empty:
            latest_dates.append(data[key]['date'].max())
    last_dt = max(latest_dates).strftime('%Y-%m-%d') if latest_dates else "未知"
    st.caption(f"数据更新于 {last_dt} | 绿色=买入信号 | 黄色=观望 | 红色=暂停")
    
    grade_cfg = {
        'S': {'color': '#00FF88', 'bg': 'rgba(0,255,136,0.08)', 'action': '强烈买入', 'desc': '极度超卖，历史高胜率'},
        'A': {'color': '#88FF00', 'bg': 'rgba(136,255,0,0.08)', 'action': '积极买入', 'desc': '严重超卖，信号可靠'},
        'B': {'color': '#FFD700', 'bg': 'rgba(255,215,0,0.08)', 'action': '适度买入', 'desc': '中度低估，可分批建仓'},
        'C': {'color': '#FF8C00', 'bg': 'rgba(255,140,0,0.08)', 'action': '谨慎参与', 'desc': '轻度低估，小额试探'},
        'D': {'color': '#FF6B6B', 'bg': 'rgba(255,107,107,0.08)', 'action': '持有观望', 'desc': '估值中性，等待更好时机'},
        'F': {'color': '#FF4444', 'bg': 'rgba(255,68,68,0.08)', 'action': '暂停买入', 'desc': '估值偏高，不建议入场'},
    }

    cols = st.columns(3)
    for i, (key, info) in enumerate(scores.items()):
        with cols[i]:
            score = info['score']
            grade = info['grade']
            g = grade_cfg.get(grade, grade_cfg['C'])
            
            # 获取分配金额
            amount = 0
            for rec in allocation.get("recommendations", []):
                if rec["index_key"] == key:
                    amount = rec["amount"]
                    break
            
            # 大号信号卡片
            signal_strength = min(int(score / 20), 5)
            bars = "●" * signal_strength + "○" * (5 - signal_strength)
            
            buy_action = "✅ 建议买入" if grade in ['S', 'A', 'B'] else ("⚠️ 少量参与" if grade == 'C' else "⛔ 暂不建议")
            
            st.markdown(f"""
            <div style='border: 2px solid {g["color"]}; border-radius: 16px; padding: 20px 15px; 
                        background: {g["bg"]}; text-align: center; min-height: 320px;'>
                <h3 style='margin:0; color:{g["color"]};'>{info['name']}</h3>
                <div style='font-size: 56px; font-weight: 900; color:{g["color"]}; margin: 8px 0; line-height:1;'>
                    {grade}</div>
                <div style='font-size: 22px; font-weight: bold; color:{g["color"]}; margin-bottom: 6px;'>
                    {g["action"]}</div>
                <p style='font-size:13px; opacity:0.8; margin:4px 0;'>{g["desc"]}</p>
                <div style='background: {g["color"]}22; border-radius: 8px; padding: 10px; margin: 10px 0;'>
                    <span style='font-size: 24px; font-weight: bold; color:{g["color"]};'>{score:.0f}</span>
                    <span style='font-size: 14px;'> 分</span>
                </div>
                <p style='margin: 4px 0;'>💰 建议: ¥{amount:.0f}</p>
                <p style='margin: 4px 0; font-size: 16px; color:{g["color"]};'>{bars}</p>
                <p style='margin: 4px 0; font-weight: bold; color:{g["color"]};'>{buy_action}</p>
            </div>
            """, unsafe_allow_html=True)

    # 总额摘要
    st.markdown(f"<h3 style='text-align: center; color: {THEMES[st.session_state.theme]['accent']};'>本月建议定投总额: ¥{allocation['total_amount']:.2f}</h3>", unsafe_allow_html=True)
    
    # 三指数信号快速总结
    grade_summary = " | ".join([f"{INDICES[k]['name']}: <span style='color:{grade_cfg.get(scores[k]['grade'],{}).get('color','#888')}'>{scores[k]['grade']}级 {scores[k]['score']:.0f}分</span>" for k in scores])
    st.markdown(f"<p style='text-align: center;'>{grade_summary}</p>", unsafe_allow_html=True)

    # ==================== 评分趋势图 ====================
    st.markdown("---")
    st.subheader("📈 评分趋势")

    # 计算历史评分
    hist_scores = []
    for key, df in data.items():
        if df is None or len(df) < 60:
            continue

        weights = custom_weights
        engine = ScoringEngine(weights=weights)

        score_list = []
        for idx in range(len(df) - 60, len(df)):
            row = df.iloc[idx]
            score_result = engine.calculate_total_score(row)
            score_list.append({
                "date": row["date"],
                key: score_result["total"],
            })

        if score_list:
            hist_scores.append(pd.DataFrame(score_list))

    if hist_scores:
        df_scores = hist_scores[0]
        for df_s in hist_scores[1:]:
            df_scores = df_scores.merge(df_s, on="date", how="outer")

        df_scores = df_scores.sort_values("date").reset_index(drop=True)

        fig = ChartComponents.create_score_trend(df_scores)
        st.plotly_chart(fig, use_container_width=True)

    # ==================== 价格走势图 ====================
    st.markdown("---")
    st.subheader("📈 价格走势")

    tab1, tab2, tab3 = st.tabs(["科创50", "中证红利", "红利低波"])

    tabs = {"kc50": tab1, "zxhl": tab2, "hldb": tab3}
    for key, tab in tabs.items():
        with tab:
            if data.get(key) is not None:
                fig = ChartComponents.create_price_chart(data[key], INDICES[key]["name"])
                st.plotly_chart(fig, use_container_width=True)

    # ==================== 技术指标面板 ====================
    st.markdown("---")
    st.subheader("🔍 技术指标")

    selected = st.selectbox("选择指数", list(INDICES.keys()), format_func=lambda x: INDICES[x]["name"])
    if data.get(selected) is not None:
        fig = ChartComponents.create_technical_subplots(data[selected])
        st.plotly_chart(fig, use_container_width=True)

    # ==================== 历史回测（折叠） ====================
    st.markdown("---")
    st.subheader("🎯 多因子对比")

    if scores:
        # 确保所有分数数据都传递给雷达图
        radar_scores = {}
        for key, info in scores.items():
            radar_scores[key] = {
                "name": info.get("name", key),
                "technical": info.get("technical", 0),
                "valuation": info.get("valuation", 0),
                "momentum": info.get("momentum", 0),
                "sentiment": info.get("sentiment", 0),
                "fundflow": info.get("fundflow", 0),
            }
        
        fig = ChartComponents.create_radar_chart(radar_scores)
        st.plotly_chart(fig, use_container_width=True)

    # ==================== 回测面板 ====================
    st.markdown("---")
    st.subheader("📊 策略回测")

    with st.expander("🔬 运行回测", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            backtest_start = st.date_input("回测开始日期", value=datetime(2022, 1, 1))
            backtest_end = st.date_input("回测结束日期", value=datetime(2026, 7, 21))
        with col2:
            backtest_amount = st.number_input("回测月投金额", value=2000, step=100)
            backtest_min_score = st.slider("回测最低阈值", 0, 50, 45)

        if st.button("🚀 运行回测"):
            with st.spinner("正在运行回测..."):
                # 使用真实数据而不是模拟数据
                bt_data = {}
                for key, info in INDICES.items():
                    try:
                        # 尝试加载真实Excel数据
                        if key == "kc50":
                            file_path = "../000688perf科创50.xlsx"
                        elif key == "zxhl":
                            file_path = "../000922perf中证红利.xlsx"
                        elif key == "hldb":
                            file_path = "../H30269perf红利低波.xlsx"
                        else:
                            continue
                            
                        df = pd.read_excel(file_path)
                        columns = df.columns.tolist()
                        
                        # 转换数据格式
                        df['date'] = pd.to_datetime(df[columns[0]].astype(str))
                        df['close'] = df[columns[9]]
                        
                        # 添加其他必要列
                        df['open'] = df[columns[6]]
                        df['high'] = df[columns[7]]
                        df['low'] = df[columns[8]]
                        df['volume'] = df[columns[12]]
                        
                        # 计算技术指标
                        df = TechnicalIndicators.calculate_all(df)
                        bt_data[key] = df
                        
                    except Exception as e:
                        st.warning(f"加载 {info['name']} 真实数据失败，使用模拟数据")
                        # 回退到模拟数据
                        bt_data[key] = generate_mock_data()[key]
                
                # 过滤日期
                filtered_data = {}
                for key, df in bt_data.items():
                    mask = (df["date"] >= pd.to_datetime(backtest_start)) & (df["date"] <= pd.to_datetime(backtest_end))
                    filtered_data[key] = df[mask].copy()
                
                # 运行回测
                weights = custom_weights
                result = run_backtest(filtered_data, weights, backtest_min_score, backtest_amount)
                
                # 显示结果
                st.success("回测完成！")
                
                # 关键指标卡片
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("累计投入", f"¥{result['cumulative_invested']:,.0f}")
                col2.metric("最终价值", f"¥{result['final_value']:,.2f}")
                col3.metric("总收益", f"{result['total_return']:.2f}%")
                col4.metric("年化收益", f"{result['annual_return']:.2f}%")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("最大回撤", f"{result['max_drawdown']:.2f}%")
                col2.metric("夏普比率", f"{result['sharpe_ratio']:.2f}")
                col3.metric("胜率", f"{result.get('win_rate', 0):.1f}%")
                
                # 权益曲线 vs 累计投入
                if result["portfolio_values"]:
                    st.markdown("---")
                    st.subheader("📈 权益曲线")
                    fig = ChartComponents.create_backtest_equity_curve(
                        result["portfolio_values"],
                        result.get("trades", [])
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # 回撤图
                if result["portfolio_values"]:
                    st.markdown("---")
                    st.subheader("📉 回撤分析")
                    fig = ChartComponents.create_drawdown_chart(result["portfolio_values"])
                    st.plotly_chart(fig, use_container_width=True)
                
                # 月度收益热力图
                if result["portfolio_values"]:
                    st.markdown("---")
                    st.subheader("🗓️ 月度收益热力图")
                    fig = ChartComponents.create_monthly_returns_heatmap(result["portfolio_values"])
                    st.plotly_chart(fig, use_container_width=True)
                
                # 滚动夏普比率
                if result["portfolio_values"]:
                    st.markdown("---")
                    st.subheader("📊 滚动夏普比率")
                    fig = ChartComponents.create_rolling_sharpe(result["portfolio_values"], window=12)
                    st.plotly_chart(fig, use_container_width=True)
                
                # 基准对比
                if result.get("benchmark"):
                    st.markdown("---")
                    st.subheader("📊 基准对比")
                    
                    bench = result["benchmark"]
                    col1, col2 = st.columns(2)
                    col1.metric("策略总收益", f"{result['total_return']:.2f}%")
                    col2.metric("基准总收益", f"{bench.get('total_return', 0):.2f}%")
                    
                    # 超额收益
                    excess = result['total_return'] - bench.get('total_return', 0)
                    st.info(f"超额收益: {excess:.2f}%")
                
                # 交易历史
                if result.get("trades"):
                    st.markdown("---")
                    st.subheader("📋 交易历史")
                    trade_df = ChartComponents.create_trade_history_table(result["trades"])
                    if not trade_df.empty:
                        st.dataframe(trade_df, use_container_width=True)
                        
                        # 交易统计
                        st.markdown("**交易统计**")
                        trade_stats = {
                            "总交易次数": len(result["trades"]),
                            "总手续费": f"¥{sum(t['fee'] for t in result['trades']):.2f}",
                            "平均单次金额": f"¥{np.mean([t['amount'] for t in result['trades']]):.2f}",
                        }
                        st.json(trade_stats)
                
                # 分红记录
                if result.get("dividends"):
                    st.markdown("---")
                    st.subheader("💰 分红再投资记录")
                    div_df = pd.DataFrame(result["dividends"])
                    if not div_df.empty:
                        div_df["date"] = pd.to_datetime(div_df["date"]).dt.strftime("%Y-%m-%d")
                        st.dataframe(div_df, use_container_width=True)
                        st.info(f"累计分红再投资: ¥{div_df['dividend_amount'].sum():.2f}")

    # ==================== 底部信息 ====================
    st.markdown("---")
    st.markdown("<p style='text-align: center; opacity: 0.5;'>量化定投择时系统 v2.1 | 数据仅供参考，不构成投资建议</p>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
