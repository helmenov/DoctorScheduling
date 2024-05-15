import pulp
from tool import isBizDay

class ShiftModel():
   def __init__(self,Doctors:list[str],Hospitals:list[str],Days:list[int],rests_dr:dict,jobs_hos:dict,Nj_dr:dict):
      # Sets
      self.Doctors = Doctors
      self.Hospitals = Hospitals
      self.Days = Days
      # Constants
      self.rests_dr = rests_dr
      self.jobs_hos = jobs_hos
      self.Nj_dr = Nj_dr
      # Variables
      self.X = None

      # Model
      self.model = None

      # Status
      self.status = None

   def modeling(self):
      DrHosDay = [(dr,h,day) for dr in self.Doctors for h in self.Hospitals for day in self.Days]
      X = pulp.LpVariable.dicts("X", DrHosDay, cat="Binary")

      model = pulp.LpProblem("DoctorAttendingProblem", pulp.LpMinimize)

      # 制約
      ## 医師の希望休暇日を守る（制約）
      for dr in self.Doctors:
         for day in self.rests_dr[dr]:
            model += pulp.lpSum([X[dr,h,day] for h in self.Hospitals]) == 0


      ## 病院の希望当直日を守る（制約）
      ### 希望当直日以外は配置しない
      for h in self.Hospitals:
         for day in self.Days:
            if day in self.jobs_hos[h]:
                  model += pulp.lpSum([X[dr,h,day] for dr in self.Doctors]) == 1
            else:
                  model += pulp.lpSum([X[dr,h,day] for dr in self.Doctors]) == 0


      ## 同じ病院への当直は週に1回まで（不等式制約）
      for dr in self.Doctors:
         for h in self.Hospitals:
            for day in self.Days[:-5]:
               model += pulp.lpSum([X[dr,h,day+d] for d in range(5)]) <= 1


      ## 連日・隔日勤務NG（制約）
      for dr in self.Doctors:
         for day in self.Days[:-1]:
            model += pulp.lpSum([X[dr,h,day]+X[dr,h,day+1] for h in self.Hospitals]) <= 1
         for day in self.Days[:-2]:
            model += pulp.lpSum([X[dr,h,day]+X[dr,h,day+2] for h in self.Hospitals]) <= 1


      ## 月に平日勤務2回，土日祝勤務2回（制約？）
      ### 日付dayが平日か土日祝なのかを判断する関数をisBizDay(day)とする．

      Day_biz = [d for d in self.Days if isBizDay(f'202405{d:02d}')]
      Day_hol = [d for d in self.Days if not isBizDay(f'202405{d:02d}')]
      for dr in self.Doctors:
         model += self.Nj_dr[dr][0] - pulp.lpSum([X[dr,h,day] for h in self.Hospitals for day in Day_biz])
         model += self.Nj_dr[dr][1] - pulp.lpSum([X[dr,h,day] for h in self.Hospitals for day in Day_hol])
         model += self.Nj_dr[dr][0] - pulp.lpSum([X[dr,h,day] for h in self.Hospitals for day in Day_biz]) <= 1
         model += self.Nj_dr[dr][1] - pulp.lpSum([X[dr,h,day] for h in self.Hospitals for day in Day_hol]) <= 1
         model += self.Nj_dr[dr][0] - pulp.lpSum([X[dr,h,day] for h in self.Hospitals for day in Day_biz]) >= -1
         model += self.Nj_dr[dr][1] - pulp.lpSum([X[dr,h,day] for h in self.Hospitals for day in Day_hol]) >= -1
         model += pulp.lpSum([X[dr,h,day] for h in self.Hospitals for day in Day_biz]) <=3
         model += pulp.lpSum([X[dr,h,day] for h in self.Hospitals for day in Day_hol]) <=3


      ## 各医師は，各日，1箇所にしか存在しない．
      for day in self.Days:
         for dr in self.Doctors:
            model += pulp.lpSum([X[dr,h,day] for h in self.Hospitals]) <= 1
         for h in self.Hospitals:
            model += pulp.lpSum([X[dr,h,day] for dr in self.Doctors]) <= 1

      # modeling
      self.X = X
      self.model = model

   def print(self):
      print(self.model)

   def solve(self):
      self.status = self.model.solve()
      print(f"Status: {pulp.LpStatus[self.status]}")

   def get_results(self):
      import pandas as pd

      print(f'Objective: {self.model.objective.value()}')
      dr_on_hos = list()
      for h in self.Hospitals:
         hos_ = list()
         for day in self.Days:
            s = np.array([self.X[dr,h,day].value() for dr in self.Doctors])
            l = np.where(s==1)[0]
            if len(l):
               dr_l = [self.Doctors[i] for i in l]
               hos_.append(dr_l)
            else:
               hos_.append('x')
         dr_on_hos.append(hos_)

      hos_on_dr = list()
      for dr in self.Doctors:
         dr_ = list()
         for day in self.Days:
            s = np.array([self.X[dr,h,day].value() for h in self.Hospitals])
            l = np.where(s==1)[0]
            if len(l):
               h_l = [self.Hospitals[i] for i in l]
               dr_.append(h_l)
            else:
               dr_.append('x')
         hos_on_dr.append(dr_)

      Days_with_holmark = [f'{d}' if isBizDay(f'202405{d:02d}') else f'*{d}*' for d in self.Days]

      dr_on_hos = pd.DataFrame(dr_on_hos,columns=Days_with_holmark)
      dr_on_hos.index = self.Hospitals

      hos_on_dr = pd.DataFrame(hos_on_dr,columns=Days_with_holmark)
      hos_on_dr.index = self.Doctors

      return dr_on_hos, hos_on_dr

   def check_result(self):
      Day_biz = [d for d in self.Days if isBizDay(f'202405{d:02d}')]
      Day_hol = [d for d in self.Days if not isBizDay(f'202405{d:02d}')]

      ## 病院の希望当直日を守る（制約）
      ### 希望当直日以外は配置しない
      for h in self.Hospitals:
         print(f'{h}:')
         for day in self.Days:
            if day in self.jobs_hos[h]:
                  if not sum([self.X[dr,h,day].value() for dr in self.Doctors]) == 1:
                     print(f'\t- {day}日に担当する医師がいません．')
            else:
                  if not sum([self.X[dr,h,day].value() for dr in self.Doctors]) == 0:
                     print(f'\t- {day}日は依頼がありませんでしたが，当直があります．')


      for dr in self.Doctors:
         print(f'{dr}：')

         ## 医師の希望休暇日を守る（制約）
         print(f'\t* 希望休暇日について，')
         for day in self.rests_dr[dr]:
            if not sum([self.X[dr,h,day].value() for h in self.Hospitals]) == 0:
               print(f'\t\t- {day}に休暇申請していますが，却下されました')


         ## 同じ病院への当直は週に1回まで（不等式制約）
         print(f'\t* 同じ病院への週間勤務回数について，')
         for h in self.Hospitals:
            for day in self.Days[:-5]:
               if not sum([self.X[dr,h,day+d].value() for d in range(5)]) <= 1:
                  print(f'\t\t- {h} に {day}日からの5日間に2回以上勤務しています．')

         ## 連日・隔日勤務NG（制約）
         print(f'\t* 連日・隔日勤務について，')
         for day in self.Days[:-1]:
            if not sum([self.X[dr,h,day].value()+self.X[dr,h,day+1].value() for h in self.Hospitals]) <= 1:
               print(f'\t\t- {day}日から連日勤務しています．')
         for day in self.Days[:-2]:
            if not sum([self.X[dr,h,day].value()+self.X[dr,h,day+2].value() for h in self.Hospitals]) <= 1:
               print(f'\t\t- {day}日から隔日勤務しています．')

         ## 平日勤務回数，土日祝日勤務回数
         print(f'\t* 平日勤務回数，土日祝日勤務回数')
         Nj_b = int(sum([self.X[dr,h,day].value() for h in self.Hospitals for day in Day_biz]))
         Nj_h = int(sum([self.X[dr,h,day].value() for h in self.Hospitals for day in Day_hol]))
         x = self.Nj_dr[dr][0] - Nj_b
         if x<0:
            print(f'\t\t- 平日勤務 {self.Nj_dr[dr][0]} 回を希望しているが，{Nj_b} 回に増えた')
         elif x>0:
            print(f'\t\t- 平日勤務 {self.Nj_dr[dr][0]} 回を希望しているが，{Nj_b} 回に減った')
         y = self.Nj_dr[dr][1] - Nj_h
         if y<0:
            print(f'\t\t- 土日祝日勤務 {self.Nj_dr[dr][1]} 回を希望しているが，{Nj_h} 回に増えた')
         elif y>0:
            print(f'\t\t- 土日祝日勤務 {self.Nj_dr[dr][1]} 回を希望しているが，{Nj_h} 回に減った')

      ## 各医師は，各日，1箇所にしか存在しない．
      print(f'エラー:')
      for day in self.Days:
         for dr in self.Doctors:
            if not sum([self.X[dr,h,day].value() for h in self.Hospitals]) <= 1:
               s = np.array([self.X[dr,h,day].value() for h in self.Hospitals])
               l = np.where(s>=1)[0]
               print(f'\t- {day}日に，{dr} が {[self.Hospitals[l_i] for l_i in l for _ in range(int(s[l_i]))]} に同時勤務します.')
         for h in self.Hospitals:
            if not sum([self.X[dr,h,day].value() for dr in self.Doctors]) <= 1:
               s = np.array([self.X[dr,h,day].value() for dr in self.Doctors])
               l = np.where(s>=1)[0]
               print(f'\t- {day}日に，{h} に {[self.Doctors[l_i] for l_i in l for _ in range(int(s[l_i]))]} が同時勤務します')


if __name__ == '__main__':
   import numpy as np
   rg = np.random.default_rng(1)

   N_dr = 10
   N_hos = 10
   Doctors = [f'dr{dr:02d}' for dr in range(N_dr)]
   Hospitals = [f'hos{hos:02d}' for hos in range(N_hos)]
   Days = list(range(1,32))

   rests_dr = {f'{dr}':rg.integers(1,32,size=rg.integers(10)) for dr in Doctors}
   jobs_hos = {f'{hos}':rg.integers(1,32,size=rg.integers(14)) for hos in Hospitals}
   Nj_dr = {f'{dr}':rg.integers(4,size=2) for dr in Doctors}

   Nj_1 = np.sum([np.count_nonzero(jobs_hos[hos]) for hos in Hospitals])
   Nj_2 = N_dr * len(Days) - np.sum([np.count_nonzero(rests_dr[dr]) for dr in Doctors])
   assert Nj_1 < Nj_2

   Prob = ShiftModel(Doctors, Hospitals, Days, rests_dr, jobs_hos, Nj_dr)
   Prob.modeling()
   Prob.print()
   Prob.solve()
   dr_on_hos, hos_on_dr = Prob.get_results()
   print(dr_on_hos)
   print(hos_on_dr)
   Prob.check_result()



