from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from pandas import to_datetime
import json
import numpy as np
from datetime import datetime, timedelta
import calendar


def store_filter_data(year, month):
    session['filter'] = {'year': year, 'month': month}


def store_mode_data(mode):
    session['mode'] = {'mode': mode}


def convert_percentage(percentage_str):
    if isinstance(percentage_str, str) and percentage_str.endswith('%'):
        return float(percentage_str[:-1]) / 100


def when_check_out(df):
    df['Check-out'] = pd.NaT

    name_counter = 0
    compare_name = ''
    for i in range(0, df.shape[0]):
        guest_name = df['Guest'].iloc[i]  # Retrieve the guest for row i

        if guest_name != compare_name:
            if compare_name is None:  # First case (i = 0, when there was no previous guest)
                name_counter = 1
                compare_name = guest_name
            else:
                current_date = df['Date'].iloc[i - 1]  # We found the end of reservation
                next_day = current_date + timedelta(days=1)

                for day in range(name_counter):
                    df.loc[(df['Guest'] == compare_name) & (df.index == i - name_counter + day), 'Check-out'] = next_day

                compare_name = guest_name
                name_counter = 1  # First occurence of a new name
        elif guest_name == compare_name:
            name_counter += 1

    # Handle the last guest after the loop ends
    if name_counter > 0:
        current_date = df['Date'].iloc[-1]  # Get the last date for the current guest
        next_day = current_date + timedelta(days=1)

        for day in range(name_counter):
            df.loc[(df['Guest'] == compare_name) & (df.index == len(df) - name_counter + day), 'Check-out'] = next_day

    return df['Check-out']


def when_payday(df):
    df['Payday'] = ""

    # Iterate over the DataFrame to calculate the payday for each check-out date
    for i in range(len(df)):
        check_out_date = df['Check-out'].iloc[i]
        if pd.notna(check_out_date):
            payday = find_next_thursday(check_out_date)
            df.loc[i, 'Payday'] = payday

    return df['Payday']


def find_next_thursday(date):
    # Find the number of days to add to reach the next Thursday
    days_to_thursday = (3 - date.weekday() + 7) % 7  # 3 corresponds to Thursday (Monday = 0, ..., Sunday = 6)
    if days_to_thursday == 0:  # If it's already Thursday, add 7 days to get the next one
        days_to_thursday = 7

    next_thursday = date + timedelta(days=days_to_thursday)     # Calculate the next Thursday
    return next_thursday.strftime('%Y-%m-%d')
