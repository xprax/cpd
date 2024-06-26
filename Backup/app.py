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
        try:
            response = session.get(url, timeout=30)  # Set a 30-second timeout
            response.raise_for_status()  # Will raise an HTTPError for bad responses
            data = response.json()
            return data
        except requests.exceptions.Timeout:
            app.logger.error(f"Request timed out for tracking ID {tracking_id}")
            return {'status': 'error', 'message': 'Request timed out'}
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Request failed for tracking ID {tracking_id}: {e}")
            return {'status': 'error', 'message': str(e)}

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
            data = fetch_data(tracking_id)
            if data['status'] == 'success':
                shipment = data['results'][0]
                customer_info = {
                    'name': shipment['customer_info'].get('name', ''),
                    'address1': shipment['customer_info'].get('address1', ''),
                    'address2': shipment['customer_info'].get('address2', ''),
                    'city': shipment['customer_info'].get('city', ''),
                    'state': shipment['customer_info'].get('state', ''),
                    'pincode': shipment['customer_info'].get('pincode', '')
                }
                customer_promise_date = ''
                for attribute in shipment['attributes']:
                    if attribute['name'] == 'customer_promise_date':
                        customer_promise_date = attribute['value'].split(' ')[0]
                        break
                result = {
                    'tracking_id': tracking_id,
                    'shipment_id': shipment['shipment_id'],
                    'cod_amount': shipment['cod_amount'],
                    'customer_info': customer_info,
                    'agent_info': {
                        'name': shipment['agent_info'].get('name', '')
                    },
                    'customer_promise_date': customer_promise_date
                }
                results.append(result)
            else:
                results.append({'tracking_id': tracking_id, 'error': data.get('message', 'No data found')})
        
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