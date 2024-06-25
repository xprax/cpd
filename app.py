from flask import Flask, request, render_template, jsonify
import requests
import pandas as pd
from io import BytesIO
import base64
import logging
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management

# Enable logging
logging.basicConfig(level=logging.DEBUG)

# Function to load cookies from a JSON file
def load_cookies(filename):
    with open(filename, 'r') as f:
        cookies = json.load(f)
    return {cookie['name']: cookie['value'] for cookie in cookies}

# Function to fetch data from API
def fetch_data(tracking_id):
    url = f'http://10.24.1.71/hub-ops-routes-api/sal-proxy/v1/shipment/{tracking_id}/track'
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    cookies = load_cookies('cookies.json')  # Load cookies from JSON file
    
    with requests.Session() as session:
        session.headers.update(headers)
        session.cookies.update(cookies)
        response = session.get(url)
        response.raise_for_status()  # Will raise an HTTPError for bad responses
        data = response.json()
        return data

# Route for the home page
@app.route('/')
def home():
    return render_template('index.html')

# Route to handle form submission and fetch data
@app.route('/fetch', methods=['POST'])
def fetch():
    try:
        tracking_ids = request.form['tracking_ids'].strip().split('\n')
        tracking_ids = [tid.strip() for tid in tracking_ids if tid.strip()]
        app.logger.debug(f'Received tracking IDs: {tracking_ids}')
        results = []
        for tracking_id in tracking_ids:
            try:
                data = fetch_data(tracking_id)
                app.logger.debug(f'API response data for {tracking_id}: {data}')
                if data['status'] == 'success':
                    shipment = data['results'][0]
                    result = {
                        'tracking_id': tracking_id,
                        'shipment_id': shipment['shipment_id'],
                        'cod_amount': shipment['cod_amount'],
                        'customer_info': shipment['customer_info'],
                        'agent_info': shipment['agent_info']
                    }
                    results.append(result)
                else:
                    results.append({'tracking_id': tracking_id, 'error': 'No data found'})
            except requests.exceptions.HTTPError as e:
                logging.exception(f"HTTPError for tracking ID {tracking_id}: {e.response.text}")
                results.append({'tracking_id': tracking_id, 'error': str(e)})
            except Exception as e:
                logging.exception(f"An error occurred while fetching data for tracking ID {tracking_id}")
                results.append({'tracking_id': tracking_id, 'error': str(e)})
        
        return jsonify(results)
    except Exception as e:
        logging.exception("An error occurred while processing the request")
        return jsonify({'error': str(e)}), 500

# Route to handle exporting data to Excel
@app.route('/export', methods=['POST'])
def export():
    data = request.json
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    excel_data = output.read()
    encoded_excel = base64.b64encode(excel_data).decode('utf-8')
    return jsonify({'excel_data': encoded_excel})

if __name__ == '__main__':
    app.run(debug=True)
