import argparse
from datetime import datetime, timedelta


def get_arg_variables():
    my_parser = argparse.ArgumentParser()
    date_now = datetime.now()
    last_week = date_now - timedelta(days=7)
    date_now_as_str = date_now.strftime("%Y-%m-%d")
    last_week_as_str = last_week.strftime("%Y-%m-%d")

    my_parser.add_argument("start_date", type=str, default=last_week_as_str, nargs="?")
    my_parser.add_argument("end_date", type=str, default=date_now_as_str, nargs="?")
    return my_parser
