from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# Your published CSV link
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vShgIQLk5ObcBTzPmZkQlzYsey33Z9ey59-z7N5kL_rbW-UjHv224ssD_lDXgWm8q8-QRcAqVHKweIZ/pub?gid=2053876350&single=true&output=csv"

def get_all_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.fillna("", inplace=True)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        return df
    except Exception as e:
        print("Error loading CSV:", e)
        return pd.DataFrame()

@app.route('/', methods=['GET', 'POST'])
def index():
    df = get_all_data()
    selected_date = None
    summary = None

    if request.method == 'POST':
        selected_date = request.form.get('date')
        if selected_date:
            try:
                selected_date_obj = pd.to_datetime(selected_date).date()
                match = df[df['Date'] == selected_date_obj]
                summary = match.iloc[0].to_dict() if not match.empty else None
            except Exception as e:
                print("Date parsing error:", e)

    return render_template('index.html', selected_date=selected_date, summary=summary)

if __name__ == '__main__':
    app.run(debug=True)
