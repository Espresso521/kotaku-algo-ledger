import ccxt
import pandas as pd
import time
import sqlite3
import os
import argparse

def fetch_historical_data(symbol='BTC/USDT', timeframe='1m', total_limit=10080, sleep_time=1):
    exchange = ccxt.okx()
    all_data = []

    # 计算目标起始时间
    current_time = exchange.milliseconds()
    target_start_time = current_time - (total_limit * 60000)

    print(f"开始抓取过去一周 ({total_limit} 条) 的 {symbol} 数据...")

    since = target_start_time

    while len(all_data) < total_limit:
        try:
            # 每次抓 100 条
            bars = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=100)

            if not bars:
                print("已达到数据源极限。")
                break

            all_data.extend(bars)
            since = bars[-1][0] + 60000

            print(f"进度: {len(all_data)} / {total_limit}...")
            time.sleep(sleep_time)

            if bars[-1][0] >= current_time:
                break
        except Exception as e:
            print(f"请求失败: {e}，暂停 5 秒后重试...")
            time.sleep(5)

    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def save_to_db(df, db_name='data/market_data.sqlite3'):
    os.makedirs('data', exist_ok=True)
    with sqlite3.connect(db_name) as conn:
        df.to_sql('btc_1m', conn, if_exists='replace', index=False)
    print(f"数据库更新完毕，共 {len(df)} 条数据。")

def main():
    parser = argparse.ArgumentParser(description="Kotaku Algo Ledger - 数据采集器")
    parser.add_argument('--limit', type=int, default=3600, help="需要抓取的 K 线数量")
    parser.add_argument('--symbol', type=str, default='BTC/USDT', help="交易对名称")
    parser.add_argument('--db', type=str, default='data/market_data.sqlite3', help="数据库路径")
    parser.add_argument('--sleep', type=float, default=0.5, help="请求间隔秒数")

    args = parser.parse_args()

    print(f"参数已确认: 抓取 {args.symbol}, 共 {args.limit} 条...")

    df = fetch_historical_data(symbol=args.symbol, total_limit=args.limit, sleep_time=args.sleep)
    save_to_db(df, db_name=args.db)

if __name__ == "__main__":
    main()
