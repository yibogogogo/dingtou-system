"""
量化定投择时系统 - 全局配置
"""

# ============================================
# 指数配置
# ============================================

INDICES = {
    "kc50": {
        "name": "科创50",
        "code": "000688",
        "short": "KC50",
        "type": "成长型",
        "description": "高波动成长型指数",
        "weights": {
            "technical": 0.383,
            "valuation": 0.173,
            "momentum": 0.099,
            "sentiment": 0.158,
            "fundflow": 0.187,
        }
    },
    "zxhl": {
        "name": "中证红利",
        "code": "000922",
        "short": "ZXHL",
        "type": "防御型",
        "description": "高股息防御型指数",
        "weights": {
            "technical": 0.183,
            "valuation": 0.263,
            "momentum": 0.335,
            "sentiment": 0.104,
            "fundflow": 0.116,
        }
    },
    "hldb": {
        "name": "红利低波",
        "code": "H30269",
        "short": "HLDB",
        "type": "ETF代理",
        "description": "红利低波ETF(563020)在线实时数据",
        "weights": {
            "technical": 0.202,
            "valuation": 0.103,
            "momentum": 0.355,
            "sentiment": 0.244,
            "fundflow": 0.096,
        }
    },
}

# ============================================
# 定投参数
# ============================================

INVESTMENT = {
    "base_amount": 2000,        # 月定投基础金额（元）
    "min_score": 47,           # 最低投资评分阈值（经各指数独立优化后取均值）
    "max_single_ratio": 0.6,   # 单个标的最高占比
}

# ============================================
# 评分等级
# ============================================

GRADE_CONFIG = {
    "S": {"min": 85, "max": 100, "multiplier": 2.0, "label": "极度超卖"},
    "A": {"min": 70, "max": 84, "multiplier": 1.5, "label": "严重超卖"},
    "B": {"min": 55, "max": 69, "multiplier": 1.0, "label": "中度超卖"},
    "C": {"min": 40, "max": 54, "multiplier": 0.5, "label": "轻度超卖"},
    "D": {"min": 25, "max": 39, "multiplier": 0.25, "label": "中性区域"},
    "F": {"min": 0, "max": 24, "multiplier": 0.0, "label": "偏强区域"},
}

# ============================================
# 技术指标参数
# ============================================

TECH_PARAMS = {
    "rsi": {"short": 6, "mid": 12, "long": 24},
    "kdj": {"n": 9, "m1": 3, "m2": 3},
    "bias": {"short": 5, "mid": 10, "long": 20, "vlong": 60},
    "macd": {"fast": 12, "slow": 26, "signal": 9},
}

# ============================================
# 数据配置
# ============================================

DATA_CONFIG = {
    "data_dir": "data",
    "cache_format": "parquet",
    "lookback_days": 365,       # 回溯天数
    "history_start": "20190101", # 历史数据起始
}

# ============================================
# 回测参数
# ============================================

BACKTEST_CONFIG = {
    "start_date": "20190101",
    "end_date": "20260721",
    "initial_capital": 100000,
    "monthly_invest": 2000,
    "fee_rate": 0.0005,  # 交易费率 0.05%
}
