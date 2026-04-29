import sqlite3
import pandas as pd
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import argparse

def run_analysis(db_name='data/market_data.sqlite3', threshold=10.0, stability=45.0, window=11):
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
    is_abnormal = df['volume'] > threshold
    is_stable = (df['delta'].abs() <= stability) & (df['delta2'] <= stability)

    entry_signal = [False] * len(df)

    consecutive_normal_minutes = 0 # 记录连续平稳的分钟数
    is_locked = False              # 是否处于锁定状态

    for i in range(len(df)):
        # 如果当前发生了异常 (放量)
        if is_abnormal.iloc[i]:
            # 如果没被锁定且满足波动稳定性，触发信号并加锁
            if not is_locked and is_stable.iloc[i]:
                entry_signal[i] = True
                is_locked = True
                consecutive_normal_minutes = 0
            else:
                # 即使没触发信号，只要有异常，平稳计数器就重置
                consecutive_normal_minutes = 0
        else:
            # 只有成交量平稳时，才累加平稳分钟数
            consecutive_normal_minutes += 1
            # 当平稳分钟数达到 window，解锁，允许下一次触发
            if consecutive_normal_minutes >= window:
                is_locked = False

    df['entry_signal'] = entry_signal
    signals = df[df['entry_signal']]
    # ------------------------------------

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

    # 7. 布局配置
    fig.update_layout(
        title_text=f'Signals: Vol>{threshold}, Body/Range<={stability}, CoolingWindow={window}m',
        hovermode='x',
        xaxis=dict(rangeslider=dict(visible=True), type="date", showspikes=True, spikemode='across', spikecolor='grey'),
        height=800, showlegend=False, template='plotly_white'
    )

    fig.show(config={'scrollZoom': True})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--threshold', type=float, default=10.0, help="成交量异常阈值")
    parser.add_argument('--stability', type=float, default=45.0, help="波动过滤阈值")
    parser.add_argument('--window', type=int, default=11, help="需要连续平稳的分钟数(冷却期)")
    parser.add_argument('--db', type=str, default='data/market_data.sqlite3', help="数据库路径")

    args = parser.parse_args()
    run_analysis(db_name=args.db, threshold=args.threshold, stability=args.stability, window=args.window)
