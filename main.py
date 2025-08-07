from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# ✅ Your published Google Sheet CSV link
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vShgIQLk5ObcBTzPmZkQlzYsey33Z9ey59-z7N5kL_rbW-UjHv224ssD_lDXgWm8q8-QRcAqVHKweIZ/pub?gid=2053876350&single=true&output=csv"

def get_all_data():
    try:
        df = pd.read_csv(CSV_URL, dtype=str)
        df.fillna("", inplace=True)
        return df
    except Exception as e:
        print("Error reading CSV:", e)
        return pd.DataFrame()

def get_site_names(df):
    if 'Site Name' in df.columns:
        return sorted(df['Site Name'].dropna().unique())
    return []

def get_summary_for_site(df, site_name):
    if 'Site Name' in df.columns:
        match = df[df['Site Name'].str.strip() == site_name.strip()]
        return match.iloc[0].to_dict() if not match.empty else None
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
   def index():
    df = get_all_data()
    selected_date = None
    summary = None

    if request.method == 'POST':
        selected_date = request.form.get('date')
        if selected_date:
            # Assuming your CSV has a column 'Date' in DD-MM-YYYY format
            match = df[df['Date'] == selected_date]
            summary = match.iloc[0].to_dict() if not match.empty else None

    return render_template(
        'index.html',
        selected_date=selected_date,
        summary=summary
