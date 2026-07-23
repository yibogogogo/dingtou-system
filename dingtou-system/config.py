"""
量化定投择时系统 - 全局配置 (ETF版 | 四指数)
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
    "a500": {
        "name": "中证A500",
        "code": "563360",
        "short": "A500",
        "type": "ETF",
        "description": "中证A500ETF易方达(563360)",
        "weights": {"technical": 0.233, "valuation": 0.365, "momentum": 0.110, "sentiment": 0.153, "fundflow": 0.139},
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
    "min_score": 40,
}
