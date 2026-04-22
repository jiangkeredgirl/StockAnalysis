# -*- coding: utf-8 -*-
import tushare as ts
import datetime
import pandas as pd
import time

ts.set_token('532a922509bf767b8a5ac2571fc4882b7b9e878a3d1a7999d97f9e3c')
pro = ts.pro_api()

# 大单定义：单日大单净买入量 >= 20万手
# tushare moneyflow 接口按金额分档（超大单>=100万元，大单20~100万元）
# 将超大单(elg)+大单(lg)合并作为大单成交量统计
LARGE_VOL_THRESHOLD = 200000  # 大单阈值：20万手


def get_recent_trade_dates(n=6):
    end_date = datetime.datetime.now().strftime('%Y%m%d')
    start_date = (datetime.datetime.now() - datetime.timedelta(days=n * 4)).strftime('%Y%m%d')
    cal = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date, is_open='1')
    return cal['cal_date'].sort_values(ascending=False).head(n).tolist()


def get_large_order_net(ts_code, stock_name, trade_dates):
    """
    大单净量功能:
      大单定义   = 单笔成交量 >= 30万股(3000手)，用 moneyflow 超大单+大单成交量近似
      大单净量   = 大单买入量(手) - 大单卖出量(手)
      大单净量比 = 大单净量(手) / 流通股本(手) * 100%
    """
    mf_list = []
    for td in trade_dates:
        print(f'  获取 {td} 资金流向数据...')
        df = pro.moneyflow(ts_code=ts_code, trade_date=td,
                           fields='trade_date,ts_code,'
                                  'buy_sm_amount,sell_sm_amount,'
                                  'buy_md_amount,sell_md_amount,'
                                  'buy_lg_vol,sell_lg_vol,buy_lg_amount,sell_lg_amount,'
                                  'buy_elg_vol,sell_elg_vol,buy_elg_amount,sell_elg_amount')
        if df is not None and not df.empty:
            mf_list.append(df)
        time.sleep(0.5)

    if not mf_list:
        print(f'  未获取到数据，请确认 tushare 积分是否满足 moneyflow 接口要求（需2000+积分）。')
        return

    data = pd.concat(mf_list, ignore_index=True)

    # 超大单 + 大单合并（近似 >= 30万股的大单）
    data['big_buy_vol']    = data['buy_elg_vol']    + data['buy_lg_vol']
    data['big_sell_vol']   = data['sell_elg_vol']   + data['sell_lg_vol']
    data['big_buy_amount'] = data['buy_elg_amount'] + data['buy_lg_amount']
    data['big_sell_amount']= data['sell_elg_amount']+ data['sell_lg_amount']
    data['net_lg_vol']     = data['big_buy_vol']    - data['big_sell_vol']

    # 总成交额 = 所有级别买入+卖出金额之和
    data['total_amount'] = (data['buy_sm_amount']  + data['sell_sm_amount'] +
                            data['buy_md_amount']  + data['sell_md_amount'] +
                            data['big_buy_amount'] + data['big_sell_amount'])

    # 大单净量占比 = (大单买入额 - 大单卖出额) / 总成交额 * 100
    data['buy_lg_amount_rate']  = (data['big_buy_amount']  / data['total_amount'] * 100).round(4)
    data['sell_lg_amount_rate'] = (data['big_sell_amount'] / data['total_amount'] * 100).round(4)
    data['net_lg_amount_rate']  = (data['buy_lg_amount_rate'] - data['sell_lg_amount_rate']).round(4)

    data = data[['trade_date', 'ts_code', 'big_buy_vol', 'big_sell_vol', 'net_lg_vol',
                 'buy_lg_amount_rate', 'sell_lg_amount_rate', 'net_lg_amount_rate']]
    data = data.sort_values('trade_date', ascending=False).reset_index(drop=True)

    # 标注是否达到大单标准（大单买入量 >= 20万手）
    data['是否大单日'] = data['big_buy_vol'].apply(lambda v: '是' if v >= LARGE_VOL_THRESHOLD else '否')

    print(f'\n{stock_name}（{ts_code}）最近{len(data)}个交易日大单净量:')
    print(data.rename(columns={
        'trade_date':           '交易日',
        'ts_code':              '代码',
        'big_buy_vol':          '大单买入(手)',
        'big_sell_vol':         '大单卖出(手)',
        'net_lg_vol':           '大单净量(手)',
        'buy_lg_amount_rate':   '大单买入占比(%)',
        'sell_lg_amount_rate':  '大单卖出占比(%)',
        'net_lg_amount_rate':   '大单净量占比(%)',
    }).to_string(index=False))
    print(f'说明: 大单=当日大单买入量>={LARGE_VOL_THRESHOLD//10000}万手  净量占比(%)=(大单买入额-大单卖出额)/总成交额*100\n')


if __name__ == '__main__':
    trade_dates = get_recent_trade_dates(n=6)
    print(f'最近6个交易日: {trade_dates}\n')

    stocks = [
        ('002882.SZ', '金龙羽'),
    ]

    for ts_code, stock_name in stocks:
        print(f'>>> 查询 {stock_name}（{ts_code}）')
        get_large_order_net(ts_code, stock_name, trade_dates)
