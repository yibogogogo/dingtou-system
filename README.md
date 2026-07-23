# 量化定投择时系统 v2.1

> 基于多因子评分的指数基金定投择时系统，支持科创50、中证红利、红利低波三个指数

## 核心特性

- **五因子评分模型**：技术指标(38.3%) + 估值因子(17.3%) + 动量因子(9.9%) + 情绪因子(15.8%) + 资金因子(18.7%)
- **三指数独立优化**：每个指数拥有独立的最优权重配置
- **历史信号验证**：基于真实数据的训练/测试集划分，科学评估信号有效性
- **回测引擎**：季度分红再投资、年化收益、夏普比率、最大回撤、基准对比
- **Streamlit Web界面**：三主题切换（深色/浅色/护眼），实时可视化

## 快速开始

```bash
cd dingtou-system
pip install -r requirements.txt
streamlit run app.py
```

或直接运行：
```bash
python run_app.py
```

## 项目结构

```
dingtou-system/
├── app.py                    # Streamlit主应用
├── config.py                 # 全局配置（每指数优化权重）
├── run_app.py                # EXE入口脚本
├── build_exe.py              # PyInstaller打包脚本
├── engine/                   # 核心引擎
│   ├── scoring.py            # 五因子评分引擎
│   ├── allocation.py         # 动态资金分配
│   ├── backtest.py           # 回测引擎（含分红再投资）
│   ├── backtest_enhanced.py  # 增强版回测引擎
│   ├── backtest_optimizer.py # 参数优化器
│   ├── indicators.py         # 技术指标计算（RSI/KDJ/MACD/BIAS）
│   ├── valuation.py          # 估值指标（PE/PB/股息率百分位）
│   ├── daily_signal.py       # 每日操作信号
│   ├── historical_validator.py # 历史信号验证
│   └── validated_daily_signal.py # 经过验证的每日信号
├── data/                     # 数据层
│   ├── fetcher.py            # 多源数据获取（akshare/中证指数/EastMoney）
│   └── cache.py              # 数据缓存管理
├── ui/
│   └── charts.py             # Plotly图表组件
└── optimization_*.json       # 各指数最优参数
```

## 评分体系

| 等级 | 阈值 | 倍数 | 操作建议 |
|------|------|------|----------|
| **S** | ≥85分 | 2.0x | 强烈买入 — 极度超卖 |
| **A** | ≥70分 | 1.5x | 积极买入 — 严重超卖 |
| **B** | ≥55分 | 1.0x | 适度买入 — 中度超卖 |
| **C** | ≥40分 | 0.5x | 轻度买入 — 谨慎参与 |
| **D** | ≥25分 | 0.25x | 持有观望 — 中性区域 |
| **F** | <25分 | 0 | 暂停 — 偏强区域 |

## 因子权重（经独立优化）

| 因子 | 科创50 | 中证红利 | 红利低波 |
|------|--------|----------|----------|
| 技术指标 | **38.3%** | 18.3% | 20.2% |
| 估值因子 | 17.3% | **26.3%** | 10.3% |
| 动量因子 | 9.9% | **33.5%** | **35.5%** |
| 情绪因子 | 15.8% | 10.4% | **24.4%** |
| 资金因子 | 18.7% | 11.6% | 9.6% |

## 数据说明

- **数据源**：中证指数官网导出的日线OHLC数据（2021-07-22 ~ 2026-07-20）
- **除权处理**：使用价格指数 + 每季度手动分红再投资（股息率：科创50~0.5%，中证红利~5%，红利低波~4.5%）
- **数据过滤**：自动过滤Excel中混入的其他指数代码数据

## 技术要求

- Python 3.8+
- streamlit, pandas, numpy, plotly, openpyxl
- 可选：akshare（在线数据获取），PyInstaller（EXE打包）

## 免责声明

本系统仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。

---

## Quantitative DCA Timing System v2.1

A multi-factor scoring system for index fund Dollar-Cost Averaging (DCA) with timing optimization, supporting three CSI indices.

**Features**: 5-factor scoring | Per-index optimized weights | Backtest with dividend reinvestment | Streamlit dashboard with 3 themes
