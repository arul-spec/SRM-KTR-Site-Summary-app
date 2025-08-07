from flask import Flask, render_template, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Replace with your actual Google Sheet name
sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/e/2PACX-1vShgIQLk5ObcBTzPmZkQlzYsey33Z9ey59-z7N5kL_rbW-UjHv224ssD_lDXgWm8q8-QRcAqVHKweIZ/pub?gid=2053876350&single=true&output=csv').sheet1

def get_site_names():
    records = sheet.get_all_records()
    site_names = sorted(set(row['Site Name'] for row in records if row['Site Name']))
    return site_names

def get_summary(site_name):
    records = sheet.get_all_records()
    for row in records:
        if row['Site Name'] == site_name:
            return row
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    summary = None
    selected_site = None
    site_names = get_site_names()

    if request.method == 'POST':
        selected_site = request.form.get('site')
        summary = get_summary(selected_site)

    return render_template("index.html", summary=summary, site_names=site_names, selected_site=selected_site)

if __name__ == '__main__':
    app.run(debug=True)
