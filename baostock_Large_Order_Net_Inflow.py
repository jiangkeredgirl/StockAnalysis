import baostock as bs
import pandas as pd
from datetime import datetime, timedelta

# 股票：金龙羽 002882
code = "sz.002882"

# 自动取最近 30 天
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

# 登录
bs.login()

# 获取数据
rs = bs.query_history_k_data_plus(
    code=code,
    fields="date,close,volume,amount",
    start_date=start_date,
    end_date=end_date,
    frequency="d"
)

# 转换数据
data_list = []
while (rs.error_code == '0') & rs.next():
    data_list.append(rs.get_row_data())

df = pd.DataFrame(data_list, columns=rs.fields)

# 安全转换为数字（修复报错）
df["close"] = pd.to_numeric(df["close"])
df["volume"] = pd.to_numeric(df["volume"])
df["amount"] = pd.to_numeric(df["amount"])

# 计算大单净量
df["avg_amount"] = df["amount"] / df["volume"]
threshold = df["avg_amount"].median()
df["大单净量"] = df["volume"] * (df["avg_amount"] > threshold) / 10000

# 输出
print("=" * 70)
print("📊 金龙羽(002882) 近一个月 大单净量")
print("日期        收盘价  成交量  大单净量(万手)")
print("-" * 70)

for i, row in df.iterrows():
    print(f"{row['date']}   {row['close']:>6.2f}   {int(row['volume']/100):>5}   {row['大单净量']:>10.2f}")

print("-" * 70)
print(f"✅ 近一个月大单净量总计：{df['大单净量'].sum():.2f} 万手")

bs.logout()