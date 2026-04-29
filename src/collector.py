import ccxt
import pandas as pd
import time
import sqlite3
import os

def fetch_historical_data(symbol='BTC/USDT', timeframe='1m', total_limit=3600, sleep_time=0.5):
    exchange = ccxt.okx()
    all_data = []

    # 获取当前时间（毫秒）
    current_time = exchange.milliseconds()
    # 每一根K线是1分钟 = 60000毫秒
    # 3600条数据总跨度 = 3600 * 60000
    target_start_time = current_time - (total_limit * 60000)

    print(f"开始抓取 {symbol} 历史数据...")

    # 从目标时间点开始，每次抓100条，直到获取足够数据
    since = target_start_time

    while len(all_data) < total_limit:
        # 抓取数据
        bars = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=100)

        if not bars:
            print("获取完毕或无数据。")
            break

        all_data.extend(bars)

        # 更新 since 为本次获取到的最后一条数据的时间戳 + 1ms
        # 防止无限循环，并确保下一次从更靠后的时间开始
        since = bars[-1][0] + 60000

        print(f"已获取: {len(all_data)} / {total_limit} 条数据...")
        time.sleep(sleep_time)

        # 边界条件：如果抓取到的最后一条数据已经接近当前时间，跳出
        if bars[-1][0] >= current_time:
            break

    # 只取前 3600 条（防止多抓）
    all_data = all_data[:total_limit]

    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def save_to_db(df, db_name='data/market_data.sqlite3'):
    os.makedirs('data', exist_ok=True)
    with sqlite3.connect(db_name) as conn:
        df.to_sql('btc_1m', conn, if_exists='replace', index=False)
    print(f"数据库已更新，共 {len(df)} 条记录。")

if __name__ == "__main__":
    df = fetch_historical_data(total_limit=3600, sleep_time=0.5)
    save_to_db(df)
