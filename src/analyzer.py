import sqlite3
import pandas as pd
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def run_analysis(db_name='data/market_data.sqlite3'):
    if not os.path.exists(db_name):
        raise FileNotFoundError(f"Database not found: {db_name}")

    # 1. 加载并规范化数据
    with sqlite3.connect(db_name) as conn:
        df = pd.read_sql("SELECT * FROM btc_1m ORDER BY timestamp ASC", conn)

    # 确保时间戳是 datetime 类型，这是 Plotly 正确渲染时间轴的关键
    # 如果你的 timestamp 存的是 Unix 毫秒，用 unit='ms'；如果是字符串，去掉 unit 参数
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 2. 创建子图
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03,
                        subplot_titles=('BTC/USDT 1m', 'Volume'),
                        row_width=[0.3, 0.7])

    # 3. 绘制 K 线图
    # 增加计算：Price Change = Close - Open
    # 在 hovertemplate 中使用 %{customdata} 无法直接做减法，
    # 我们最好在 df 中预先计算好 delta 列，作为 customdata 传入
    df['delta'] = df['close'] - df['open']

    # 将 volume 和 delta 都放入 customdata 中 (注意 customdata 必须是二维数组或者 DataFrame 转换)
    # 为了方便，我们直接把 volume 和 delta 拼成列表传给 customdata
    custom_data = df[['volume', 'delta']].values

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
                                               '<b>Delta: %{customdata[1]:+.3f}</b><br>' + # 显示差值，带正负号
                                               '<b>Volume: %{customdata[0]:.3f}</b><extra></extra>'),
                  row=1, col=1)

    # 4. 绘制成交量柱状图
    colors = ['green' if row['close'] >= row['open'] else 'red' for _, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df['timestamp'], y=df['volume'],
                         name='Volume', marker_color=colors), row=2, col=1)

    # 5. 布局美化与交互配置
    fig.update_layout(
        title_text='Kotaku Algo Ledger - Full 3600 Data View',
        hovermode='x',  # 关键：改为 'x'，强制垂直线联动
        xaxis=dict(
            rangeslider=dict(visible=True),
            type="date",
            showspikes=True,
            spikemode='across',
            spikesnap='cursor',
            spikecolor='grey',
            spikethickness=1,
            spikedash='dash'
        ),
        # 下方配置允许成交量图也响应鼠标悬停
        xaxis2=dict(
            showspikes=True,
            spikemode='across',
            spikesnap='cursor',
            spikecolor='grey',
            spikethickness=1,
            spikedash='dash'
        ),
        yaxis=dict(title='Price'),
        yaxis2=dict(title='Volume'),
        height=800,
        showlegend=False,
        template='plotly_white'
    )

    # 6. 显示图表，config 允许鼠标滚轮自由缩放
    fig.show(config={'scrollZoom': True})

if __name__ == "__main__":
    run_analysis()
