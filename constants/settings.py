from datetime import datetime

SLEEP_INTERVAL = 10

INITIAL_RETURN = 0.01
INCREMENTAL_RETURN = 0.005

MAXIMUM_ALLOCATION = 1000

OLD_DATE  = datetime(2024, 9, 23) .date()

def update_old_date(new_date):
    global OLD_DATE
    OLD_DATE = new_date

def get_old_date():
    global OLD_DATE
    return OLD_DATE

def get_allocation():
    global MAXIMUM_ALLOCATION
    return MAXIMUM_ALLOCATION