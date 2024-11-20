from flask import Blueprint, request, render_template, redirect, url_for, session
import json
import numpy as np
import pandas as pd
from utils.data_reading import load_guest_data, load_dictionary_data, process_expenses, process_settlement, \
    total_guests, guests_by_column, calculate_settlement
from utils.helpers import store_filter_data, store_mode_data
from utils.data_mapping import month_mapping, month_words, month_numbers, colours
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
import plotly.express as px
from plotly.subplots import make_subplots
import calendar
from PIL import Image, ImageDraw, ImageOps, ImageEnhance, ImageFont
from utils.charts import DataChartCreator
import base64

data_analysis_bp = Blueprint('data_analysis', __name__, template_folder='templates')


class MakeDashboard:

    @staticmethod
    @data_analysis_bp.route('/')
    def dashboard():
        # Load guest data (you can replace this with the actual loading function)
        current_module = 'dashboard'

        # Retrieve year and month from the session
        filter_data = session.get('filter', {})
        year = filter_data.get('year')
        month = filter_data.get('month')

        df_guest = load_guest_data()

        if year and month:
            df_guest = total_guests(df_guest, year, month)

        month_name = month_mapping.get(month, None)  # Get the month name; default to None if not found

        if month_name:
            expenses_dict, monthname_year = load_dictionary_data('expenses', year, month)
            df_expenses = process_expenses(expenses_dict)
        else:
            expenses_dict, monthname_year = load_dictionary_data('expenses')
            df_expenses = process_expenses(expenses_dict)

        mode_data = session.get('mode', {})
        mode = mode_data.get('mode')

        if 'mode' not in mode_data:
            session['mode'] = {'mode': mode}

        chart_creator = DataChartCreator(df_guest, df_expenses, year, month, mode)
        graph_json = chart_creator.create_chart()

        return render_template("data_analysis.html", graph_json=graph_json, current_module=current_module)

    @staticmethod
    @data_analysis_bp.route('/filter_dashboard', methods=['POST'])
    def filter_dashboard():
        current_module = 'dashboard'

        # Retrieve the selected month and year from the form and save
        year, month = str(request.form['year']), str(request.form['month'])
        session['filter'] = {'year': year, 'month': month}

        mode_data = session.get('mode', {})
        mode = mode_data.get('mode', 'accounting')

        if 'mode' not in mode_data:
            session['mode'] = {'mode': mode}

        df_guest = load_guest_data()
        df_guest = total_guests(df_guest, year, month)

        month_name = month_mapping.get(month, None)  # Get the month name; default to None if not found

        if month_name:
            expenses_dict, monthname_year = load_dictionary_data('expenses', year, month)
            df_expenses = process_expenses(expenses_dict)
        else:
            expenses_dict, monthname_year = load_dictionary_data('expenses')
            df_expenses = process_expenses(expenses_dict)

        chart_creator = DataChartCreator(df_guest, df_expenses, year, month, mode)
        graph_json = chart_creator.create_chart()

        return render_template('data_analysis.html', year=year, month=month, tables=[df_guest], graph_json=graph_json,
                               current_module=current_module)

    @staticmethod
    @data_analysis_bp.route('/dashboard_mode', methods=['POST'])
    def dashboard_mode():
        current_module = 'dashboard'

        mode = request.form.get('mode', 'accounting')  # Default to accounting

        store_mode_data(mode)

        # Get year, month, and mode from the query parameters (no need to save it in session here!)
        filter_data = session.get('filter', {})
        year = filter_data.get('year')
        month = filter_data.get('month')

        df_guest = load_guest_data()
        if year and month:
            df_guest = total_guests(df_guest, year, month)

        month_name = month_mapping.get(month, None)

        if month_name:
            expenses_dict, monthname_year = load_dictionary_data('expenses', year, month)
            df_expenses = process_expenses(expenses_dict)
        else:
            expenses_dict, monthname_year = load_dictionary_data('expenses')
            df_expenses = process_expenses(expenses_dict)

        chart_creator = DataChartCreator(df_guest, df_expenses, year, month, mode)
        graph_json = chart_creator.create_chart()

        return render_template("data_analysis.html", graph_json=graph_json, current_module=current_module,
                               year=year, month=month, mode=mode)
