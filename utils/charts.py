import pandas as pd
from pandas import to_datetime
import json
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
import plotly.express as px
from plotly.subplots import make_subplots
import calendar
from PIL import Image, ImageDraw, ImageOps, ImageEnhance, ImageFont
import io
import base64
from utils.helpers import store_filter_data, store_mode_data
from utils.data_reading import load_guest_data, load_dictionary_data, process_expenses, process_settlement, \
    total_guests, guests_by_column, calculate_settlement
from utils.data_mapping import colours, columns_guests

STANDARD_TITLE_STYLE = {
    "font": {
        "family": "Open Sans, sans-serif",  # Set the font to match the indicator's font
        "size": 22,
        "color": "black"
    }
}


def create_clipped_image(occupancy_rate):
    """Creates an occupancy rate visual in-memory and returns it."""
    # Load base image
    input_image_path = 'utils/suitcases.png'
    img = Image.open(input_image_path)

    # Calculate new image dimensions based on occupancy percentage
    width, height = img.size
    new_width = int(width * occupancy_rate)

    # Create image parts: cropped (filled) and remaining (greyed out)
    cropped_img = img.crop((0, 0, new_width, height))
    remaining_img = img.crop((new_width, 0, width, height))

    # Convert remaining part to grayscale and adjust contrast
    remaining_bw = ImageOps.grayscale(remaining_img)
    remaining_bw_rgb = remaining_bw.convert("RGB")

    white_overlay = Image.new("RGB", remaining_bw_rgb.size, (255, 255, 255))
    remaining_blended = Image.blend(remaining_bw_rgb, white_overlay, alpha=0.75)

    # Merge the cropped and remaining parts
    loadbar_img = Image.new("RGB", (width, height))
    loadbar_img.paste(cropped_img, (0, 0))
    loadbar_img.paste(remaining_blended, (new_width, 0))

    # Load and resize circle overlay
    circle = Image.open("utils/circle_percentage.png").convert("RGBA")
    new_circle_size = (int(circle.width * 1.25), int(circle.height * 1.25))
    circle = circle.resize(new_circle_size, Image.LANCZOS)

    # Calculate position for overlaying circle
    circle_x = (width - circle.size[0]) // 2
    circle_y = (height - circle.size[1]) // 2

    # Create final image and add occupancy percentage text
    final_img = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    final_img.paste(loadbar_img, (0, 0))
    final_img.paste(circle, (circle_x, circle_y), circle)

    # Add occupancy rate text
    font = ImageFont.truetype("verdanab.ttf", 115)
    draw = ImageDraw.Draw(final_img)
    occupancy_text = f"{int(occupancy_rate * 100)}%"

    bbox = draw.textbbox((0, 0), occupancy_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (width - text_width) / 2
    text_y = (height - text_height) / 2 - 30
    draw.text((text_x, text_y), occupancy_text, fill="black", font=font)

    return final_img


def generate_x_values(base_position, group, spacing, bar_width):
    num_ticks = len(group)
    total_width = (num_ticks - 1) * spacing
    start_x = base_position + (bar_width / 2) - (total_width / 2)
    return [start_x + i * spacing for i in range(num_ticks)]


def create_vertical_lines(x_positions, y_values, color, name):
    lines = []
    for x, y in zip(x_positions, y_values):
        lines.append(go.Scatter(
            x=[x, x],  # Same x-position to create a vertical line
            y=[0, y],  # Line from y=0 to the reservation length
            mode='lines',
            line=dict(width=3, color=color),
            name=name,
            showlegend=False  # Disable multiple legends
        ))
    return lines


def guests_and_their_days(df, n):
    df = df[df['Number of people'] == n]
    n_guests = list(df['Guest'])
    n_days = {}
    for guest in n_guests:
        if guest in n_days:
            n_days[guest] += 1
        else:
            n_days[guest] = 1

    return n_days


class DataChartCreator:
    def __init__(self, df_guest, df_expenses, year, month, mode=None):  # Default mode to None
        # Set default mode to 'accounting' if no mode is provided
        self.mode = mode if mode in ['accounting', 'reservation'] else 'accounting'

        # Assign guest, expenses, year, and month data
        self.df_guest = df_guest
        self.df_expenses = df_expenses
        self.year = year
        self.month = month

        # Initialize the guest DataFrames based on the mode
        if self.mode == 'accounting':
            self.df_guest_date = guests_by_column(df_guest, 'Date', year, month)
            self.df_guest_check_out = guests_by_column(df_guest, 'Check-out', year, month)
            self.df_guest_payday = guests_by_column(df_guest, 'Payday', year, month)
            self.vat_data = calculate_settlement('accounting', year, month)
        elif self.mode == 'reservation':
            self.df_guest_date = guests_by_column(df_guest, 'Date', year, month)
            self.df_guest_check_out = self.df_guest_date
            self.df_guest_payday = self.df_guest_date
            self.vat_data = calculate_settlement('reservation', year, month)

        if self.df_guest_payday.empty:
            self.df_guest_payday = pd.DataFrame(columns=columns_guests)

    # 1 1
    def create_price_share_pie(self):
        values = [
            round((self.df_guest_payday['Daily Rate'].sum() - self.df_guest_payday['Commission'].sum() - self.df_guest_payday['Transaction Fee'].sum()), 2),
            round(self.df_guest_check_out['Commission'].sum(), 2),
            round(self.df_guest_check_out['Transaction Fee'].sum(), 2)
        ]

        labels = ['Paycheck', 'Commission', 'Transaction Fee']
        return go.Pie(labels=labels, values=values, hole=.4, marker=dict(colors=colours[0:3]))

    # 1 2
    def create_total_sold_nights_indicator(self):
        total_nights = self.df_guest_date['Date'].count()
        return go.Indicator(
            mode="number",
            value=total_nights,
            domain={'x': [0, 1], 'y': [0, 1]}
        )

    # 1 3
    def create_expenses_pie(self):
        values = [
            round(self.df_expenses['Shopping Price'].sum(), 2),
            round(self.df_expenses['Apartment Price'].sum(), 2),
            round(self.df_expenses['Company Fees Price'].sum(), 2)
        ]
        labels = ['Shopping Gross', 'Apartment Bills Gross', 'Company Fees Gross']
        return go.Pie(labels=labels, values=values, hole=.4, marker=dict(colors=colours[3:6]))

    # 2 2
    def create_occupancy_rate_image(self, fig, row, col):
        """Adds occupancy rate image to the chart."""
        month_int = int(self.month)
        year_int = int(self.year)

        days_in_month = calendar.monthrange(year_int, month_int)[1]
        total_nights = self.df_guest_date['Date'].count()
        occupancy_rate = total_nights / days_in_month

        # Create occupancy image in memory and convert to URI for plotly
        occupancy_img = create_clipped_image(occupancy_rate)
        buffered = io.BytesIO()
        occupancy_img.save(buffered, format="PNG")
        img_data = buffered.getvalue()
        img_uri = "data:image/png;base64," + base64.b64encode(img_data).decode('utf-8')

        # Add occupancy rate image to the plot
        fig.add_layout_image(
            dict(
                source=img_uri,
                xref="paper",
                yref="paper",
                x=2.55,
                y=7.2,
                sizex=4.2,
                sizey=7.2,
                xanchor="center",
                layer="below"
            ),
            row=row, col=col
        )

        # Hide x and y axes
        fig.update_xaxes(visible=False, range=[2.1, 3], row=row, col=col)
        fig.update_yaxes(visible=False, range=[0, 7.2], row=row, col=col)

    # 3 1
    def create_number_of_reservations(self):
        df_guest_sorted = self.df_guest_payday[['Date', 'Guest']].copy()
        df_guest_sorted = df_guest_sorted.sort_values(by=['Guest', 'Date'])

        guests = list(df_guest_sorted['Guest'])
        guests_no_repetition = set(guests)
        number_of_reservations = len(guests_no_repetition)

        return go.Indicator(
            mode="number",
            value=number_of_reservations,
            number={"valueformat": ".0f"},
            domain={'x': [0, 1], 'y': [0, 0]}
        )

    # 3 2
    def create_total_sales_distribution(self):
        insurance = self.vat_data['Insurance']
        tax_base = self.vat_data['Tax Base']

        which_surplus = self.vat_data['Which Surplus']
        month_vat = self.vat_data['Month VAT']
        previous_surplus = self.vat_data['Ex-Surplus']
        vat_to_pay = self.vat_data['VAT to pay']

        if which_surplus == 'deductible':
            values = [
                self.df_guest_payday['Commission'].sum(),
                self.df_guest_payday['Transaction Fee'].sum(),
                self.df_expenses['Shopping Price'].sum(),
                self.df_expenses['Apartment Price'].sum(),
                self.df_expenses['Company Fees Price'].sum(),
                insurance,
                tax_base
            ]
            labels = ['Commission', 'Transaction Fee', 'Shopping Gross', 'Apartment Bills Gross', 'Company Fees Gross',
                      'Insurance', 'Net Profit']
            colour_list = [colours[1], colours[2], colours[3], colours[4], colours[5],
                           colours[11], colours[6]]
        elif which_surplus == 'payable' and previous_surplus >= month_vat:
            values = [
                self.df_guest_payday['Commission'].sum(),
                self.df_guest_payday['Transaction Fee'].sum(),
                self.df_expenses['Shopping Price'].sum(),
                self.df_expenses['Apartment Price'].sum(),
                self.df_expenses['Company Fees Price'].sum(),
                insurance,
                tax_base,
                month_vat
            ]
            labels = ['Commission', 'Transaction Fee', 'Shopping Gross', 'Apartment Bills Gross', 'Company Fees Gross',
                      'Insurance', 'Net Profit', 'VAT Covered']
            colour_list = [colours[1], colours[2], colours[3], colours[4], colours[5],
                           colours[11], colours[6], colours[12]]
        elif which_surplus == 'payable' and previous_surplus < month_vat:
            values = [
                self.df_guest_payday['Commission'].sum(),
                self.df_guest_payday['Transaction Fee'].sum(),
                self.df_expenses['Shopping Price'].sum(),
                self.df_expenses['Apartment Price'].sum(),
                self.df_expenses['Company Fees Price'].sum(),
                insurance,
                tax_base,
                previous_surplus,
                vat_to_pay
            ]
            labels = ['Commission', 'Transaction Fee', 'Shopping Gross', 'Apartment Bills Gross', 'Company Fees Gross',
                      'Insurance', 'Net Profit', 'VAT Covered', 'VAT to pay']
            colour_list = [colours[1], colours[2], colours[3], colours[4], colours[5],
                           colours[11], colours[6], colours[15], colours[12]]

        return go.Pie(labels=labels, values=values, hole=.4, marker=dict(colors=colour_list))

    # 3 3
    def create_net_profit_indicator(self):
        net_profit = self.vat_data['Net Profit']

        return go.Indicator(
            mode="number",
            value=net_profit,
            domain={'x': [0, 1], 'y': [0, 0]}
        )

    # 4 1
    def create_tick_chart(self, fig, row, col):

        if self.df_guest_payday.empty:
            # If the DataFrame is empty, just skip the tick chart creation
            return

        first_dict = guests_and_their_days(self.df_guest_payday, 1)
        second_dict = guests_and_their_days(self.df_guest_payday, 2)
        third_dict = guests_and_their_days(self.df_guest_payday, 3)

        first_group = sorted(list(first_dict.values()))
        second_group = sorted(list(second_dict.values()))
        third_group = sorted(list(third_dict.values()))

        max_ticks = max(len(first_group), len(second_group), len(third_group))

        bar_width = 1.0
        margin = 0.05 * bar_width
        spacing = (bar_width - 2 * margin) / max_ticks

        # Base positions for each group to align with the bars
        base_first = 0
        base_second = 1.5
        base_third = 3.0

        first_x = generate_x_values(base_first, first_group, spacing, bar_width)
        second_x = generate_x_values(base_second, second_group, spacing, bar_width)
        third_x = generate_x_values(base_third, third_group, spacing, bar_width)

        # Add vertical lines for each reservation group
        first_ticks = create_vertical_lines(first_x, first_group, colours[12], '1 Person Reservations')
        second_ticks = create_vertical_lines(second_x, second_group, '#d17fd3', '2 People Reservations')
        third_ticks = create_vertical_lines(third_x, third_group, 'purple', '3 People Reservations')

        bar_x = [base_first + bar_width / 2, base_second + bar_width / 2, base_third + bar_width / 2]

        # Add tick lines to fig
        for tick in first_ticks + second_ticks + third_ticks:
            fig.add_trace(tick, row=row, col=col)

        # Update layout for bar and tick chart
        fig.update_xaxes(
            tickvals=bar_x,
            ticktext=['1 Person', '2 People', '3 People'],
            range=[-0.5, base_third + bar_width + 0.5],
            showgrid=False,
            showline=False,
            zeroline=False,
            row=4, col=1
        )

        fig.update_yaxes(
            title='Number of Nights',
            title_text="Number Of Nights",
            title_font=dict(size=12),
            title_standoff=0,
            automargin=True,
            showline=False,
            zeroline=False,
            row=4, col=1
        )

    # 4 3
    def create_total_sales(self):
        total_sales = self.df_guest_payday['Total Price'].sum()
        return go.Indicator(
            mode="number",
            value=total_sales,
            number={"valueformat": ".0f"},
            domain={'x': [0, 1], 'y': [0, 0]}
        )

    # 5 1
    def create_number_of_people_per_night(self):
        counts = self.df_guest_payday['Number of people'].value_counts().sort_index()
        bar_colors = [colours[12], '#d17fd3', 'purple']

        return go.Bar(
            x=['1 Person', '2 People', '3 People'],
            y=counts.values,
            name="Number of Nights",
            marker=dict(color=bar_colors),
            text=counts.values,
            textposition='outside',
            showlegend=False
        )

    # 5 2
    def create_people_per_day_of_the_week(self):
        dates = list(self.df_guest_payday['Date'])
        dates_series = pd.to_datetime(dates)
        days_of_week = dates_series.day_name()
        nights_sold = days_of_week.value_counts().reindex(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        )

        return go.Bar(
            x=nights_sold.index,
            y=nights_sold.values,
            name='Nights Sold per Day of the Week',
            marker=dict(color=colours[14]),
            text=nights_sold.values,
            textposition='outside',
            showlegend=False
        )

    # 5 3
    def create_average_daily_rate_chart(self):
        avg_daily_rate = self.df_guest_payday.groupby('Number of people')['Daily Rate'].mean().round(2)
        return go.Bar(
            x=['1 Person', '2 People', '3 People'],
            y=avg_daily_rate.values,
            name="Average Daily Rate",
            marker=dict(color='#36f0c2'),
            text=avg_daily_rate.values,
            textposition='outside',
            showlegend=False
        )

    def create_chart(self):
        # Create the grid layout with 3 rows and 3 columns
        fig = make_subplots(
            rows=6, cols=3,
            subplot_titles=("Price Breakdown", "Total Nights Occupied", "Gross Expenses Distribution",
                            "Occupancy Rate",
                            "Total Reservations", "Real Cash Flow", "Net Profit",
                            "Length of stay per Guest Count", "Total Sales",
                            "Total Nights by Guest Count", "Occupancy per Day of the Week", "Average Daily Rate",
                            ),
            specs=[[{"type": "pie", "rowspan": 2}, {"type": "indicator"}, {"type": "pie", "rowspan": 2}],
                   [None, {"type": "xy"}, None],
                   [{"type": "indicator"}, {"type": "pie", "rowspan": 2}, {"type": "indicator"}],
                   [{"type": "xy"}, None, {"type": "indicator"}],
                   [{"type": "xy", "rowspan": 2}, {"type": "xy", "rowspan": 2}, {"type": "xy", "rowspan": 2}],
                   [None, None, None]
                   ]
        )

        for annotation in fig['layout']['annotations']:
            if annotation['text'] is not None:  # Only update non-empty titles
                annotation['font'] = STANDARD_TITLE_STYLE["font"]
                annotation['y'] += 0.015

        # 1 1 Add Price Share Pie Chart
        fig.add_trace(self.create_price_share_pie(), row=1, col=1)

        # 1 2 Add Total Sold Nights Indicator
        fig.add_trace(self.create_total_sold_nights_indicator(), row=1, col=2)

        # 1 3 Add Expenses Pie Chart
        fig.add_trace(self.create_expenses_pie(), row=1, col=3)

        # 2 2 Add Occupancy Rate Image
        # fig.add_trace(self.create_occupancy_rate_image(fig, row=2, col=2))
        self.create_occupancy_rate_image(fig, row=2, col=2)

        # 3 1 Add Number of Reservations
        fig.add_trace(self.create_number_of_reservations(), row=3, col=1)

        # 3 2 Add Total Sales Distribution
        fig.add_trace(self.create_total_sales_distribution(), row=3, col=2)

        # Add Net Profit Indicator
        fig.add_trace(self.create_net_profit_indicator(), row=3, col=3)

        # Add Tick Bar Chart
        self.create_tick_chart(fig, row=4, col=1)

        # Add Total Sales Indicator
        fig.add_trace(self.create_total_sales(), row=4, col=3)

        # 5 1 Add Number Of Nights Per Number Of People
        if self.df_guest_payday.empty:
            return
        else:
            fig.add_trace(self.create_number_of_people_per_night(), row=5, col=1)
            counts = self.df_guest_payday['Number of people'].value_counts().sort_index()
            y_max_night = max(counts.values)
            y_add_night = max(1, y_max_night // 5)
            fig.update_yaxes(
                title_text="Number of Nights",
                title_font=dict(size=12),
                title_standoff=0,
                automargin=True,
                range=[0, y_max_night + y_add_night],
                row=5, col=1
            )

        # 5 2 Add People Per Day Of The Week
        fig.add_trace(self.create_people_per_day_of_the_week(), row=5, col=2)
        dates = list(self.df_guest_payday['Date'])
        dates_series = pd.to_datetime(dates)
        days_of_week = dates_series.day_name()
        nights_sold = days_of_week.value_counts().reindex(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        )
        y_max_week = np.nanmax(np.array(nights_sold.values))
        y_add_week = max(1, y_max_week // 5)
        fig.update_yaxes(
            title_text="Number of Nights",
            title_font=dict(size=12),
            title_standoff=0,
            automargin=True,
            range=[0, y_max_week + y_add_week],
            row=5, col=2
        )

        # 5 3 Add Average Daily Rate Chart
        fig.add_trace(self.create_average_daily_rate_chart(), row=5, col=3)
        avg_daily_rate = self.df_guest_payday.groupby('Number of people')['Daily Rate'].mean().round(2)
        y_max_rate = max(avg_daily_rate.values)
        y_add_rate = y_max_rate // 5
        fig.update_yaxes(
            title_text="Daily Rate",
            title_font=dict(size=12),
            title_standoff=0,
            automargin=True,
            range=[0, y_max_rate + y_add_rate],
            row=5, col=3
        )

        # The end
        # Update the layout for readability
        fig.update_layout(
            height=1000,
            margin=dict(l=10, r=10, t=40, b=10),
            showlegend=True,
            plot_bgcolor='#eedcf8'
        )

        # Convert the figure to JSON to pass to the front end
        graph_json = json.dumps(fig, cls=PlotlyJSONEncoder)
        return graph_json

