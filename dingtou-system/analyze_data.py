import pandas as pd
import numpy as np

# 读取三个指数的真实数据
data_summary = {}

for key, file in [('kc50', '../000688perf科创50.xlsx'), ('zxhl', '../000922perf中证红利.xlsx'), ('hldb', '../H30269perf红利低波.xlsx')]:
    df = pd.read_excel(file)
    columns = df.columns.tolist()
    
    # 转换日期格式
    df['date'] = pd.to_datetime(df[columns[0]].astype(str))
    df['close'] = df[columns[9]]
    
    # 计算日收益率
    df['daily_return'] = df['close'].pct_change()
    
    # 计算月度收益率
    df['year_month'] = df['date'].dt.to_period('M')
    monthly_returns = df.groupby('year_month')['close'].last().pct_change()
    
    # 计算年化收益率
    total_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    annual_return = ((df['close'].iloc[-1] / df['close'].iloc[0]) ** (365.25 / (df['date'].iloc[-1] - df['date'].iloc[0]).days) - 1) * 100
    
    # 计算波动率
    daily_vol = df['daily_return'].std() * np.sqrt(252) * 100
    monthly_vol = monthly_returns.std() * np.sqrt(12) * 100
    
    # 最大回撤
    cummax = df['close'].cummax()
    drawdown = (df['close'] - cummax) / cummax
    max_drawdown = drawdown.min() * 100
    
    data_summary[key] = {
        'name': file.split('/')[-1].split('.')[0],
        'start_date': df['date'].iloc[0].strftime('%Y-%m-%d'),
        'end_date': df['date'].iloc[-1].strftime('%Y-%m-%d'),
        'total_return': total_return,
        'annual_return': annual_return,
        'daily_volatility': daily_vol,
        'monthly_volatility': monthly_vol,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': annual_return / daily_vol if daily_vol != 0 else 0,
        'data_points': len(df),
    }

print('=' * 80)
print('真实数据统计摘要')
print('=' * 80)
for key, info in data_summary.items():
    print(f"\n{info['name']} ({key}):")
    print(f"  时间范围: {info['start_date']} ~ {info['end_date']}")
    print(f"  数据点数: {info['data_points']}")
    print(f"  总收益: {info['total_return']:.2f}%")
    print(f"  年化收益: {info['annual_return']:.2f}%")
    print(f"  日波动率: {info['daily_volatility']:.2f}%")
    print(f"  月波动率: {info['monthly_volatility']:.2f}%")
    print(f"  最大回撤: {info['max_drawdown']:.2f}%")
    print(f"  夏普比率: {info['sharpe_ratio']:.2f}")
