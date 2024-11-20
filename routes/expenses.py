from flask import Blueprint, request, render_template, redirect, url_for, session
import json
import numpy as np
import pandas as pd
from utils.data_reading import load_guest_data, load_dictionary_data, process_expenses, total_guests, guests_by_column
from utils.helpers import store_filter_data

expenses_bp = Blueprint('expenses', __name__, template_folder='templates')


class Expenses:
    @staticmethod
    @expenses_bp.route('/')
    def show_expenses():
        """Render expense data in expenses.html template."""
        current_module = 'expenses'

        # Retrieve year and month from the session
        filter_data = session.get('filter', {})
        year = filter_data.get('year')
        month = filter_data.get('month')

        if month:
            dict_expenses, monthname_year = load_dictionary_data('expenses', year, month)
            df_expenses = process_expenses(dict_expenses)
        else:
            dict_expenses, monthname_year = load_dictionary_data('expenses')
            df_expenses = process_expenses(dict_expenses)

        # Calculate total sums for each category
        total_shopping_price = df_expenses['Shopping Price'].sum()
        total_shopping_vat = df_expenses['Shopping VAT'].sum()
        total_shopping_netto = df_expenses['Shopping Netto'].sum()

        total_apartment_price = df_expenses['Apartment Price'].sum()
        total_apartment_vat = df_expenses['Apartment VAT'].sum()
        total_apartment_netto = df_expenses['Apartment Netto'].sum()

        total_company_price = df_expenses['Company Fees Price'].sum()
        total_company_vat = df_expenses['Company Fees VAT'].sum()
        total_company_netto = df_expenses['Company Fees Netto'].sum()

        df_expenses = df_expenses.fillna('')

        # Add an index column for each category
        df_expenses['Shopping Index'] = np.where(df_expenses['Shopping Name'] != '',
                                                 np.arange(1, df_expenses['Shopping Name'].notna().sum() + 1), '')
        df_expenses['Apartment Index'] = np.where(df_expenses['Apartment Name'] != '',
                                                  np.arange(1, df_expenses['Apartment Name'].notna().sum() + 1), '')
        df_expenses['Company Fees Index'] = np.where(df_expenses['Company Fees Name'] != '',
                                                np.arange(1, df_expenses['Company Fees Name'].notna().sum() + 1), '')

        # Pass sums to the template
        return render_template(
            'expenses.html',
            tables=[df_expenses],
            current_module=current_module,
            total_shopping_price=total_shopping_price,
            total_shopping_vat=total_shopping_vat,
            total_shopping_netto=total_shopping_netto,
            total_apartment_price=total_apartment_price,
            total_apartment_vat=total_apartment_vat,
            total_apartment_netto=total_apartment_netto,
            total_company_price=total_company_price,
            total_company_vat=total_company_vat,
            total_company_netto=total_company_netto
        )

    @staticmethod
    @expenses_bp.route('/add_expense_form')
    def add_expense_form():
        """Render the Add Expense form."""
        return render_template('add_expense.html')

    @staticmethod
    @expenses_bp.route('/add_expense', methods=['POST'])
    def add_expense():
        """Add a new expense to the JSON file."""
        category = request.form['category']
        name = request.form['name']
        price = request.form['price']
        monthname = request.form['monthname']
        vat_perc = request.form['vat_perc']
        # year = request.form['year']
        year = '2024'

        monthname_year = monthname + " " + year

        # Load existing expenses
        with open('data_source/expenses.json', 'r') as file:
            expense_data = json.load(file)

        if monthname_year not in expense_data:
            expense_data[monthname_year] = {"Shopping": [], "Apartment Bills": [], "Company Fees": []}

        # Append the new expense to the Shopping category
        new_expense = {"Name": name, "Price": float(price), "VAT %": vat_perc}

        # Append the new expense to the specified category
        if category in expense_data[monthname_year]:
            expense_data[monthname_year][category].append(new_expense)

        # Save the updated data back to the JSON file
        with open('data_source/expenses.json', 'w') as file:
            json.dump(expense_data, file, indent=4)

        # Redirect back to the expenses page
        return redirect(url_for('expenses.show_expenses'))

    @staticmethod
    @expenses_bp.route('/filter_expenses', methods=['POST'])
    def filter_expenses():
        current_module = 'expenses'

        year = str(request.form['year'])  # Retrieve the selected month and year from the form
        month = str(request.form['month'])

        store_filter_data(year, month)  # Store filter data in session

        dict_expenses, monthname_year = load_dictionary_data('expenses', year, month)
        df_expenses = process_expenses(dict_expenses)

        # Calculate total sums for each category
        total_shopping_price = df_expenses['Shopping Price'].sum()
        total_shopping_vat = df_expenses['Shopping VAT'].sum()
        total_shopping_netto = df_expenses['Shopping Netto'].sum()

        total_apartment_price = df_expenses['Apartment Price'].sum()
        total_apartment_vat = df_expenses['Apartment VAT'].sum()
        total_apartment_netto = df_expenses['Apartment Netto'].sum()

        total_company_price = df_expenses['Company Fees Price'].sum()
        total_company_vat = df_expenses['Company Fees VAT'].sum()
        total_company_netto = df_expenses['Company Fees Netto'].sum()

        df_expenses = df_expenses.fillna('')

        # Add an index column for each category
        df_expenses['Shopping Index'] = np.where(df_expenses['Shopping Name'] != '',
                                                 np.arange(1, df_expenses['Shopping Name'].notna().sum() + 1), '')
        df_expenses['Apartment Index'] = np.where(df_expenses['Apartment Name'] != '',
                                                 np.arange(1, df_expenses['Apartment Name'].notna().sum() + 1), '')
        df_expenses['Company Fees Index'] = np.where(df_expenses['Company Fees Name'] != '',
                                                 np.arange(1, df_expenses['Company Fees Name'].notna().sum() + 1), '')

        # Pass sums to the template
        return render_template(
            'expenses.html',
            year=year,
            month=month,
            tables=[df_expenses],
            current_module=current_module,
            total_shopping_price=total_shopping_price,
            total_shopping_vat=total_shopping_vat,
            total_shopping_netto=total_shopping_netto,
            total_apartment_price=total_apartment_price,
            total_apartment_vat=total_apartment_vat,
            total_apartment_netto=total_apartment_netto,
            total_company_price=total_company_price,
            total_company_vat=total_company_vat,
            total_company_netto=total_company_netto
        )
