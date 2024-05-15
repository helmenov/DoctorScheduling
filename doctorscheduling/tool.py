def isBizDay(yyyymmdd:str)->bool:
    """平日か土日祝かを判断

    Args:
        yyyymmdd (str): 8桁日付

    Returns:
        bool: 平日(True),土日祝(False)
    """
    import datetime
    import jpholiday

    y = int(yyyymmdd[:4])
    m = int(yyyymmdd[4:6])
    d = int(yyyymmdd[6:8])
    Date = datetime.date(y, m, d)
    if Date.weekday() >= 5 or jpholiday.is_holiday(Date):
        return False
    else:
        return True
