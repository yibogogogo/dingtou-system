import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class DailySignalEngine:
    """
    每日操作信号引擎
    
    核心逻辑：
    1. 根据评分等级确定信号类型
    2. 根据信号类型确定入场日期和金额
    3. 生成具体的操作指令
    """
    
    def __init__(self, base_amount: float = 2000):
        self.base_amount = base_amount
        
        # 评分等级配置
        self.grade_config = {
            'S': {
                'min_score': 85,
                'signal': 'STRONG_BUY',
                'multiplier': 2.0,
                'description': '极度超卖，强烈建议买入',
                'action': '立即买入',
                'urgency': '高',
            },
            'A': {
                'min_score': 70,
                'signal': 'BUY',
                'multiplier': 1.5,
                'description': '严重超卖，建议买入',
                'action': '积极买入',
                'urgency': '中高',
            },
            'B': {
                'min_score': 55,
                'signal': 'MODERATE_BUY',
                'multiplier': 1.0,
                'description': '中度超卖，适度买入',
                'action': '适度买入',
                'urgency': '中',
            },
            'C': {
                'min_score': 40,
                'signal': 'LIGHT_BUY',
                'multiplier': 0.5,
                'description': '轻度超卖，轻度买入',
                'action': '轻度买入',
                'urgency': '低',
            },
            'D': {
                'min_score': 25,
                'signal': 'HOLD',
                'multiplier': 0.25,
                'description': '中性区域，持有观望',
                'action': '持有观望',
                'urgency': '无',
            },
            'F': {
                'min_score': 0,
                'signal': 'REDUCE',
                'multiplier': 0.0,
                'description': '偏强区域，建议减仓',
                'action': '减仓或暂停',
                'urgency': '高',
            },
        }
    
    def get_grade(self, score: float) -> str:
        """根据评分获取等级"""
        for grade in ['S', 'A', 'B', 'C', 'D', 'F']:
            if score >= self.grade_config[grade]['min_score']:
                return grade
        return 'F'
    
    def get_signal(self, score: float) -> Dict:
        """根据评分获取信号信息"""
        grade = self.get_grade(score)
        config = self.grade_config[grade]
        
        return {
            'grade': grade,
            'signal_type': config['signal'],
            'multiplier': config['multiplier'],
            'description': config['description'],
            'action': config['action'],
            'urgency': config['urgency'],
            'amount': self.base_amount * config['multiplier'],
        }
    
    def generate_daily_signal(self, 
                              index_key: str,
                              index_name: str,
                              current_score: float,
                              previous_score: float = None,
                              current_price: float = None,
                              previous_price: float = None) -> Dict:
        """
        生成每日操作信号
        
        Args:
            index_key: 指数代码
            index_name: 指数名称
            current_score: 当前评分
            previous_score: 昨日评分（可选）
            current_price: 当前价格（可选）
            previous_price: 昨日价格（可选）
            
        Returns:
            dict: 操作信号详情
        """
        signal = self.get_signal(current_score)
        
        # 计算评分变化
        score_change = 0
        if previous_score is not None:
            score_change = current_score - previous_score
        
        # 计算价格变化
        price_change = 0
        if current_price is not None and previous_price is not None:
            price_change = (current_price - previous_price) / previous_price * 100
        
        # 生成操作指令
        instructions = self._generate_instructions(
            index_name, signal, score_change, price_change
        )
        
        return {
            'index_key': index_key,
            'index_name': index_name,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'current_score': current_score,
            'previous_score': previous_score,
            'score_change': score_change,
            'current_price': current_price,
            'price_change': price_change,
            'grade': signal['grade'],
            'signal_type': signal['signal_type'],
            'multiplier': signal['multiplier'],
            'suggested_amount': signal['amount'],
            'description': signal['description'],
            'action': signal['action'],
            'urgency': signal['urgency'],
            'instructions': instructions,
        }
    
    def _generate_instructions(self, 
                              index_name: str,
                              signal: Dict,
                              score_change: float,
                              price_change: float) -> List[str]:
        """生成具体操作指令"""
        instructions = []
        
        grade = signal['grade']
        action = signal['action']
        amount = signal['amount']
        
        # 基础指令
        instructions.append(f"[{index_name}] Today Operation:")
        instructions.append(f"  Current Grade: {grade} ({signal['signal_type']})")
        instructions.append(f"  Operation: {action}")
        
        if amount > 0:
            instructions.append(f"  Suggested Amount: ${amount:.0f}")
        else:
            instructions.append(f"  Suggested Amount: Pause investment")
        
        # 评分变化分析
        if score_change != 0:
            direction = "Up" if score_change > 0 else "Down"
            instructions.append(f"  Score Change: {direction} {abs(score_change):.1f} points")
        
        # 价格变化分析
        if price_change != 0:
            direction = "Up" if price_change > 0 else "Down"
            instructions.append(f"  Price Change: {direction} {abs(price_change):.2f}%")
        
        # 具体操作建议
        instructions.append(f"\n  Details:")
        instructions.append(f"  {signal['description']}")
        
        if grade in ['S', 'A']:
            instructions.append(f"  * Market is oversold, good buying opportunity")
            instructions.append(f"  * Consider分批买入, don't invest all at once")
            instructions.append(f"  * Set price alerts for further declines")
        elif grade in ['B', 'C']:
            instructions.append(f"  * Market is mildly oversold, moderate participation")
            instructions.append(f"  * Small amount定投, keep watching")
        elif grade == 'D':
            instructions.append(f"  * Market is neutral, wait and see")
            instructions.append(f"  * Pause定投, wait for better entry")
        else:
            instructions.append(f"  * Market is strong, consider reducing or pausing")
            instructions.append(f"  * Avoid chasing highs, wait for pullback")
        
        return instructions
    
    def generate_monthly_plan(self, 
                             index_key: str,
                             index_name: str,
                             daily_scores: List[Tuple[datetime, float]],
                             daily_prices: List[Tuple[datetime, float]] = None) -> Dict:
        """
        生成月度投资计划
        
        Args:
            index_key: 指数代码
            index_name: 指数名称
            daily_scores: 每日评分列表 [(date, score), ...]
            daily_prices: 每日价格列表 [(date, price), ...]
            
        Returns:
            dict: 月度投资计划
        """
        if not daily_scores:
            return {
                'index_key': index_key,
                'index_name': index_name,
                'plan': 'No data',
                'total_amount': 0,
                'investment_days': [],
            }
        
        # 按评分排序，找出最佳入场日
        sorted_scores = sorted(daily_scores, key=lambda x: x[1], reverse=True)
        
        # 选择评分最高的几天作为入场日
        investment_days = []
        total_amount = 0
        
        for date, score in sorted_scores[:5]:  # 最多选择5天
            signal = self.get_signal(score)
            if signal['multiplier'] > 0:
                amount = self.base_amount * signal['multiplier']
                investment_days.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'score': score,
                    'grade': signal['grade'],
                    'amount': amount,
                    'reason': signal['description'],
                })
                total_amount += amount
        
        return {
            'index_key': index_key,
            'index_name': index_name,
            'month': daily_scores[0][0].strftime('%Y-%m'),
            'plan': f'Suggested {len(investment_days)} investments this month',
            'total_amount': total_amount,
            'investment_days': investment_days,
        }


class InvestmentCalendar:
    """
    投资日历
    管理每日的投资计划和执行情况
    """
    
    def __init__(self, base_amount: float = 2000):
        self.base_amount = base_amount
        self.signal_engine = DailySignalEngine(base_amount)
        self.calendar = {}
    
    def add_day(self, date: datetime, signals: List[Dict]):
        """添加一天的投资信号"""
        self.calendar[date.strftime('%Y-%m-%d')] = {
            'date': date,
            'signals': signals,
            'total_amount': sum(s['suggested_amount'] for s in signals),
        }
    
    def get_day_plan(self, date_str: str) -> Dict:
        """获取某天的投资计划"""
        return self.calendar.get(date_str, {
            'date': date_str,
            'signals': [],
            'total_amount': 0,
            'message': 'No investment plan',
        })
    
    def get_month_summary(self, year: int, month: int) -> Dict:
        """获取月度投资汇总"""
        month_signals = []
        total_invested = 0
        
        for date_str, day_data in self.calendar.items():
            date = datetime.strptime(date_str, '%Y-%m-%d')
            if date.year == year and date.month == month:
                month_signals.extend(day_data['signals'])
                total_invested += day_data['total_amount']
        
        return {
            'year': year,
            'month': month,
            'total_days': len(month_signals),
            'total_invested': total_invested,
            'signals': month_signals,
        }
