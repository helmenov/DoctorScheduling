---
title: Doctor Scheduling
author: Kotaro Sonoda <kotaro@nagasaki-u.ac.jp>
---

## 依頼された条件

- 基本的には平日2回、休日2回の体制です。
- 本人の体力的な問題や先月、先々月の当直不足分の補充で回数が1〜3回と前後することがあります。
- 医師年数の高い医師から順位づけで当直先が大方決まっています。
- 同じ病院への当直は週に1回まで、土日の日当直は1回までが基本です。
- 表に緑で記載している部分はその医師の外勤となります。am勤務では前日の当直、pm勤務では当日の勤務を考慮しなくてはなりません。
- 当直は連日、隔日とならないように可能な限り調整しています。どうしても難しい場合には医師年数の低い医師から隔日になっても良いか打診して調整を行っています。
- オレンジの枠は要相談枠として設けたものになります。システム作成の際には考慮しなくても良いかと思われます。
- 枠の右側にそれぞれの医師の外勤の情報や当てない病院などの条件を記載した欄があります。

## 集合・定数・変数

### 集合

- 医師：$dr \in\mathscr(Dr)$, `Dr = [f'dr{dr:0d}' for dr in range(N_dr)]`
- 病院：$h \in\mathscr(H)$, `H = [f'h{h:0d}' for h in range(N_h)]`
- 日付: $day \in\mathscr{Day}$, `Day = list(range(1,32))`
  - 平日の集合はDw, 土日祝の集合はDh

### 定数

- 医師 $dr$ の 希望休暇日の辞書 `r_d = {'dr01':[1, 3], 'dr02':[], 'dr03':[3,6], ...}`
- 病院 $h$ の 希望当直日の辞書 `b_h = {'h01':[1,2,3], 'h02':[4,5], ...}`
- 医師 $dr$ の 希望平日当直数の辞書 `w_d= {'dr01':2, 'dr02':2, ...}`
- 医師 $dr$ の 希望土日祝当直数の辞書 `h_d = {'dr01':2, 'dr02':3, ...}`

### 変数

- 当直リスト `X_{dr,h,day} \in \pmb{B}`, 0:休み 1:出勤

## 目的および制約

- 医師の希望休暇日を守る（制約）

  ```{python}
  for dr in Dr:
    for day in r_d[dr]:
        model += pulp.lpSum(X[dr,h,day] for h in H) == 0
  ```

- 病院の希望当直日を守る（制約）
   希望当直日以外は配置しない

  ```{python}
  for h in H:
    for day in Day:
      if day in b_h[h]:
          model += pulp.lpSum(X[dr,h,day] for dr in Dr) == 1
      else:
          model += pulp.lpSum(X[dr,h,day] for dr in Dr) == 0
  ```

- 同じ病院への当直は週に1回まで（不等式制約）

  ```{python}
  for dr in Dr:
    for h in H:
      for day in Day[:-5]:
        model += pulp.lpSum(X[dr,h,day+d] for d in range(5)) <= 1
  ```

- 連日・隔日勤務NG（制約）

  ```{python}
  for dr in Dr:
    for day in Day[:-1]:
      model += pulp.lpSum(X[dr,h,day]+X[dr,h,day+1] for h in H) <= 1
    for day in Day[:-2]:
      model += pulp.lpSum(X[dr,h,day]+X[dr,h,day+2] for h in H) <= 1
  ```

- 月に平日勤務2回，土日祝勤務2回（制約？）

  日付dayが平日か土日祝なのかを判断する関数をisBizDay(day)とする．

  ```{python}
  Day_biz = Day[isBizDay(Day)]
  Day_hol = Day[~isBizDay(Day)]
  for dr in Dr:
    model += pulp.lpSum(X[dr,h,day] for h in H for day in Day_biz) == w_d[dr]
    model += pulp.lpSum(X[dr,h,day] for h in H for day in Day_hol) == h_d[dr]
  ```
