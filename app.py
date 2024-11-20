from flask import Flask, render_template, request, redirect, url_for, session

from routes.guests import guests_bp
from routes.expenses import expenses_bp
from routes.settlement import settlement_bp
from routes.data_analysis import data_analysis_bp
from utils.helpers import store_filter_data

app = Flask(__name__)
app.secret_key = 'your_secret_key'


@app.route('/')
def home():
    return redirect(url_for('guests.show_guests'))


app.register_blueprint(guests_bp, url_prefix='/guests')
app.register_blueprint(expenses_bp, url_prefix='/expenses')
app.register_blueprint(settlement_bp, url_prefix='/settlement')
app.register_blueprint(data_analysis_bp, url_prefix='/data_analysis')


if __name__ == '__main__':
    app.run(debug=True)
