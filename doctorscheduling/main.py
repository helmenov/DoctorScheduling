from types import NoneType
import pulp
import calendar
from doctorscheduling.tool import isBizDay, BizDaysOnWeek
import numpy as np

# print時に省略しない．
np.set_printoptions(threshold=np.inf)

class ShiftModel():
   def __init__(self,Doctors:list[str],Hospitals:list[str],Days:list[int],grade_dr:dict, grade_hos:dict, rests_dr:dict,jobs_hos:dict,Nj_dr:dict,yyyymm:str):
      self.yyyymm = yyyymm
      # Sets
      self.Doctors = Doctors
      self.Hospitals = Hospitals
      self.Days = Days
      # Constants
      self.rests_dr = rests_dr
      self.jobs_hos = jobs_hos
      self.Nj_dr = Nj_dr
      self.grade_dr = grade_dr
      self.grade_hos = grade_hos
      # Variables
      self.X = None

      # Model
      self.model = None

      # Status
      self.status = None

   def modeling(self):
      DrHosDay = [(dr,h,day) for dr in self.Doctors for h in self.Hospitals for day in self.Days]
      X = pulp.LpVariable.dicts("X", DrHosDay, cat="Integer",lowBound=0,upBound=1)
      S1 = pulp.LpVariable.dicts("S1", DrHosDay, cat="Continuous", lowBound=0)
      DrDay_1 = [(dr,day) for dr in self.Doctors for day in self.Days[:-1]]
      S2 = pulp.LpVariable.dicts("S2", DrDay_1, cat='Continuous',lowBound=0,upBound=1)
      DrDay_2 = [(dr,day) for dr in self.Doctors for day in self.Days[:-2]]
      S3 = pulp.LpVariable.dicts("S3", DrDay_2, cat='Continuous',lowBound=0,upBound=1)
      S4 = pulp.LpVariable.dicts("S4", [(dr, k) for dr in self.Doctors for k in [0,1,2,3,4]], cat="Continuous",lowBound=0)

      model = pulp.LpProblem(name = "DoctorSchedulingProblem", sense = pulp.LpMinimize)

      # 目的関数と許容誤差
      model += pulp.lpSum([S1[dr,h,day] for dr in self.Doctors for h in self.Hospitals for day in self.Days]) \
         + pulp.lpSum([S2[dr,day] for dr in self.Doctors for day in self.Days[:-1]]) \
         + pulp.lpSum([S3[dr,day] for dr in self.Doctors for day in self.Days[:-2]]) \
         + pulp.lpSum([S4[dr,k] for dr in self.Doctors for k in [0,1,2,3,4]]) \
         - 0.01*pulp.lpSum([self.grade_hos[h]*self.grade_dr[dr]*X[dr,h,day] for dr in self.Doctors for h in self.Hospitals for day in self.Days])

      ## 医師の希望休暇日を守る（等式制約）
      for dr in self.Doctors:
         for day in self.rests_dr[dr]:
            model += pulp.lpSum([X[dr,h,day] for h in self.Hospitals]) == 0


      ## 病院の希望当直日を守る（等式制約）
      ### 希望当直日以外は配置しない
      for h in self.Hospitals:
         for day in self.Days:
            if day in self.jobs_hos[h]:
                  model += pulp.lpSum([X[dr,h,day] for dr in self.Doctors]) == 1
            else:
                  model += pulp.lpSum([X[dr,h,day] for dr in self.Doctors]) == 0

      # 不等式制約もしくは最小化
      # - Infeasibleは，制約が不可能（答えに意味ない）

      ## 同じ病院への当直は週に1回まで（不等式制約もしくは最小化）
      for dr in self.Doctors:
         for h in self.Hospitals:
            bdw_list = list()
            for day in self.Days:
               bdw = BizDaysOnWeek(f'{self.yyyymm}{day:02d}')
               if not bdw in bdw_list:
                  model += pulp.lpSum([X[dr,h,d] for d in bdw]) - 1 - S1[dr,h,day] <= 0
                  model += S1[dr,h,day] <= len(bdw)-1
                  bdw_list.append(bdw)
               else:
                  model += S1[dr,h,day] == 0

      ## 連日・隔日勤務NG（制約）
      for dr in self.Doctors:
         for day in self.Days[:-1]:
            model += pulp.lpSum([X[dr,h,day]+X[dr,h,day+1] for h in self.Hospitals]) - 1 - S2[dr,day] <= 0
            model += S2[dr,day] == 0
         # 隔日勤務
         for day in self.Days[:-2]:
            model += pulp.lpSum([X[dr,h,day]+X[dr,h,day+2] for h in self.Hospitals]) - 1 - S3[dr,day] <= 0
            model += S3[dr,day] == 0


      ## 月に平日勤務2回，土日祝勤務2回（制約？）
      ### 日付dayが平日か土日祝なのかを判断する関数をisBizDay(day)とする．
      ### 0,1の人は守らないといけない．2の人は増やしてもよい気がする．

      Day_biz = [d for d in self.Days if isBizDay(f'{self.yyyymm}{d:02d}')]
      Day_hol = [d for d in self.Days if not isBizDay(f'{self.yyyymm}{d:02d}')]
      Hosp_Daigaku = self.Hospitals[0:1]
      Hosp_Kyukyu = self.Hospitals[1:2]
      Hosp_Other = self.Hospitals[2:]
      for dr in self.Doctors:
         # 救急部
         model += pulp.lpSum([X[dr,h,day] for h in Hosp_Kyukyu for day in self.Days]) - self.Nj_dr[dr][0] - S4[dr,0] <= 0
         if self.Nj_dr[dr][0] < 2:
            model += S4[dr,0] == 0
         else:
         #   model += S4[dr,0] <= len(Hosp_Kyukyu) * len(self.Days) - self.Nj_dr[dr][0]
            model += S4[dr,0] <= 1
         # 大学平日
         model += pulp.lpSum([X[dr,h,day] for h in Hosp_Daigaku for day in Day_biz]) - self.Nj_dr[dr][1] - S4[dr,1] <= 0
         if self.Nj_dr[dr][1] < 2:
            model += S4[dr,1] == 0
         else:
         #   model += S4[dr,1] <= len(Hosp_Daigaku) * len(Day_biz) - self.Nj_dr[dr][1]
            model += S4[dr,1] <= 1
         # 大学休日
         model += pulp.lpSum([X[dr,h,day] for h in Hosp_Daigaku for day in Day_hol]) - self.Nj_dr[dr][2] - S4[dr,2] <= 0
         if self.Nj_dr[dr][2] < 2:
            model += S4[dr,2] == 0
         else:
         #   model += S4[dr,2] <= len(Hosp_Daigaku) * len(Day_hol) - self.Nj_dr[dr][2]
            model += S4[dr,2] <= 1
         # 病院平日
         model += pulp.lpSum([X[dr,h,day] for h in Hosp_Other for day in Day_biz]) - self.Nj_dr[dr][3] - S4[dr,3] <= 0
         if self.Nj_dr[dr][3] < 2:
            model += S4[dr,3] == 0
         else:
         #   model += S4[dr,3] <= len(Hosp_Other) * len(Day_biz) - self.Nj_dr[dr][3]
            model += S4[dr,3] <= 1
         # 病院祝日
         model += pulp.lpSum([X[dr,h,day] for h in Hosp_Other for day in Day_hol]) - self.Nj_dr[dr][4] - S4[dr,4] <= 0
         if self.Nj_dr[dr][4] < 2:
            model += S4[dr,4] == 0
         else:
         #   model += S4[dr,4] <= len(Hosp_Other) * len(Day_hol) - self.Nj_dr[dr][4]
            model += S4[dr,4] <= 1

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

   def set_option(self, msg, timeLimit, threads=4, solver="CBC"):
        self.msg = msg
        self.threads = threads
        self.timeLimit = timeLimit
        if solver == "SCIP":
            self.solver = pulp.SCIP(
                msg=self.msg, threads=self.threads, timeLimit=self.timeLimit
            )
        else:  # CBC
            self.solver = pulp.PULP_CBC_CMD(
                msg=self.msg, threads=self.threads, timeLimit=self.timeLimit
            )

   def solve(self):
      self.status = self.model.solve(self.solver)
      print(f"Status: {pulp.LpStatus[self.status]}")

   def get_results(self,mode="onehot"):
      if self.status < -1:
         dr_on_hos, hos_on_dr = None, None
      else:
         import pandas as pd

         if not isinstance(self.model.objective,NoneType):
            print(f'Objective: {self.model.objective.value()}')

         if mode == "schedules":
            dr_on_hos = list()
            for h in self.Hospitals:
               hos_ = list()
               for day in self.Days:
                  s = np.array([self.X[dr,h,day].value() for dr in self.Doctors])
                  l = np.where(s>=1)[0]
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
                  l = np.where(s>=1)[0]
                  if len(l):
                     h_l = [self.Hospitals[i] for i in l]
                     dr_.append(h_l)
                  else:
                     dr_.append('x')
               hos_on_dr.append(dr_)

            Days_with_holmark = [f'{d}' if isBizDay(f'{self.yyyymm}{d:02d}') else f' *{d}* ' for d in self.Days]

            dr_on_hos = pd.DataFrame(dr_on_hos,columns=Days_with_holmark)
            dr_on_hos.index = self.Hospitals

            hos_on_dr = pd.DataFrame(hos_on_dr,columns=Days_with_holmark)
            hos_on_dr.index = self.Doctors
            ret = (dr_on_hos, hos_on_dr)
         else: #"onehot"
            df = pd.DataFrame([[dr, h, day, self.X[dr,h,day].value()] for dr in self.Doctors for h in self.Hospitals for day in self.Days],columns=['Doctor','Hospital','Day','On'])
            ret = df

      return ret

   def check_result(self,Xdf,isdict=False):
      Day_biz = [d for d in self.Days if isBizDay(f'{self.yyyymm}{d:02d}')]
      Day_hol = [d for d in self.Days if not isBizDay(f'{self.yyyymm}{d:02d}')]
      Hosp_Daigaku = self.Hospitals[0:1]
      Hosp_Kyukyu = self.Hospitals[1:2]
      Hosp_Other = self.Hospitals[2:]
      S1 = S2 = S3 = S4 = 0

      if not isdict:
         X = dict()
         for dr in self.Doctors:
            X0 = Xdf[Xdf["Doctor"]==dr]
            for h in self.Hospitals:
               X1 = X0[X0["Hospital"]==h]
               for day in self.Days:
                  L = X1[X1["Day"]==day]["On"].values
                  X[(dr,h,day)] = int(L[0]) if len(L)>0 else 0
      else:
         X = Xdf

      ## 病院の希望当直日を守る（制約）
      ### 希望当直日以外は配置しない
      print(f'== 病院ごとの希望当直日について')
      for h in self.Hospitals:
         print(f'{h}:')
         e = 0
         for day in self.Days:
            if day in self.jobs_hos[h]:
                  if not sum([X[(dr,h,day)] for dr in self.Doctors]) == 1:
                     print(f'\t- {day}日に担当する医師がいません．')
                     e += 1
            else:
                  if not sum([X[(dr,h,day)] for dr in self.Doctors]) == 0:
                     print(f'\t- {day}日は依頼がありませんでしたが，当直があります．')
                     e += 1
         if not e:
            print(f'\t- 満たしています．')

      print(f'== 医師ごとのチェック')
      for dr in self.Doctors:
         print(f'{dr}：')
         ## 医師の希望休暇日を守る（制約）
         print(f'\t* 希望休暇日について，')
         e = 0
         for day in self.rests_dr[dr]:
            if not sum([X[(dr,h,day)] for h in self.Hospitals]) == 0:
               print(f'\t\t- {day}に休暇申請していますが，却下されました')
               e += 1
         if not e:
            print(f'\t\t- 問題なし')

         ## 同じ病院への当直は週に1回まで（不等式制約）
         print(f'\t* 同じ病院への週間勤務回数について，(S1)')
         e = 0
         for h in self.Hospitals:
            bdw_old = []
            for day in self.Days:
               bdw = BizDaysOnWeek(f'{self.yyyymm}{day:02d}')
               if not bdw == bdw_old:
                  if not sum([X[(dr,h,d)] for d in bdw]) <= 1:
                     print(f'\t\t- {h} に {day}日を含む週に2回以上勤務しています．')
                     e += 1
                     S1 += sum([X[(dr,h,d)] for d in bdw]) -1
                  bdw_old = bdw[:]
         if not e:
            print(f'\t\t- 問題なし')

         ## 連日・隔日勤務NG（制約）
         print(f'\t* 連日・隔日勤務について，(S2,S3)')
         e = 0
         for day in self.Days[:-1]:
            if not sum([X[(dr,h,day)]+X[(dr,h,day+1)] for h in self.Hospitals]) <= 1:
               print(f'\t\t- {day}日から連日勤務しています．')
               S2 += sum([X[(dr,h,day)]+X[(dr,h,day+1)] for h in self.Hospitals]) - 1
               e += 1
         for day in self.Days[:-2]:
            if not sum([X[(dr,h,day)]+X[(dr,h,day+2)] for h in self.Hospitals]) <= 1:
               print(f'\t\t- {day}日から隔日勤務しています．')
               S3 += sum([X[(dr,h,day)]+X[(dr,h,day+2)] for h in self.Hospitals]) - 1
               e += 1
         if not e:
            print(f'\t\t- 問題なし')

         ## 平日勤務回数，土日祝日勤務回数
         print(f'\t* 平日勤務回数，土日祝日勤務回数 (S4)')
         e = 0
         Nj_0 = int(sum([X[(dr,h,day)] for h in Hosp_Kyukyu for day in self.Days]))
         Nj_1 = int(sum([X[(dr,h,day)] for h in Hosp_Daigaku for day in Day_biz]))
         Nj_2 = int(sum([X[(dr,h,day)] for h in Hosp_Daigaku for day in Day_hol]))
         Nj_3 = int(sum([X[(dr,h,day)] for h in Hosp_Other for day in Day_biz]))
         Nj_4 = int(sum([X[(dr,h,day)] for h in Hosp_Other for day in Day_hol]))

         x0 = self.Nj_dr[dr][0] - Nj_0
         if x0 < 0:
            print(f'\t\t- 救急部勤務 {self.Nj_dr[dr][0]} 回を希望しているが，{Nj_0} 回に増えた')
            e += 1
            S4 += -x0

         x1 = self.Nj_dr[dr][1] - Nj_1
         if x1 < 0:
            print(f'\t\t- 大学平日勤務 {self.Nj_dr[dr][1]} 回を希望しているが，{Nj_1} 回に増えた')
            e += 1
            S4 += -x1

         x2 = self.Nj_dr[dr][2] - Nj_2
         if x2 <0:
            print(f'\t\t- 大学休日勤務 {self.Nj_dr[dr][2]} 回を希望しているが，{Nj_2} 回に増えた')
            e += 1
            S4 += -x2

         x3 = self.Nj_dr[dr][3] - Nj_3
         if x3 < 0:
            print(f'\t\t- 病院平日勤務 {self.Nj_dr[dr][3]} 回を希望しているが，{Nj_3} 回に増えた')
            e += 1
            S4 += -x3
         elif x3>0:
            print(f'\t\t- 病院平日勤務 {self.Nj_dr[dr][3]} 回を希望しているが，{Nj_3} 回に減った')
            e += 1

         x4 = self.Nj_dr[dr][4] - Nj_4
         if x4 < 0:
            print(f'\t\t- 病院土日祝日勤務 {self.Nj_dr[dr][4]} 回を希望しているが，{Nj_4} 回に増えた')
            e += 1
            S4 += -x4
         elif x4 > 0:
            print(f'\t\t- 病院土日祝日勤務 {self.Nj_dr[dr][4]} 回を希望しているが，{Nj_4} 回に減った')
            e += 1

         if not e:
            print(f'\t\t- 問題なし')

      ## 各医師は，各日，1箇所にしか存在しない．
      print(f'== エラー:')
      e = 0
      for day in self.Days:
         for dr in self.Doctors:
            if not sum([X[(dr,h,day)] for h in self.Hospitals]) <= 1:
               s = np.array([X[(dr,h,day)] for h in self.Hospitals])
               l = np.where(s>=1)[0]
               print(f'\t- {day}日に，{dr} が {[self.Hospitals[l_i] for l_i in l for _ in range(int(s[l_i]))]} に同時勤務します.')
               e += 1
         for h in self.Hospitals:
            if not sum([X[(dr,h,day)] for dr in self.Doctors]) <= 1:
               s = np.array([X[(dr,h,day)] for dr in self.Doctors])
               l = np.where(s>=1)[0]
               print(f'\t- {day}日に，{h} に {[self.Doctors[l_i] for l_i in l for _ in range(int(s[l_i]))]} が同時勤務します')
               e += 1
      if not e: print(f'\t- なし')

      Obj = S1 + S2 + S3 + S4 - 0.01*sum([self.grade_hos[h]*self.grade_dr[dr]*X[dr,h,day] for dr in self.Doctors for h in self.Hospitals for day in self.Days])
      return Obj

if __name__ == '__main__':
   import numpy as np

   rg = np.random.default_rng(1)

   yyyymm = '202406'
   N_dr = 10
   N_hos = 10

   day_end = calendar.monthrange(int(yyyymm[:4]),int(yyyymm[4:6]))[1]
   Doctors = [f'dr{dr:02d}' for dr in range(N_dr)]
   Hospitals = [f'hos{hos:02d}' for hos in range(N_hos)]
   Days = [d+1 for d in range(day_end)]

   rests_dr = {f'{dr}':rg.integers(1,int(day_end+1),size=rg.integers(10)) for dr in Doctors}
   jobs_hos = {f'{hos}':rg.integers(1,int(day_end+1),size=rg.integers(14)) for hos in Hospitals}
   Nj_dr = {f'{dr}':rg.integers(4,size=5) for dr in Doctors}
   grade_dr = {f'{dr}':N_dr-i for i, dr in enumerate(Doctors)}
   grade_hos = {f'{h}':N_hos-i for i, h in enumerate(Hospitals)}

   Prob = ShiftModel(Doctors, Hospitals, Days, grade_dr, grade_hos, rests_dr, jobs_hos, Nj_dr, yyyymm)
   Prob.modeling()
   #Prob.print()
   Prob.set_option(msg=0,timeLimit=1000,threads=10, solver="CBC")
   Prob.solve()
   (dr_on_hos, hos_on_dr) = Prob.get_results(mode='schedules')
   print(dr_on_hos)
   print(hos_on_dr)
   X = Prob.get_results()
   Obj = Prob.check_result(X)
   print(Obj)
