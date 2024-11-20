from flask import Blueprint, request, render_template, redirect, url_for, session
import json
from utils.data_reading import load_guest_data, guests_by_column, total_guests
from utils.helpers import store_filter_data
import pandas as pd

guests_bp = Blueprint('guests', __name__, template_folder='templates')


class Guests:
    @staticmethod
    @guests_bp.route('/')
    def show_guests():
        """Render guest data with merged cells for total price in guests.html template."""
        current_module = 'guests'

        df_guest = load_guest_data()
        df_guest = df_guest.fillna('')

        # Convert the Date column to datetime
        df_guest['Date'] = pd.to_datetime(df_guest['Date'], format='%Y-%m-%d').dt.date
        df_guest = df_guest.sort_values(by='Date')  # Ascending order (from oldest to most recent)

        # Retrieve year and month from the session
        filter_data = session.get('filter', {})
        year = filter_data.get('year')
        month = filter_data.get('month')

        if not filter_data:
            most_recent_date = df_guest['Date'].max()
            year = most_recent_date.year
            month = f"{most_recent_date.month:02d}"
            filter_data = {'year': str(year), 'month': month}
            session['filter'] = filter_data

        if year and month:
            df_guest = total_guests(df_guest, year, month)

        df_guest['row_position_in_group'] = df_guest.groupby('Guest').cumcount()
        df_guest['group_size'] = df_guest.groupby('Guest')['Guest'].transform('size')

        return render_template('guests.html', tables=[df_guest], current_module=current_module, year=year, month=month)

    @staticmethod
    @guests_bp.route('/add_guest_form')
    def add_guest_form():
        """Render the form to add a new guest."""
        return render_template('add_guest.html')

    @staticmethod
    @guests_bp.route('/add_guest', methods=['POST'])
    def add_guest():
        """Process the new guest data, calculate fields, and update JSON file."""

        # Load the existing guest data from JSON
        with open('data_source/data.json', 'r') as file:
            guest_data = json.load(file)

        new_guest_entry = {
            "Date": request.form['date'],
            "Guest": request.form['guest'],
            "Standard": float(request.form['standard']),
            "Number of people": int(request.form['number_of_people']),
            "Offer": request.form['offer'],
            "Genius": request.form['genius'],
            "Commission %": request.form['commission']
        }

        guest_data.append(new_guest_entry)

        # Save updated data back to JSON
        with open('data_source/data.json', 'w') as file:
            json.dump(guest_data, file, indent=4)

        # Redirect to guest list page
        return redirect(url_for('guests.show_guests'))

    @staticmethod
    @guests_bp.route('/filter_guests', methods=['POST'])
    def filter_guests():
        """Filter the guest list by year and month."""
        current_module = 'guests'

        df = load_guest_data()
        df = df.fillna('')
        df = df.sort_values(by='Date')

        # Retrieve the selected month and year from the form
        year, month = str(request.form['year']), str(request.form['month'])

        # Store filter data in session
        store_filter_data(year, month)

        filtered_data = total_guests(df, year, month)

        filtered_data['row_position_in_group'] = filtered_data.groupby('Guest').cumcount()
        filtered_data['group_size'] = filtered_data.groupby('Guest')['Guest'].transform('size')

        return render_template('guests.html', year=year, month=month, tables=[filtered_data],
                               current_module=current_module)
