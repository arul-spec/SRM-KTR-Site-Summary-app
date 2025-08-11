from flask import Flask, render_template, request
import pandas as pd
import html

app = Flask(__name__)

# === Replace with your two published CSV links ===
CSV_URL_REPORTED = "https://docs.google.com/spreadsheets/d/e/2PACX-1vROsAZADl0n9kUVDkJbZQK-vbjMhb4lqyFNoGxGWiOcJsbAIYg40TtMNX7kuX_LdFtvobPi5A6z_TM9/pubhtml?gid=885148516&single=true"
CSV_URL_BILLABLE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vShgIQLk5ObcBTzPmZkQlzYsey33Z9ey59-z7N5kL_rbW-UjHv224ssD_lDXgWm8q8-QRcAqVHKweIZ/pubhtml?gid=2053876350&single=true"

# Helper: load CSV as strings to avoid dtype issues
def load_csv(url):
   import requests, csv, io, pandas as pd

def load_csv(url):
    try:
        text = requests.get(url, timeout=15).text
    except Exception as e:
        print("Error fetching CSV:", e)
        return pd.DataFrame()

    # Try csv.DictReader (handles quoted fields/newlines well if CSV is valid)
    try:
        f = io.StringIO(text)
        reader = csv.DictReader(f)
        rows = list(reader)  # if this fails, exception raised
        df = pd.DataFrame(rows).astype(str).fillna("")
        df.columns = [c.strip() for c in df.columns]
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        return df
    except Exception as e_csv:
        print("csv.DictReader failed:", e_csv)
        # Attempt to detect problematic lines for debugging
        lines = text.splitlines()
        header_len = len(lines[0].split(','))
        bad = []
        for i, line in enumerate(lines[1:], start=2):
            if line.count(',') + 1 != header_len:
                bad.append((i, line[:300]))  # show line number + a snippet
                if len(bad) >= 10:
                    break
        print("Detected suspicious lines (line_no, snippet):", bad[:10])

    # Final fallback: pandas with python engine and skip bad lines
    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, engine='python', on_bad_lines='skip')
        df.fillna("", inplace=True)
        df.columns = [c.strip() for c in df.columns]
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        return df
    except Exception as e_pd:
        print("Pandas fallback failed:", e_pd)
        return pd.DataFrame()

# Derive list of sites and ticket ids
def site_and_tickets(reported_df, billable_df):
    ticket_set = set()
    site_set = set()

    for df in (reported_df, billable_df):
        if df.empty:
            continue
        if 'Ticket ID' in df.columns:
            ticket_set.update(df['Ticket ID'].astype(str).str.strip().tolist())
        if 'Site Name' in df.columns:
            site_set.update(df['Site Name'].astype(str).str.strip().tolist())

    ticket_ids = sorted([t for t in ticket_set if t])  # remove blanks
    site_names = sorted([s for s in site_set if s])
    return site_names, ticket_ids

# Determine comparable numeric fields automatically (common columns excluding identifiers)
def find_comparable_fields(reported_df, billable_df):
    exclude = {'Ticket ID', 'Site Name', 'Date', 'Remarks', 'Comments', 'Timestamp'}
    rep_cols = set(reported_df.columns) if not reported_df.empty else set()
    bill_cols = set(billable_df.columns) if not billable_df.empty else set()
    common = sorted((rep_cols & bill_cols) - exclude)
    return common

# Convert a single value to numeric safely
def to_num(v):
    try:
        return float(str(v).replace(',', ''))  # handle commas
    except:
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    reported_df = load_csv(CSV_URL_REPORTED)
    billable_df = load_csv(CSV_URL_BILLABLE)

    site_names, ticket_ids = site_and_tickets(reported_df, billable_df)
    comparable_fields = find_comparable_fields(reported_df, billable_df)

    action = None
    selected_ticket = None
    selected_site = None
    comparison = None
    all_table = None

    if request.method == "POST":
        action = request.form.get("action")
        selected_site = request.form.get("site") or None
        selected_ticket = request.form.get("ticket") or None

        # If site selected, filter ticket dropdown client-side is also provided in template,
        # but here we can additionally restrict when showing "All"
        if action == "compare" and selected_ticket:
            # Find rows for this ticket
            rep_row = reported_df[reported_df['Ticket ID'].astype(str).str.strip() == selected_ticket]
            bill_row = billable_df[billable_df['Ticket ID'].astype(str).str.strip() == selected_ticket]

            # Build comparison dict
            comparison = {
                'Ticket ID': selected_ticket,
                'Site': None,
                'Reported': {},
                'Billable': {},
                'Deviation': {}
            }

            # pick site from either row
            if not rep_row.empty and 'Site Name' in rep_row.columns:
                comparison['Site'] = rep_row.iloc[0].get('Site Name', '') or comparison['Site']
            if not bill_row.empty and 'Site Name' in bill_row.columns:
                comparison['Site'] = bill_row.iloc[0].get('Site Name', '') or comparison['Site']

            # collect all relevant fields (union of columns) but prioritize comparable fields for numeric dev
            all_keys = sorted(set(reported_df.columns.tolist() + billable_df.columns.tolist()))
            for k in all_keys:
                if k in ('Ticket ID', 'Site Name'):
                    continue
                rep_val = rep_row.iloc[0][k] if (not rep_row.empty and k in rep_row.columns) else ""
                bill_val = bill_row.iloc[0][k] if (not bill_row.empty and k in bill_row.columns) else ""

                # Try compute numeric deviation if field in comparable_fields
                if k in comparable_fields:
                    rep_num = to_num(rep_val)
                    bill_num = to_num(bill_val)
                    dev = None
                    if rep_num is None and bill_num is None:
                        dev = ""
                    else:
                        rep_n = rep_num or 0.0
                        bill_n = bill_num or 0.0
                        dev = bill_n - rep_n
                    comparison['Reported'][k] = rep_val
                    comparison['Billable'][k] = bill_val
                    comparison['Deviation'][k] = dev
                else:
                    # Non-numeric or non comparable fields: show as-is (no deviation)
                    if rep_val or bill_val:
                        comparison['Reported'][k] = rep_val
                        comparison['Billable'][k] = bill_val
            # end for keys

        elif action == "all":
            # Build merged table (outer merge) on Ticket ID
            if 'Ticket ID' in reported_df.columns or 'Ticket ID' in billable_df.columns:
                rep = reported_df.copy()
                bill = billable_df.copy()
                # ensure Ticket ID present in both as str
                if 'Ticket ID' not in rep.columns:
                    rep['Ticket ID'] = ""
                if 'Ticket ID' not in bill.columns:
                    bill['Ticket ID'] = ""
                rep['Ticket ID'] = rep['Ticket ID'].astype(str).str.strip()
                bill['Ticket ID'] = bill['Ticket ID'].astype(str).str.strip()

                merged = pd.merge(rep, bill, on='Ticket ID', how='outer', suffixes=('_rep', '_bill'))

                # compute deviations for comparable fields
                dev_cols = []
                for col in comparable_fields:
                    col_rep = f"{col}_rep"
                    col_bill = f"{col}_bill"
                    # ensure columns exist
                    if col_rep not in merged.columns:
                        merged[col_rep] = ""
                    if col_bill not in merged.columns:
                        merged[col_bill] = ""
                    # compute numeric versions
                    merged[f"{col}_rep_num"] = pd.to_numeric(merged[col_rep].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
                    merged[f"{col}_bill_num"] = pd.to_numeric(merged[col_bill].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
                    merged[f"{col}_dev"] = merged[f"{col}_bill_num"] - merged[f"{col}_rep_num"]
                    dev_cols.append(col)

                # Optionally filter by site
                if selected_site:
                    if 'Site Name_rep' in merged.columns:
                        merged = merged[merged['Site Name_rep'].astype(str).str.strip() == selected_site]
                    elif 'Site Name_bill' in merged.columns:
                        merged = merged[merged['Site Name_bill'].astype(str).str.strip() == selected_site]

                # Convert to records for template
                all_table = {
                    'columns': ['Ticket ID', 'Site', *dev_cols],
                    'rows': []
                }
                for _, row in merged.iterrows():
                    site_val = ""
                    if 'Site Name_rep' in merged.columns and str(row.get('Site Name_rep','')).strip():
                        site_val = row.get('Site Name_rep','')
                    elif 'Site Name_bill' in merged.columns and str(row.get('Site Name_bill','')).strip():
                        site_val = row.get('Site Name_bill','')
                    ticket = row.get('Ticket ID', '')
                    # collect deviations per dev_cols
                    devs = {col: row.get(f"{col}_dev", 0.0) for col in dev_cols}
                    all_table['rows'].append({
                        'Ticket ID': ticket,
                        'Site': site_val,
                        **devs
                    })
            else:
                all_table = {'columns': [], 'rows': []}

    # pass info to template (escape for safety)
    return render_template("index.html",
                           site_names=site_names,
                           ticket_ids=ticket_ids,
                           comparable_fields=comparable_fields,
                           selected_ticket=selected_ticket,
                           selected_site=selected_site,
                           comparison=comparison,
                           all_table=all_table)

if __name__ == "__main__":
    # use port 3000 & 0.0.0.0 for Replit/Render
    app.run(debug=True, host='0.0.0.0', port=3000)
