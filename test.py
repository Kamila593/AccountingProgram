import pandas as pd
from pandas import to_datetime
import json
import numpy as np
from datetime import datetime, timedelta
import calendar
import data_processing as dp
from utils.data_mapping import month_mapping, columns_expenses, columns_settlement


def load_dictionary_data(file_choice, year=None, month=None):
    # Read data from JSON file
    if file_choice == 'expenses':
        with open('data_source/expenses.json', 'r') as file:
            dict_data = json.load(file)
    elif file_choice == 'settlement':
        with open('data_source/settlement.json', 'r') as file:
            dict_data = json.load(file)

    # Extract keys from the dictionary (is it a dict?)
    keys = list(dict_data.keys())

    # Choose time period
    if month and year:
        # month ---> monthname
        monthname = month_mapping.get(month)
        monthname_year = f'{monthname} {year}'    # E.g. 'February 2024' (recent)
    else:
        # monthname ---> month
        monthname_year = keys[-1]    # E.g. 'February 2024' (filtered)

    # Create dictionary for chosen time period
    if monthname_year in keys:
        dict_month = dict_data[monthname_year]
    else:
        if file_choice == 'expenses':
            dict_month = {key: None for key in columns_expenses}
        elif file_choice == 'settlement':
            dict_month = {key: None for key in columns_settlement}

    return dict_month, monthname_year


def process_expenses(expenses_dict):
    shopping_dict = expenses_dict.get('Shopping')
    apartment_dict = expenses_dict.get('Apartment Bills')
    company_dict = expenses_dict.get('Company Fees')

    df_shopping = pd.DataFrame(shopping_dict) if shopping_dict else pd.DataFrame(columns=['Name', 'Price', 'VAT %'])
    df_apartment = pd.DataFrame(apartment_dict) if apartment_dict else pd.DataFrame(columns=['Name', 'Price', 'VAT %'])
    df_company = pd.DataFrame(company_dict) if company_dict else pd.DataFrame(columns=['Name', 'Price', 'VAT %'])

    df_company['Price'] = df_company['Price'].astype(float)

    # Create lists with numerical VAT % ---------------------------------
    df_shopping_vat = df_shopping['VAT %'].replace('', '0%')
    df_apartment_vat = df_apartment['VAT %'].replace('', '0%')
    df_company_vat = df_company['VAT %'].replace('', '0%')

    df_shopping_vat = df_shopping_vat.apply(lambda x: dp.convert_percentage(x) if pd.notna(x) else x)
    df_apartment_vat = df_apartment_vat.apply(lambda x: dp.convert_percentage(x) if pd.notna(x) else x)
    df_company_vat = df_company_vat.apply(lambda x: dp.convert_percentage(x) if pd.notna(x) else x)

    df_shopping['VAT'] = (df_shopping['Price'] * (df_shopping_vat / (1 + df_shopping_vat))).round(2)
    df_apartment['VAT'] = (df_apartment['Price'] * (df_apartment_vat / (1 + df_apartment_vat))).round(2)
    df_company['VAT'] = (df_company['Price'] * (df_company_vat / (1 + df_company_vat))).round(2)

    # Calculate Netto ---------------------------------------------------
    df_shopping['Netto'] = (df_shopping['Price'] * (1 / (1 + df_shopping_vat))).round(2)
    df_apartment['Netto'] = (df_apartment['Price'] * (1 / (1 + df_apartment_vat))).round(2)
    df_company['Netto'] = (df_company['Price'] * (1 / (1 + df_company_vat))).round(2)

    # Create one df and name columns ---------------------------------------------------
    combined_df = pd.concat([df_shopping, df_apartment, df_company], axis=1)
    combined_df.columns = columns_expenses

    return combined_df


def process_settlement(settlement_dict):
    income_df = pd.DataFrame(settlement_dict.get('Income Settlement'))
    vat_df = pd.DataFrame(settlement_dict.get('VAT'))
    zus_df = pd.DataFrame(settlement_dict.get('ZUS'))

    return income_df, vat_df, zus_df


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

    # -------------------------------------------------------------------------

    # Load previous month settlement ------------------------------------------
    ex_month_ind = str(int(month) - 2)
    ex_month = month_numbers[int(ex_month_ind)]

    # ex_monthname = month_mapping.get(month)
    # ex_monthname_year = f'{ex_monthname} {year}'    # I need to introduce ex_year

    settlement_dict, ex_monthname_year = load_dictionary_data('settlement', year, ex_month)
    income_df, vat_df, zus_df = process_settlement(settlement_dict)
    # ---------------------------------------------------------------------

    # Calculate values ----------------------------------------------------
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


expenses_dict, monthname_year = load_dictionary_data('settlement', '2024', '01')
# print(expenses_dict)
income_df, vat_df, zus_df = process_settlement(expenses_dict)
print(income_df)
