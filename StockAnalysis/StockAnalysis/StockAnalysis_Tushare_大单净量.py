# coding: utf-8
import tushare as ts
import pandas as pd
import datetime
import time

ts.set_token('532a922509bf767b8a5ac2571fc4882b7b9e878a3d1a7999d97f9e3c')
pro = ts.pro_api()

# large order threshold in shares (default 300000 = 30w shares), configurable
LARGE_ORDER_SHARES = 300000


def get_recent_trade_dates(n):
    end_date = datetime.datetime.now().strftime('%Y%m%d')
    start_date = (datetime.datetime.now() - datetime.timedelta(days=n * 4)).strftime('%Y%m%d')
    cal = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date, is_open='1')
    return cal['cal_date'].sort_values(ascending=False).head(n).tolist()


def query_large_order_net_ratio(ts_code, name, days, large_order_shares=LARGE_ORDER_SHARES):
    """
    Query large order net ratio for recent N days.

    Formula:
        net_ratio(%) = (large_buy_shares - large_sell_shares) / float_shares * 100

    Args:
        ts_code            : stock code e.g. '002882.SZ', empty string = all stocks
        name               : display name
        days               : number of recent trading days
        large_order_shares : large order threshold in shares (default 300000 = 30w)

    Note:
        tushare moneyflow groups by amount (elg>=100w yuan, lg=20~100w yuan).
        elg + lg combined volume is used as the large order approximation.
        1 lot = 100 shares; moneyflow vol unit is lot, converted to shares here.
    """
    trade_dates = get_recent_trade_dates(days)
    print('trade dates:', trade_dates)

    mf_list = []
    for td in trade_dates:
        kw = dict(
            trade_date=td,
            fields='trade_date,ts_code,buy_elg_vol,sell_elg_vol,buy_lg_vol,sell_lg_vol'
        )
        if ts_code:
            kw['ts_code'] = ts_code
        df = pro.moneyflow(**kw)
        if df is not None and not df.empty:
            mf_list.append(df)
        time.sleep(0.5)

    if not mf_list:
        print('no moneyflow data')
        return None

    data = pd.concat(mf_list, ignore_index=True)

    # convert lot -> shares, combine elg + lg as large order
    data['buy_shares']  = (data['buy_elg_vol']  + data['buy_lg_vol'])  * 100
    data['sell_shares'] = (data['sell_elg_vol'] + data['sell_lg_vol']) * 100
    data['net_shares']  = data['buy_shares'] - data['sell_shares']

    start = min(trade_dates)
    end   = max(trade_dates)
    bk = dict(start_date=start, end_date=end, fields='trade_date,ts_code,float_share')
    if ts_code:
        bk['ts_code'] = ts_code
    basic = pro.daily_basic(**bk)
    time.sleep(0.5)

    if basic is not None and not basic.empty:
        basic['float_shares'] = basic['float_share'] * 10000   # 10k shares -> shares
        data = data.merge(
            basic[['trade_date', 'ts_code', 'float_shares']],
            on=['trade_date', 'ts_code'], how='left'
        )
        data['net_ratio'] = (data['net_shares'] / data['float_shares'] * 100).round(4)
    else:
        data['net_ratio'] = None

    result = data[['trade_date', 'ts_code', 'buy_shares', 'sell_shares', 'net_shares', 'net_ratio']]
    result = result.sort_values(['ts_code', 'trade_date'], ascending=[True, False]).reset_index(drop=True)

    label = name if name else 'all stocks'
    threshold_w = large_order_shares // 10000
    print('\n=== ' + label + ' last ' + str(days) + ' days'
          ' | large order >= ' + str(threshold_w) + 'w shares ===')
    print(result.rename(columns={
        'trade_date' : 'Date',
        'ts_code'    : 'Code',
        'buy_shares' : 'Buy(shares)',
        'sell_shares': 'Sell(shares)',
        'net_shares' : 'Net(shares)',
        'net_ratio'  : 'NetRatio(%)',
    }).to_string(index=False))
    print('note: NetRatio(%) = (large_buy - large_sell) / float_shares * 100')
    print('      large order = elg(>=100w yuan) + lg(20~100w yuan), threshold: '
          + str(large_order_shares) + ' shares')
    return result


if __name__ == '__main__':
    # single stock
    query_large_order_net_ratio('002882.SZ', 'JinLongYu', 5, large_order_shares=100000)

    # all stocks (may be slow, requires sufficient tushare points)
    # query_large_order_net_ratio('', '', 5)
