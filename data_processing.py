import pandas as pd
from pandas import to_datetime
import json
import numpy as np
from datetime import datetime, timedelta
from data_reading import load_guest_data, load_settlement_data, load_dictionary_data, process_expenses, process_settlement, how_to_filter_guests


def convert_percentage(percentage_str):
    if isinstance(percentage_str, str) and percentage_str.endswith('%'):
        return float(percentage_str[:-1]) / 100


def find_next_thursday(date):
    # Find the number of days to add to reach the next Thursday
    days_to_thursday = (3 - date.weekday() + 7) % 7  # 3 corresponds to Thursday (Monday = 0, ..., Sunday = 6)
    if days_to_thursday == 0:  # If it's already Thursday, add 7 days to get the next one
        days_to_thursday = 7

    next_thursday = date + timedelta(days=days_to_thursday)     # Calculate the next Thursday
    return next_thursday.strftime('%Y-%m-%d')


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


def guests_by_column(df, column, year, month):
    year = int(year)
    month = int(month)

    # Use `.apply(lambda x: x.year)` and `.apply(lambda x: x.month)` to extract year and month from the column
    df_filtered = df[
        (df[column].apply(lambda x: x.year) == year) &
        (df[column].apply(lambda x: x.month) == month)
    ]

    return df_filtered

df_filtered_date = guests_by_column(df, 'Date', year, month)

# Filter by 'Payday' column using guests_by_column function
df_filtered_payday = guests_by_column(df, 'Payday', year, month)

# Combine the results of both filters using pd.concat() and drop duplicates
df_filtered_combined = pd.concat([df_filtered_date, df_filtered_payday]).drop_duplicates()


def calculate_settlement_route(year=None, month=None):
    # Load the expense data
    if month and year:
        expenses_dict, monthname_year = load_dictionary_data('expenses', year, month)
        df_expenses = process_expenses(expenses_dict)
    else:
        expenses_dict, monthname_year = load_dictionary_data('expenses')
        df_expenses = process_expenses(expenses_dict)

    # monthname ---> month
    monthname, year = monthname_year.split(' ')
    month_ind = month_words.index(monthname)
    month = month_numbers[month_ind]
    # -------------------------------------------------------------------------

    # Load the guest data -----------------------------------------------------
    df_guest = load_guest_data()
    df_guest = guests_by_column(df_guest, 'Payday', year, month)

    # df_guest_date = filter_guests_based_on_column(df_guest, 'Date', year, month)
    # df_guest_check_out = filter_guests_based_on_column(df_guest, 'Check-out', year, month)
    # df_guest_payday = filter_guests_based_on_column(df_guest, 'Payday', year, month)
    # -------------------------------------------------------------------------

    # Load previous month settlement
    ex_month_ind = str(int(month) - 2)
    ex_month = month_numbers[int(ex_month_ind)]

    # ex_monthname = month_mapping.get(month)
    # ex_monthname_year = f'{ex_monthname} {year}'    # I need to introduce ex_year

    settlement_dict, ex_monthname_year = load_dictionary_data('settlement', year, ex_month)
    income_df, vat_df, zus_df = process_settlement(settlement_dict)
    # income_df, vat_df, zus_df = load_settlement_data(year, ex_month)    # It's supposed to return an empty dictionary if month and year don't exist
    # ---------------------------------------------------------------------

    # VAT and base for sales
    service_vat_8_base = df_guest['Netto'].sum() if not df_guest['Netto'].isnull().all() else 0
    service_vat_8_tax = df_guest['VAT 8%'].sum() if not df_guest['VAT 8%'].isnull().all() else 0

    # Import of foreign services
    import_vat_23_base = df_guest['Total Commission + Fee'].sum() if not df_guest[
        'Total Commission + Fee'].isnull().all() else 0
    import_vat_23_tax = df_guest['VAT 23%'].sum() if not df_guest['VAT 23%'].isnull().all() else 0

    # VAT and base for expenses
    total_expenses_vat = df_expenses['Shopping VAT'].sum() + df_expenses['Apartment VAT'].sum() + df_expenses['Company Fees VAT'].sum()
    total_expenses_netto = df_expenses['Shopping Netto'].sum() + df_expenses['Apartment Netto'].sum() + df_expenses['Company Fees Netto'].sum()
    # ---------------------------------------------------------------------

    # VAT Payable, VAT Deductible
    vat_payable_base = service_vat_8_base + import_vat_23_base
    vat_payable_tax = service_vat_8_tax + import_vat_23_tax

    vat_deductible_base = import_vat_23_base + total_expenses_netto
    vat_deductible_tax = import_vat_23_tax + total_expenses_vat

    # Monthly settlement
    month_vat = vat_payable_tax - vat_deductible_tax
    which_surplus = ('payable' if month_vat > 0 else 'deductible')
    previous_surplus = vat_df.loc[vat_df.index[0], 'Surplus']
    previous_surplus = float(previous_surplus)

    settlement = month_vat - previous_surplus   # settlement>0 - vat_to_pay; settlement<0 - surplus
    surplus = min(0, settlement) * (-1)     # surplus + month_vat = previous_surplus (VAT covered by previous surplus)

    vat_to_pay = max(0, settlement)     # vat_to_pay + previous_surplus = month_vat (VAT covered by previous surplus & VAT to pay)
    # ---------------------------------------------------------------------
    income = round(service_vat_8_base - import_vat_23_base - total_expenses_netto, 2)

    insurance_bases = {
        '2023': 4161.00,
        '2024': 4694.40
    }

    min_health_insurance = {
        '2023': 314.10,
        '2024': 381.78
    }

    insurance_base = insurance_bases[year]
    min_health = min_health_insurance[year]

    pension_ins = round(insurance_base*0.1952, 2)
    disability_ins = round(insurance_base*0.08, 2)
    accident_ins = round(insurance_base*0.0167, 2)
    labour_fund = round(insurance_base*0.0245, 2)

    health_ins = max(round(income*0.09, 2), min_health)

    insurance = (pension_ins + disability_ins + accident_ins + labour_fund + health_ins)

    tax_base = income - insurance
    income_tax = round(tax_base*0.12, 2)
    net_profit = tax_base - income_tax

    vat_data = {
        'Hotel Services Net': service_vat_8_base,
        'Hotel Services VAT 8%': service_vat_8_tax,
        'Import Net': import_vat_23_base,
        'Import VAT 23%': import_vat_23_tax,
        'Operating Expenses Net': total_expenses_netto,
        'Operating Expenses VAT': total_expenses_vat,
        'VAT Payable Base': vat_payable_base,
        'VAT Payable': vat_payable_tax,
        'VAT Deductible Base': vat_deductible_base,
        'VAT Deductible': vat_deductible_tax,
        'Which Surplus': which_surplus,
        'Month VAT': abs(month_vat),
        'Ex-Surplus': previous_surplus,
        'VAT to pay': vat_to_pay,
        'Surplus': surplus,
        'Income':  income,
        'Pension Insurance': pension_ins,
        'Disability Insurance': disability_ins,
        'Accident Insurance': accident_ins,
        'Labour Fund': labour_fund,
        'Health Insurance': health_ins,
        'Insurance': insurance,
        'Tax Base': tax_base,
        'Income Tax': income_tax,
        'Net Profit': net_profit
    }

    return vat_data
