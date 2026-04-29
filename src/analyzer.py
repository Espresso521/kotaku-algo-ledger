import sqlite3
import pandas as pd
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import argparse

def run_analysis(db_name='data/market_data.sqlite3', threshold=9.0, stability=30.0, window=10):
    if not os.path.exists(db_name):
        raise FileNotFoundError(f"Database not found: {db_name}")

    # 1. 加载数据
    with sqlite3.connect(db_name) as conn:
        df = pd.read_sql("SELECT * FROM btc_1m ORDER BY timestamp ASC", conn)

    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 2. 计算指标
    df['delta'] = df['close'] - df['open']
    df['delta2'] = df['high'] - df['low']

    # --- 核心改进：强制冷却/平稳计数逻辑 ---
    # 定义异常状态和稳定状态
    # A. 异常放量 (当前分钟)
    df['is_abnormal'] = df['volume'] > threshold

    # B. 回溯检查 (过去 window 分钟必须都 <= threshold)
    # 只要这层在，任何“过早解锁”引发的信号如果前面 10 分钟不干净，都会被拦截
    df['previous_normal'] = df['volume'].shift(1).rolling(window=window).max() <= threshold
    df['previous_normal'] = df['previous_normal'].fillna(True)

    # C. 稳定性过滤
    df['is_stable'] = (df['delta'].abs() <= stability)

    # D. 频率控制与出场逻辑
    entry_signal = [False] * len(df)
    exit_signal = [False] * len(df)

    # 调整变量以存储入场时间
    in_position = False
    entry_price = 0.0
    entry_index = -1000  # 新增：记录入场时的索引位置
    last_signal_idx = -1000
    STOP_LOSS_LIMIT = 100.0

    for i in range(len(df)):
        # 1. 寻找入场
        if not in_position:
            if (df['is_abnormal'].iloc[i] and
                df['previous_normal'].iloc[i] and
                df['is_stable'].iloc[i] and
                (i - last_signal_idx >= window)):

                entry_signal[i] = True
                in_position = True
                entry_price = df['close'].iloc[i]
                entry_index = i      # 记录入场索引
                last_signal_idx = i

        # 2. 监控出场
        else:
            # 条件 A：止损 (无时间限制，随时止损)
            is_stop_loss = abs(df['close'].iloc[i] - entry_price) >= STOP_LOSS_LIMIT

            # 条件 B：量能变盘出场 (必须在入场 5 分钟之后才生效)
            is_volume_exit = df['is_abnormal'].iloc[i] and (i - entry_index >= 5)

            if is_stop_loss or is_volume_exit:
                exit_signal[i] = True
                in_position = False
                entry_price = 0.0
                entry_index = -1000

    df['entry_signal'] = entry_signal
    df['exit_signal'] = exit_signal
    signals = df[df['entry_signal']]
    exits = df[df['exit_signal']]

    # 3. 创建子图
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03,
                        subplot_titles=('BTC/USDT 1m', 'Volume'),
                        row_width=[0.3, 0.7])

    # 4. 绘制 K 线图
    custom_data = df[['volume', 'delta', 'delta2']].values
    fig.add_trace(go.Candlestick(x=df['timestamp'],
                                 open=df['open'], high=df['high'],
                                 low=df['low'], close=df['close'],
                                 name='Price',
                                 customdata=custom_data,
                                 hovertemplate='<b>%{x}</b><br>' +
                                               'Open: %{open:.2f}<br>' +
                                               'High: %{high:.2f}<br>' +
                                               'Low: %{low:.2f}<br>' +
                                               'Close: %{close:.2f}<br>' +
                                               'Delta: %{customdata[1]:+.3f}<br>' +
                                               'Delta2: %{customdata[2]:.3f}<br>' +
                                               'Volume: %{customdata[0]:.3f}<extra></extra>'),
                  row=1, col=1)

    # 5. 绘制成交量图
    colors = ['green' if r >= o else 'red' for r, o in zip(df['close'], df['open'])]
    fig.add_trace(go.Bar(x=df['timestamp'], y=df['volume'], marker_color=colors), row=2, col=1)

    # 6. 绘制信号箭头
    fig.add_trace(go.Scatter(
        x=signals['timestamp'],
        y=signals['high'] * 1.0005,
        mode='markers',
        name='Entry Signal',
        hoverinfo='skip',
        hoveron=None,
        marker=dict(symbol='arrow-down', color='#FFD700', size=12, line=dict(color='black', width=1))
    ), row=1, col=1)

    # 7. 绘制出场信号箭头 (红色)
    fig.add_trace(go.Scatter(
        x=exits['timestamp'],
        y=exits['low'] * 0.9995,  # 放在K线下方
        mode='markers',
        name='Exit Signal',
        hoverinfo='skip',
        marker=dict(symbol='arrow-up', color='#FF4500', size=12, line=dict(color='black', width=1))
    ), row=1, col=1)

    # 8. 布局配置
    fig.update_layout(
        title_text=f'Signals: Vol>{threshold}, Body/Range<={stability}, CoolingWindow={window}m',
        hovermode='x',
        xaxis=dict(rangeslider=dict(visible=True), type="date", showspikes=True, spikemode='across', spikecolor='grey'),
        height=800, showlegend=False, template='plotly_white'
    )

    fig.show(config={'scrollZoom': True})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--threshold', type=float, default=9.0, help="成交量异常阈值")
    parser.add_argument('--stability', type=float, default=30.0, help="波动过滤阈值")
    parser.add_argument('--window', type=int, default=10, help="需要连续平稳的分钟数(冷却期)")
    parser.add_argument('--db', type=str, default='data/market_data.sqlite3', help="数据库路径")

    args = parser.parse_args()
    run_analysis(db_name=args.db, threshold=args.threshold, stability=args.stability, window=args.window)
