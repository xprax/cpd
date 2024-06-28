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

# Function to fetch bag info
def fetch_bag_info(bag_id):
    url = f'http://10.24.1.71/hub-ops-routes-api/sal-proxy/v1/loadservice/bag/{bag_id}/track'
    
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
            app.logger.debug(f"Bag info for {bag_id}: {data}")
            return data
        except requests.exceptions.Timeout:
            app.logger.error(f"Request timed out for bag ID {bag_id}")
            return {'status': 'error', 'message': 'Request timed out'}
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Request failed for bag ID {bag_id}: {e}")
            return {'status': 'error', 'message': str(e)}

# Function to fetch smart check details
def fetch_smart_check_details(tracking_id):
    url = f'http://10.24.1.71/hub-ops-routes-api/sal-proxy/v1/shipment/{tracking_id}/smart-check-details'
    
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
            app.logger.debug(f"Smart check details for {tracking_id}: {data}")
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
                customer_info = shipment.get('customer_info', {})
                customer_info_formatted = {
                    'name': customer_info.get('name', ''),
                    'address1': customer_info.get('address1', ''),
                    'address2': customer_info.get('address2', ''),
                    'city': customer_info.get('city', ''),
                    'state': customer_info.get('state', ''),
                    'pincode': customer_info.get('pincode', '')
                }
                customer_promise_date = ''
                for attribute in shipment.get('attributes', []):
                    if attribute['name'] == 'customer_promise_date':
                        customer_promise_date = attribute['value'].split(' ')[0]
                        break
                if tracking_id[3] == 'R':
                    cod_amount = shipment.get('total_price', 0)
                    smart_check_data = fetch_smart_check_details(tracking_id)
                    item_details = ''
                    if smart_check_data['status'] == 'success' and 'results' in smart_check_data:
                        item_details = smart_check_data['results'][0].get('item_description', '')
                else:
                    cod_amount = shipment.get('cod_amount', 0)
                    if cod_amount == 0:
                        cod_amount = shipment.get('total_price', 0)
                    bag_info = shipment.get('bag_info', {})
                    item_details = ''
                    if bag_info:
                        bag_id = bag_info.get('tracking_id', '')
                        if bag_id:
                            bag_data = fetch_bag_info(bag_id)
                            if bag_data['status'] == 'success' and 'results' in bag_data:
                                items = bag_data['results'][0].get('shipment', {}).get('item_details', [])
                                filtered_items = [f"{item['item_description']} (Value: {item['item_value']})" for item in items if item['shipment_tracking_id'] == tracking_id]
                                item_details = ', '.join(filtered_items)
                agent_info = shipment.get('agent_info', {})
                agent_name = agent_info.get('name', 'NA') if agent_info else 'NA'
                result = {
                    'tracking_id': tracking_id,
                    'shipment_id': shipment.get('shipment_id', ''),
                    'cod_amount': cod_amount,
                    'customer_info': customer_info_formatted,
                    'agent_info': {
                        'name': agent_name
                    },
                    'customer_promise_date': customer_promise_date,
                    'item_details': item_details
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
