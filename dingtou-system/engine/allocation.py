"""
资金分配算法
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


class AllocationEngine:
    """资金分配引擎"""

    def __init__(self, base_amount: float = 2000, min_score: float = 25, max_single_ratio: float = 0.3):
        """
        Args:
            base_amount: 月定投基础金额
            min_score: 最低投资评分阈值
            max_single_ratio: 单个标的最高占比
        """
        self.base_amount = base_amount
        self.min_score = min_score
        self.max_single_ratio = max_single_ratio

    def get_multiplier(self, score: float) -> float:
        """根据评分获取定投倍数"""
        if score >= 85:
            return 2.0
        elif score >= 70:
            return 1.5
        elif score >= 55:
            return 1.0
        elif score >= 40:
            return 0.5
        elif score >= 25:
            return 0.25
        else:
            return 0.0

    def get_grade_label(self, score: float) -> str:
        """获取等级标签"""
        if score >= 85:
            return "极度超卖"
        elif score >= 70:
            return "严重超卖"
        elif score >= 55:
            return "中度超卖"
        elif score >= 40:
            return "轻度超卖"
        elif score >= 25:
            return "中性区域"
        else:
            return "偏强区域"

    def allocate(self, scores: Dict[str, float]) -> Dict[str, dict]:
        """
        动态资金分配

        策略：
        1. 过滤合格标的（score >= min_score）
        2. 计算每个标的的加权评分 = score * multiplier
        3. 按加权评分比例分配 base_amount
        4. 应用 max_single_ratio 限制
        5. 确保总额不超过 base_amount * max_multiplier

        Args:
            scores: {index_key: score} 各标的评分

        Returns:
            dict: 分配结果
        """
        # 过滤合格标的
        qualified = {k: v for k, v in scores.items() if v >= self.min_score}

        if not qualified:
            return {
                "total_amount": 0,
                "recommendations": [],
                "message": "所有标的评分均低于阈值，建议暂停定投",
            }

        # 计算每个标的的加权评分 = score * multiplier
        weighted_scores = {}
        for index_key, score in qualified.items():
            multiplier = self.get_multiplier(score)
            weighted_scores[index_key] = score * multiplier

        # 计算总加权评分
        total_weighted_score = sum(weighted_scores.values())

        # 计算基础分配金额（按加权评分比例分配 base_amount）
        raw_amounts = {}
        for index_key, score in qualified.items():
            multiplier = self.get_multiplier(score)
            if total_weighted_score > 0:
                ratio = weighted_scores[index_key] / total_weighted_score
            else:
                ratio = 0
            
            # 分配金额 = base_amount * 比例
            amount = self.base_amount * ratio
            
            raw_amounts[index_key] = {
                "score": score,
                "multiplier": multiplier,
                "ratio": ratio,
                "amount": amount,
            }

        # 应用 max_single_ratio 限制
        max_single_amount = self.base_amount * self.max_single_ratio
        capped = {}
        excess = 0.0
        
        for index_key, info in raw_amounts.items():
            if info["amount"] > max_single_amount:
                excess += info["amount"] - max_single_amount
                capped[index_key] = {**info, "amount": max_single_amount}
            else:
                capped[index_key] = info.copy()

        # 将超出部分重新分配给未超限的标的（按加权评分比例）
        if excess > 0:
            uncapped = {k: v for k, v in capped.items() if v["amount"] < max_single_amount}
            if uncapped:
                uncapped_total_score = sum(weighted_scores[k] for k in uncapped)
                for index_key in uncapped:
                    if uncapped_total_score > 0:
                        add_ratio = weighted_scores[index_key] / uncapped_total_score
                        capped[index_key]["amount"] += excess * add_ratio

        # 构建推荐列表
        recommendations = []
        total_amount = 0.0
        for index_key, info in capped.items():
            total_amount += info["amount"]

        # 重新计算实际占比（考虑capping和重新分配后的实际金额）
        for index_key, info in capped.items():
            actual_ratio = info["amount"] / total_amount * 100 if total_amount > 0 else 0
            recommendations.append({
                "index_key": index_key,
                "score": info["score"],
                "grade": self._get_grade(info["score"]),
                "label": self.get_grade_label(info["score"]),
                "multiplier": info["multiplier"],
                "amount": round(info["amount"], 2),
                "ratio": round(actual_ratio, 2),
            })

        return {
            "total_amount": round(total_amount, 2),
            "recommendations": recommendations,
            "message": f"本月建议定投总额: ¥{total_amount:.2f}",
        }

    def _get_grade(self, score: float) -> str:
        """获取等级字母"""
        if score >= 85:
            return "S"
        elif score >= 70:
            return "A"
        elif score >= 55:
            return "B"
        elif score >= 40:
            return "C"
        elif score >= 25:
            return "D"
        else:
            return "F"

    def get_color(self, score: float) -> str:
        """获取评分对应的颜色"""
        if score >= 85:
            return "#00FF88"  # 绿色
        elif score >= 70:
            return "#88FF00"
        elif score >= 55:
            return "#FFD700"  # 金色
        elif score >= 40:
            return "#FF8C00"  # 橙色
        elif score >= 25:
            return "#FF6B6B"
        else:
            return "#FF4444"  # 红色


if __name__ == "__main__":
    engine = AllocationEngine(base_amount=2000)

    scores = {
        "kc50": 85,
        "zxhl": 62,
        "hldb": 55,
    }

    result = engine.allocate(scores)
    print(f"总金额: ¥{result['total_amount']}")
    for rec in result["recommendations"]:
        print(f"  {rec['index_key']}: {rec['score']:.1f}分 [{rec['grade']}级] "
              f"-> ¥{rec['amount']} ({rec['ratio']}%)")
