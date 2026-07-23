"""
量化定投择时系统 - 全局配置 (ETF版 | 经独立优化)
"""
INDICES = {
    "kc50": {
        "name": "科创50",
        "code": "588080",
        "short": "KC50",
        "type": "ETF",
        "description": "科创50ETF易方达(588080)",
        "weights": {"technical": 0.383, "valuation": 0.173, "momentum": 0.099, "sentiment": 0.158, "fundflow": 0.187},
    },
    "zxhl": {
        "name": "中证红利",
        "code": "515180",
        "short": "ZXHL",
        "type": "ETF",
        "description": "中证红利ETF易方达(515180)",
        "weights": {"technical": 0.443, "valuation": 0.081, "momentum": 0.122, "sentiment": 0.277, "fundflow": 0.077},
    },
    "hldb": {
        "name": "红利低波",
        "code": "563020",
        "short": "HLDB",
        "type": "ETF",
        "description": "红利低波ETF易方达(563020)",
        "weights": {"technical": 0.109, "valuation": 0.475, "momentum": 0.134, "sentiment": 0.147, "fundflow": 0.135},
    },
}

INVESTMENT = {
    "base_amount": 2000,
    "min_score": 40,  # ETF数据下各指数最优min_score差异大，取折中
}
