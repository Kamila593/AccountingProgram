month_mapping = {
    '01': 'January',
    '02': 'February',
    '03': 'March',
    '04': 'April',
    '05': 'May',
    '06': 'June',
    '07': 'July',
    '08': 'August',
    '09': 'September',
    '10': 'October',
    '11': 'November',
    '12': 'December'
}
month_words = list(month_mapping.values())
month_numbers = list(month_mapping.keys())

colours = ['#fec2b1', '#afd2fe', '#7f9391', '#fbf895', '#ffade6', '#b6e6d2', '#c998f7', '#ffaa00', '#d5ea6b',
           '#3de59b', '#cdf1d4', '#bbfbf1', '#7394f1', '#ffc292', '#e830b9', '#ffd94d']

columns_guests = [
    'Guest', 'Date', 'Check-out', 'Payday', 'Standard', 'Number of people', 'Multiplier', 'Offer',
    'Genius', 'Total Promotion',
    'Total Promotion %', 'Daily Rate', 'Total Price', 'Commission %', 'Commission', 'Transaction Fee',
    'Commission + Fee',
    'Total Commission + Fee', 'Paycheck', 'VAT 8%', 'VAT 23%', 'Netto']

columns_expenses = [
    'Shopping Name', 'Shopping Price', 'Shopping VAT %', 'Shopping VAT', 'Shopping Netto',
    'Apartment Name', 'Apartment Price', 'Apartment VAT %', 'Apartment VAT', 'Apartment Netto',
    'Company Fees Name', 'Company Fees Price', 'Company Fees VAT %', 'Company Fees VAT', 'Company Fees Netto'
]

columns_settlement = {
    "VAT": [
        {
            "Payable": 0,
            "Deductible": 0,
            "Settlement": 0,
            "Surplus": 0
        }
    ],
    "Income Settlement": [
        {
            "Total Sales": 0,
            "Revenue": 0,
            "Expenses Net": 0,
            "Tax base": 0,
            "Income tax": 0,
            "Net profit": 0
        }
    ],
    "ZUS": [
        {
            "Retirement Insurance": 0,
            "Disability Insurance": 0,
            "Sickness Insurance": 0,
            "Accident Insurance": 0,
            "Labour Fund": 0,
            "Health Insurance": 0
        }
    ]
}
