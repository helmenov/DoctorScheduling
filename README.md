# 当直管理システム

## 手順？

0. オーダー集め
   - 各病院からオーダー: 日付と時間帯と人数 (ex [order_h01.csv](order_h01.csv))

      |date|time       |N|
      |---|---|---|
      |1   |10:00-18:00|3|

   - 各医師からオーダー: NG日とNG時間帯 (ex [doctor_d01.csv](doctor_d01.csv))

      |date|time       |
      |---|---|
      |1   |10:00-18:00|

1. 集計

   - [orders.csv](orders.csv) : order_hnnを集計したもの

      |#order|hospital|weekend|holiday|start-date-time    |end-date-time      |
      |---   |---     |---|---|---                |---                |
      |0     |A       |1|0|2024-03-01T10:00:00|2024-03-01T18:00:00|
      |1     |A       |1|0|2024-03-01T10:00:00|2024-03-01T18:00:00|
      |2     |A       |1|0|2024-03-01T10:00:00|2024-03-01T18:00:00|
      |3     |B       |1|0|2024-03-01T10:00:00|2024-03-01T18:00:00|

   - [doctor.csv](doctors.csv) : doctor_dnnを集計したもの

      |#NG   |doctor  |start-date-time    |end-date-time      |
      |---   |---     |---                |---                |
      |0     |a       |2024-03-01T10:00:00|2024-03-01T18:00:00|
      |1     |b       |2024-03-01T10:00:00|2024-03-01T18:00:00|
      |2     |c       |2024-03-01T10:00:00|2024-03-01T18:00:00|
      |3     |d       |2024-03-01T10:00:00|2024-03-01T18:00:00|

2. 条件に沿うよう医師を配置

   - 条件

      1. 休日配置（各医師は最大1回）
      2. 平日配置

   - 配置された休日と同じ週には配置しない
   - 連続日配置はしない

## 手作業

1．休日の配置

   休日のオーダー1件ごとについて，各医師について，NG時間帯にオーダー時間帯が被らない医師を選ぶ．選ばれた医師のNGリストに
   - start-date-time
   - end_date_time + 1week
   を加える．

   ```{.py}
   wh_orders = df_orders[df_orders['weekend'] OR df_orders['holiday']]
   for o in wh_orders:
      o_s = o['start-date-time']
      o_e = o['end-date-time']
      for d in df_doctors:
        d
   ```

2.
