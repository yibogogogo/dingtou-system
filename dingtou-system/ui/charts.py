"""
可视化图表组件 - Plotly图表 (增强版)
新增：回测图表、月度收益热力图、滚动夏普比率
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List


class ChartComponents:
    """图表组件"""

    # 主题配置（通过 set_theme 更新）
    plotly_template = "plotly_dark"
    paper_bgcolor = "#0E1117"
    plot_bgcolor = "#0E1117"
    font_color = "#E0E0E0"
    grid_color = "#333"

    @classmethod
    def set_theme(cls, theme: str, theme_colors: dict = None):
        """设置图表主题"""
        templates = {
            "深色暗夜": "plotly_dark",
            "浅色明亮": "plotly",
            "护眼绿色": "plotly",
        }
        cls.plotly_template = templates.get(theme, "plotly_dark")
        if theme_colors:
            cls.paper_bgcolor = theme_colors.get("bg", cls.paper_bgcolor)
            cls.plot_bgcolor = theme_colors.get("bg2", cls.paper_bgcolor)
            cls.font_color = theme_colors.get("text", cls.font_color)
            cls.grid_color = theme_colors.get("border", cls.grid_color)

    @staticmethod
    def create_score_cards(scores: Dict[str, dict]) -> go.Figure:
        """
        创建评分卡片（使用Indicator）

        Args:
            scores: {index_key: {"name": str, "score": float, "grade": str, "amount": float}}
        """
        fig = make_subplots(
            rows=1,
            cols=len(scores),
            specs=[[{"type": "indicator"} for _ in range(len(scores))]],
        )

        colors = {"S": "#00FF88", "A": "#88FF00", "B": "#FFD700", "C": "#FF8C00", "D": "#FF6B6B", "F": "#FF4444"}

        for i, (key, info) in enumerate(scores.items()):
            color = colors.get(info.get("grade", "B"), "#FFD700")
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=info["score"],
                    title={"text": f"{info['name']}<br><span style='font-size:14px'>{info.get('grade', 'B')}级</span>"},
                    delta={"reference": 50, "increasing": {"color": "#00FF88"}, "decreasing": {"color": "#FF4444"}},
                    gauge={
                        "axis": {"range": [0, 100], "tickwidth": 1},
                        "bar": {"color": color},
                        "bgcolor": "#1A1C23",
                        "borderwidth": 2,
                        "bordercolor": "#333",
                        "steps": [
                            {"range": [0, 25], "color": "#2a1a1a"},
                            {"range": [25, 40], "color": "#2a2a1a"},
                            {"range": [40, 55], "color": "#2a2a1a"},
                            {"range": [55, 70], "color": "#1a2a1a"},
                            {"range": [70, 85], "color": "#1a2a1a"},
                            {"range": [85, 100], "color": "#1a2a1a"},
                        ],
                        "threshold": {
                            "line": {"color": "white", "width": 2},
                            "thickness": 0.75,
                            "value": 50,
                        },
                    },
                    domain={"row": 0, "column": i},
                ),
                row=1,
                col=i + 1,
            )

        fig.update_layout(
            paper_bgcolor=ChartComponents.paper_bgcolor,
            font={"color": ChartComponents.font_color, "size": 14},
            height=300,
            margin={"t": 50, "b": 30, "l": 30, "r": 30},
        )

        return fig

    @staticmethod
    def create_score_trend(df_scores: pd.DataFrame) -> go.Figure:
        """
        创建评分趋势图

        Args:
            df_scores: DataFrame with columns: date, kc50, zxhl, hldb
        """
        fig = go.Figure()

        colors = {"kc50": "#00FF88", "a50": "#00AAFF", "a500": "#E040FB", "zxhl": "#FFD700", "hldb": "#FF8C00"}
        names = {"kc50": "科创50", "a50": "中证A50", "a500": "中证A500", "zxhl": "中证红利", "hldb": "红利低波"}
        for col in ["kc50", "a50", "a500", "zxhl", "hldb"]:
            if col in df_scores.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_scores["date"],
                        y=df_scores[col],
                        mode="lines",
                        name=names.get(col, col),
                        line={"color": colors.get(col, "#FFF"), "width": 2},
                        hovertemplate="%{y:.1f}分<extra></extra>",
                    )
                )

        fig.add_hline(y=85, line_dash="dash", line_color="#00FF88", opacity=0.5, annotation_text="S级")
        fig.add_hline(y=70, line_dash="dash", line_color="#88FF00", opacity=0.5, annotation_text="A级")
        fig.add_hline(y=55, line_dash="dash", line_color="#FFD700", opacity=0.5, annotation_text="B级")
        fig.add_hline(y=40, line_dash="dash", line_color="#FF8C00", opacity=0.5, annotation_text="C级")
        fig.add_hline(y=25, line_dash="dash", line_color="#FF4444", opacity=0.5, annotation_text="D级")

        fig.update_layout(
            title={"text": "评分趋势 (近3个月)", "font": {            "color": ChartComponents.font_color, "size": 18}},
            paper_bgcolor=ChartComponents.paper_bgcolor,
            plot_bgcolor=ChartComponents.paper_bgcolor,
            font={"color": ChartComponents.font_color},
            xaxis={"gridcolor": ChartComponents.grid_color, "showgrid": True, "dtick": "M1", "tickformat": "%m-%d"},
            yaxis={"gridcolor": ChartComponents.grid_color, "showgrid": True, "range": [0, 100]},
            legend={            "bgcolor": ChartComponents.paper_bgcolor, "bordercolor": ChartComponents.grid_color, "borderwidth": 1},
            hovermode="x unified",
            height=400,
            margin={"t": 50, "b": 30, "l": 50, "r": 30},
        )

        return fig

    @staticmethod
    def create_price_chart(df: pd.DataFrame, index_name: str = "指数") -> go.Figure:
        """
        创建K线图

        Args:
            df: DataFrame with columns: date, open, high, low, close
            index_name: 指数名称
        """
        fig = go.Figure()

        # K线图
        fig.add_trace(
            go.Candlestick(
                x=df["date"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name=index_name,
                increasing={"line": {"color": "#00FF88"}, "fillcolor": "#00FF88"},
                decreasing={"line": {"color": "#FF4444"}, "fillcolor": "#FF4444"},
            )
        )

        # 均线
        if "ma_5" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["ma_5"], mode="lines", name="MA5", line={"color": "#FFD700", "width": 1}))
        if "ma_20" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["ma_20"], mode="lines", name="MA20", line={"color": "#00AAFF", "width": 1}))
        if "ma_60" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["ma_60"], mode="lines", name="MA60", line={"color": "#FF8C00", "width": 1}))

        fig.update_layout(
            title={"text": f"{index_name} 价格走势", "font": {            "color": ChartComponents.font_color, "size": 18}},
            paper_bgcolor=ChartComponents.paper_bgcolor,
            plot_bgcolor=ChartComponents.paper_bgcolor,
            font={"color": ChartComponents.font_color},
            xaxis={
                "gridcolor": ChartComponents.grid_color, "showgrid": True,
                "dtick": "M3", "tickformat": "%Y-%m",
                "rangeslider": {"visible": False},
                "type": "date",
            },
            yaxis={"gridcolor": ChartComponents.grid_color, "showgrid": True, "title": "指数点位"},
            legend={            "bgcolor": ChartComponents.paper_bgcolor, "bordercolor": ChartComponents.grid_color},
            hovermode="x unified",
            height=500,
            margin={"t": 50, "b": 30, "l": 60, "r": 30},
        )

        return fig

    @staticmethod
    def create_technical_subplots(df: pd.DataFrame) -> go.Figure:
        """
        创建技术指标四合一子图

        Args:
            df: DataFrame with all indicator columns
        """
        fig = make_subplots(
            rows=4,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=("RSI", "KDJ", "BIAS", "MACD"),
            row_heights=[0.25, 0.25, 0.25, 0.25],
        )

        # RSI
        if "rsi_6" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["rsi_6"], mode="lines", name="RSI(6)", line={"color": "#00FF88"}), row=1, col=1)
        if "rsi_12" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["rsi_12"], mode="lines", name="RSI(12)", line={"color": "#FFD700"}), row=1, col=1)
        if "rsi_24" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["rsi_24"], mode="lines", name="RSI(24)", line={"color": "#FF8C00"}), row=1, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#FF4444", opacity=0.5, row=1, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#00FF88", opacity=0.5, row=1, col=1)

        # KDJ
        if "kdj_k" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["kdj_k"], mode="lines", name="K", line={"color": "#00FF88"}), row=2, col=1)
        if "kdj_d" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["kdj_d"], mode="lines", name="D", line={"color": "#FFD700"}), row=2, col=1)
        if "kdj_j" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["kdj_j"], mode="lines", name="J", line={"color": "#FF8C00"}), row=2, col=1)

        # BIAS
        if "bias_20" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["bias_20"], mode="lines", name="BIAS(20)", line={"color": "#00FF88"}), row=3, col=1)
        if "bias_60" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["bias_60"], mode="lines", name="BIAS(60)", line={"color": "#FFD700"}), row=3, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.3, row=3, col=1)

        # MACD
        if "macd_dif" in df.columns and "macd_dea" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["macd_dif"], mode="lines", name="DIF", line={"color": "#00FF88"}), row=4, col=1)
            fig.add_trace(go.Scatter(x=df["date"], y=df["macd_dea"], mode="lines", name="DEA", line={"color": "#FFD700"}), row=4, col=1)
        if "macd_hist" in df.columns:
            colors = ["#00FF88" if v >= 0 else "#FF4444" for v in df["macd_hist"]]
            fig.add_trace(go.Bar(x=df["date"], y=df["macd_hist"], name="MACD", marker_color=colors), row=4, col=1)

        fig.update_layout(
            title={"text": "技术指标面板", "font": {            "color": ChartComponents.font_color, "size": 18}},
            paper_bgcolor=ChartComponents.paper_bgcolor,
            plot_bgcolor=ChartComponents.paper_bgcolor,
            font={"color": ChartComponents.font_color},
            height=800,
            showlegend=True,
            legend={            "bgcolor": ChartComponents.paper_bgcolor, "bordercolor": ChartComponents.grid_color},
            margin={"t": 50, "b": 30, "l": 50, "r": 30},
        )

        for i in range(1, 5):
            fig.update_xaxes(            gridcolor=ChartComponents.grid_color, row=i, col=1)
            fig.update_yaxes(            gridcolor=ChartComponents.grid_color, row=i, col=1)

        return fig

    @staticmethod
    def create_radar_chart(scores: Dict[str, dict]) -> go.Figure:
        """
        创建雷达图（多因子对比）

        Args:
            scores: {index_key: {"name": str, "technical": float, "valuation": float, ...}}
        """
        categories = ["技术指标", "估值因子", "动量因子", "情绪因子", "资金因子"]

        fig = go.Figure()

        colors = {"kc50": "#00FF88", "zxhl": "#FFD700", "hldb": "#FF8C00"}

        for key, info in scores.items():
            values = [
                info.get("technical", 0),
                info.get("valuation", 0),
                info.get("momentum", 0),
                info.get("sentiment", 0),
                info.get("fundflow", 0),
            ]
            # 闭合图形
            values += values[:1]
            cats = categories + categories[:1]

            # 安全地解析颜色
            color_hex = colors.get(key, "#FFFFFF")
            try:
                r = int(color_hex[1:3], 16)
                g = int(color_hex[3:5], 16)
                b = int(color_hex[5:7], 16)
                fill_color = f"rgba({r}, {g}, {b}, 0.2)"
            except (ValueError, IndexError):
                fill_color = "rgba(255, 255, 255, 0.2)"

            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=cats,
                fill="toself",
                name=info.get("name", key),
                line={"color": color_hex},
                fillcolor=fill_color,
            ))

        fig.update_layout(
            title={"text": "多因子雷达图", "font": {            "color": ChartComponents.font_color, "size": 18}},
            paper_bgcolor=ChartComponents.paper_bgcolor,
            font={"color": ChartComponents.font_color},
            polar={
                "bgcolor": "#1A1C23",
                "radialaxis": {
                    "visible": True,
                    "range": [0, 100],
                    "gridcolor": ChartComponents.grid_color,
                },
                "angularaxis": {
                    "gridcolor": ChartComponents.grid_color,
                },
            },
            height=500,
            margin={"t": 50, "b": 30, "l": 50, "r": 30},
        )

        return fig

    @staticmethod
    def create_allocation_pie(recommendations: List[dict]) -> go.Figure:
        """
        创建资金分配饼图

        Args:
            recommendations: 分配建议列表
        """
        labels = [r["index_key"] for r in recommendations]
        values = [r["amount"] for r in recommendations]
        colors = ["#00FF88", "#FFD700", "#FF8C00"]

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=colors[:len(labels)],
            textinfo="label+percent",
            textfont={"color": ChartComponents.font_color},
        )])

        fig.update_layout(
            title={"text": "资金分配", "font": {            "color": ChartComponents.font_color, "size": 18}},
            paper_bgcolor=ChartComponents.paper_bgcolor,
            font={"color": ChartComponents.font_color},
            height=400,
            showlegend=True,
            legend={            "bgcolor": ChartComponents.paper_bgcolor, "bordercolor": ChartComponents.grid_color},
            margin={"t": 50, "b": 30, "l": 30, "r": 30},
        )

        return fig

    @staticmethod
    def create_portfolio_chart(df_values: pd.DataFrame) -> go.Figure:
        """
        创建组合价值曲线图

        Args:
            df_values: DataFrame with columns: date, value
        """
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_values["date"],
            y=df_values["value"],
            mode="lines",
            name="组合价值",
            line={"color": "#00FF88", "width": 2},
            fill="tozeroy",
            fillcolor="rgba(0, 255, 136, 0.1)",
        ))

        fig.update_layout(
            title={"text": "组合价值走势", "font": {            "color": ChartComponents.font_color, "size": 18}},
            paper_bgcolor=ChartComponents.paper_bgcolor,
            plot_bgcolor=ChartComponents.paper_bgcolor,
            font={"color": ChartComponents.font_color},
            xaxis={"gridcolor": ChartComponents.grid_color, "showgrid": True},
            yaxis={"gridcolor": ChartComponents.grid_color, "showgrid": True},
            height=400,
            margin={"t": 50, "b": 30, "l": 50, "r": 30},
        )

        return fig

    # ==================== 新增：回测可视化图表 ====================

    @staticmethod
    def create_backtest_equity_curve(portfolio_values: List[dict], trades: List[dict] = None) -> go.Figure:
        """
        创建回测权益曲线（组合价值 vs 累计投入）

        Args:
            portfolio_values: 组合价值历史列表
            trades: 交易记录（用于标记买卖点）
        """
        df = pd.DataFrame(portfolio_values)
        if df.empty:
            return go.Figure()

        fig = go.Figure()

        # 组合价值
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["value"],
            mode="lines",
            name="组合价值",
            line={"color": "#00FF88", "width": 2},
            fill="tozeroy",
            fillcolor="rgba(0, 255, 136, 0.1)",
        ))

        # 累计投入
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["invested"],
            mode="lines",
            name="累计投入",
            line={"color": "#888888", "width": 2, "dash": "dash"},
        ))

        # 标记买卖点（简化：只标记前50个避免性能问题）
        if trades and len(trades) > 0:
            trade_df = pd.DataFrame(trades)
            # 限制标记数量
            if len(trade_df) > 50:
                trade_df = trade_df.iloc[::len(trade_df)//50]
            
            for key in trade_df["index_key"].unique():
                key_trades = trade_df[trade_df["index_key"] == key]
                y_values = []
                for d in key_trades["date"]:
                    match = df[df["date"] == d]
                    if len(match) > 0:
                        y_values.append(match["value"].iloc[0])
                    else:
                        y_values.append(None)
                
                fig.add_trace(go.Scatter(
                    x=key_trades["date"],
                    y=y_values,
                    mode="markers",
                    name=f"买入 ({key})",
                    marker={"size": 8, "symbol": "triangle-up", "color": "#FFD700"},
                ))

        fig.update_layout(
            title={"text": "回测权益曲线", "font": {            "color": ChartComponents.font_color, "size": 18}},
            paper_bgcolor=ChartComponents.paper_bgcolor,
            plot_bgcolor=ChartComponents.paper_bgcolor,
            font={"color": ChartComponents.font_color},
            xaxis={"gridcolor": ChartComponents.grid_color, "showgrid": True},
            yaxis={"gridcolor": ChartComponents.grid_color, "showgrid": True},
            height=450,
            legend={            "bgcolor": ChartComponents.paper_bgcolor, "bordercolor": ChartComponents.grid_color},
            margin={"t": 50, "b": 30, "l": 50, "r": 30},
        )

        return fig

    @staticmethod
    def create_drawdown_chart(portfolio_values: List[dict]) -> go.Figure:
        """
        创建回撤图

        Args:
            portfolio_values: 组合价值历史列表
        """
        df = pd.DataFrame(portfolio_values)
        if df.empty or len(df) < 2:
            return go.Figure()
            
        values = df["value"].values

        # 计算回撤
        peak = np.maximum.accumulate(values)
        drawdown = np.where(peak > 0, (peak - values) / peak * 100, 0)

        fig = go.Figure()

        colors = ["#FF4444" if d > 5 else "#FF8C00" if d > 2 else "#00FF88" for d in drawdown]

        fig.add_trace(go.Bar(
            x=df["date"],
            y=drawdown,
            name="回撤",
            marker_color=colors,
            opacity=0.7,
        ))

        fig.add_hline(y=5, line_dash="dash", line_color="#FF8C00", opacity=0.5, annotation_text="5%")
        fig.add_hline(y=10, line_dash="dash", line_color="#FF4444", opacity=0.5, annotation_text="10%")

        fig.update_layout(
            title={"text": "回撤分析", "font": {            "color": ChartComponents.font_color, "size": 18}},
            paper_bgcolor=ChartComponents.paper_bgcolor,
            plot_bgcolor=ChartComponents.paper_bgcolor,
            font={"color": ChartComponents.font_color},
            xaxis={"gridcolor": ChartComponents.grid_color, "showgrid": True},
            yaxis={"gridcolor": ChartComponents.grid_color, "showgrid": True, "title": "回撤 (%)", "range": [0, max(drawdown) * 1.2] if len(drawdown) > 0 else [0, 10]},
            height=350,
            showlegend=False,
            margin={"t": 50, "b": 30, "l": 50, "r": 30},
        )

        return fig

    @staticmethod
    def create_monthly_returns_heatmap(portfolio_values: List[dict]) -> go.Figure:
        """
        创建月度收益热力图

        Args:
            portfolio_values: 组合价值历史列表
        """
        df = pd.DataFrame(portfolio_values)
        if df.empty or len(df) < 2:
            return go.Figure()
            
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

        # 计算月度收益
        monthly = df["value"].resample("ME").last()
        monthly_returns = monthly.pct_change() * 100

        # 创建透视表
        monthly_df = monthly_returns.to_frame("return")
        monthly_df["year"] = monthly_df.index.year
        monthly_df["month"] = monthly_df.index.month

        # 过滤掉只有一个月份的数据
        if len(monthly_df) < 2:
            return go.Figure()

        pivot = monthly_df.pivot(index="year", columns="month", values="return")

        # 月份名称
        month_names = ["1月", "2月", "3月", "4月", "5月", "6月",
                       "7月", "8月", "9月", "10月", "11月", "12月"]

        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=month_names[:len(pivot.columns)],
            y=pivot.index.astype(str),
            colorscale=[
                [0, "#FF4444"],
                [0.25, "#FF8C00"],
                [0.5, "#FFD700"],
                [0.75, "#88FF00"],
                [1, "#00FF88"],
            ],
            zmid=0,
            text=[[f"{v:.2f}%" if not pd.isna(v) else "" for v in row] for row in pivot.values],
            texttemplate="%{text}",
            textfont={"size": 10, "color": ChartComponents.font_color},
            hovertemplate="%{y}年 %{x}: %{z:.2f}%<extra></extra>",
        ))

        fig.update_layout(
            title={"text": "月度收益热力图", "font": {            "color": ChartComponents.font_color, "size": 18}},
            paper_bgcolor=ChartComponents.paper_bgcolor,
            plot_bgcolor=ChartComponents.paper_bgcolor,
            font={"color": ChartComponents.font_color},
            height=350,
            margin={"t": 50, "b": 30, "l": 50, "r": 30},
        )

        return fig

    @staticmethod
    def create_rolling_sharpe(portfolio_values: List[dict], window: int = 12) -> go.Figure:
        """
        创建滚动夏普比率图

        Args:
            portfolio_values: 组合价值历史列表
            window: 滚动窗口（月）
        """
        df = pd.DataFrame(portfolio_values)
        if df.empty or len(df) < 2:
            return go.Figure()
            
        df["date"] = pd.to_datetime(df["date"])

        # 计算月度收益
        df.set_index("date", inplace=True)
        monthly = df["value"].resample("ME").last()
        monthly_returns = monthly.pct_change().dropna()

        if len(monthly_returns) < window:
            return go.Figure()

        # 计算滚动夏普
        rolling_sharpe = monthly_returns.rolling(window=window).apply(
            lambda x: (x.mean() / x.std()) * np.sqrt(12) if x.std() > 0 else 0
        )
        
        # 移除NaN值
        rolling_sharpe = rolling_sharpe.dropna()
        
        if len(rolling_sharpe) == 0:
            return go.Figure()

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=rolling_sharpe.index,
            y=rolling_sharpe.values,
            mode="lines",
            name=f"滚动夏普 ({window}月)",
            line={"color": "#00FF88", "width": 2},
            fill="tozeroy",
            fillcolor="rgba(0, 255, 136, 0.1)",
        ))

        fig.add_hline(y=1, line_dash="dash", line_color="#FFD700", opacity=0.5, annotation_text="良好")
        fig.add_hline(y=2, line_dash="dash", line_color="#00FF88", opacity=0.5, annotation_text="优秀")

        fig.update_layout(
            title={"text": f"滚动夏普比率 ({window}个月)", "font": {            "color": ChartComponents.font_color, "size": 18}},
            paper_bgcolor=ChartComponents.paper_bgcolor,
            plot_bgcolor=ChartComponents.paper_bgcolor,
            font={"color": ChartComponents.font_color},
            xaxis={"gridcolor": ChartComponents.grid_color, "showgrid": True},
            yaxis={"gridcolor": ChartComponents.grid_color, "showgrid": True},
            height=350,
            showlegend=False,
            margin={"t": 50, "b": 30, "l": 50, "r": 30},
        )

        return fig

    @staticmethod
    def create_trade_history_table(trades: List[dict]) -> pd.DataFrame:
        """
        创建交易历史表格

        Args:
            trades: 交易记录列表

        Returns:
            DataFrame: 格式化后的交易记录
        """
        if not trades:
            return pd.DataFrame()

        df = pd.DataFrame(trades)
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["amount"] = df["amount"].round(2)
        df["price"] = df["price"].round(2)
        df["shares"] = df["shares"].round(4)
        df["fee"] = df["fee"].round(2)

        return df[["date", "index_key", "amount", "price", "shares", "fee"]]


if __name__ == "__main__":
    # 测试
    import numpy as np

    dates = pd.date_range("2024-01-01", "2024-01-31", freq="B")
    np.random.seed(42)

    df = pd.DataFrame({
        "date": dates,
        "open": 1000 + np.random.normal(0, 10, len(dates)),
        "high": 1010 + np.random.normal(0, 10, len(dates)),
        "low": 990 + np.random.normal(0, 10, len(dates)),
        "close": 1000 + np.cumsum(np.random.normal(0, 5, len(dates))),
    })

    chart = ChartComponents.create_price_chart(df, "测试指数")
    chart.show()
