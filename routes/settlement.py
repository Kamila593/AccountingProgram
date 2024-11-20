from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify
import json
import numpy as np
import pandas as pd
from utils.data_reading import load_guest_data, load_dictionary_data, process_settlement, calculate_settlement, \
    total_guests, guests_by_column
from utils.data_mapping import month_mapping, columns_settlement, month_numbers, month_words
from utils.helpers import store_filter_data
import os

settlement_bp = Blueprint('settlement', __name__, template_folder='templates')


class MakeSettlement:
    path_json = 'data_source/settlement.json'

    @staticmethod
    @settlement_bp.route('/')
    def settlement():
        current_module = 'settlement'

        # Retrieve year and month from the session
        filter_data = session.get('filter', {})
        year, month = filter_data.get('year'), filter_data.get('month')

        if year and month:
            vat_data = calculate_settlement('accounting', year, month)
        else:
            vat_data = calculate_settlement('accounting')

        return render_template('settlement.html', title="VAT Settlement", vat_data=vat_data,
                               filter_data=filter_data, current_module=current_module)

    @staticmethod
    @settlement_bp.route('/filter_settlement', methods=['POST'])
    def filter_settlement():
        current_module = 'settlement'

        year = str(request.form['year'])  # Retrieve the selected month and year from the form
        month = str(request.form['month'])

        store_filter_data(year, month)  # Store filter data in session

        vat_data = calculate_settlement('accounting', year, month)

        return render_template('settlement.html', title="Settlement", vat_data=vat_data,
                               filter_data=vat_data, current_module=current_module)

    @staticmethod
    def save_settlement_to_file(year, month, settlement_data):
        # Create the month key for the JSON
        monthname = month_mapping.get(month)
        monthname_year = f'{monthname} {year}'  # E.g. 'February 2024' (recent)

        json_file_path = 'data_source/settlement.json'

        # Load existing data from JSON
        with open(json_file_path, 'r') as file:
            settlement_data_json = json.load(file)

        # Update or create the entry for the given month and year
        settlement_data_json[monthname_year] = settlement_data

        # Write the updated data back to the JSON file
        with open(json_file_path, 'w') as file:
            json.dump(settlement_data_json, file, indent=4)

    @staticmethod
    @settlement_bp.route('/save_to_file', methods=['POST'])
    def save_to_file():
        try:
            # Retrieve the data from the JSON request
            data = request.get_json()

            # Extract year and month
            year = data.get('year')
            month = data.get('month')
            settlement_data = data.get('settlement_data')

            if not year or not month or not settlement_data:
                return jsonify({"message": "Invalid data"}), 400

            # Create the month key for the JSON
            monthname = month_mapping.get(month, "Unknown Month")
            monthname_year = f'{monthname} {year}'  # E.g. 'February 2024'

            # Load existing data from JSON
            json_file_path = 'data_source/settlement.json'

            if not os.path.exists(json_file_path):
                # If file doesn't exist, create an empty dictionary
                settlement_data_json = {}
            else:
                with open(json_file_path, 'r') as file:
                    settlement_data_json = json.load(file)

            # Update or create the entry for the given month and year
            settlement_data_json[monthname_year] = settlement_data

            # Write the updated data back to the JSON file
            with open(json_file_path, 'w') as file:
                json.dump(settlement_data_json, file, indent=4)

            return jsonify({"message": "Data saved successfully"}), 200

        except Exception as e:
            # Log the error for debugging
            print(f"Error saving data: {e}")
            return jsonify({"message": "Failed to save data"}), 500
