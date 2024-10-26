import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import requests
from datetime import datetime
import pytz
 
# Constants for IP and port
IP_ADDRESS = "4.228.64.5"
PORT_STH = 8666
DASH_HOST = "0.0.0.0"  # Set this to "0.0.0.0" to allow access from any IP
lamp = "05x"
 
# Function to get luminosity data from the API
def get_luminosity_data(lastN):
    url = f"http://{IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/Lamp/id/urn:ngsi-ld:Lamp:{lamp}/attributes/luminosity?lastN={lastN}"
    headers = {
        'fiware-service': 'smart',
        'fiware-servicepath': '/'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        try:
            values = data['contextResponses'][0]['contextElement']['attributes'][0]['values']
            return values
        except KeyError as e:
            print(f"Key error: {e}")
            return []
    else:
        print(f"Error accessing {url}: {response.status_code}")
        return []
 
# Function to convert UTC timestamps to Lisbon time
def convert_to_sao_paulo_time(timestamps):
    utc = pytz.utc
    lisbon = pytz.timezone('America/Sao_Paulo')
    converted_timestamps = []
    for timestamp in timestamps:
        try:
            timestamp = timestamp.replace('T', ' ').replace('Z', '')
            converted_time = utc.localize(datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')).astimezone(lisbon)
        except ValueError:
            # Handle case where milliseconds are not present
            converted_time = utc.localize(datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')).astimezone(lisbon)
        converted_timestamps.append(converted_time)
    return converted_timestamps
 
# Set lastN value
lastN = 10  # Get 10 most recent points at each interval
 
app = dash.Dash(__name__)
 
app.layout = html.Div([
    html.H1('Luminosity Data Viewer'),
    dcc.Graph(id='luminosity-graph'),
    # Store to hold historical data
    dcc.Store(id='luminosity-data-store', data={'timestamps': [], 'luminosity_values': []}),
    dcc.Interval(
        id='interval-component',
        interval=10*1000,  # in milliseconds (10 seconds)
        n_intervals=0
    )
])

@app.callback(
    Output('luminosity-data-store', 'data'),
    Input('interval-component', 'n_intervals'),
    State('luminosity-data-store', 'data')
)
def update_data_store(n, stored_data):
    # Get luminosity data
    data_luminosity = get_luminosity_data(lastN)

    if data_luminosity:
        # Extract values and timestamps
        luminosity_values = [float(entry['attrValue']) for entry in data_luminosity]  # Ensure values are floats
        timestamps = [entry['recvTime'] for entry in data_luminosity]

        # Calculate the average luminosity for the current interval
        average_luminosity = sum(luminosity_values) / len(luminosity_values)

        # Convert timestamps to Lisbon time
        timestamps = convert_to_sao_paulo_time(timestamps)

        # Append the new average and the latest timestamp to stored data
        stored_data['timestamps'].append(timestamps[-1])  # Store only the latest timestamp
        stored_data['luminosity_values'].append(average_luminosity)  # Store the average luminosity

        # Calculate total average luminosity
        total_luminosity = sum(stored_data['luminosity_values'])
        total_count = len(stored_data['luminosity_values'])
        stored_data['total_average_luminosity'] = total_luminosity / total_count if total_count > 0 else 0

        return stored_data

    return stored_data

@app.callback(
    Output('luminosity-graph', 'figure'),
    Input('luminosity-data-store', 'data')
)
def update_graph(stored_data):
    if stored_data['timestamps'] and stored_data['luminosity_values']:
        # Create traces for the plot
        trace_average = go.Scatter(
            x=stored_data['timestamps'],
            y=stored_data['luminosity_values'],
            mode='lines+markers',
            name='Luminosidade',
            line=dict(color='orange')
        )

        # Create a trace for the total average
        total_average_luminosity = stored_data['total_average_luminosity']
        trace_total_average = go.Scatter(
            x=[stored_data['timestamps'][0], stored_data['timestamps'][-1]],
            y=[total_average_luminosity, total_average_luminosity],
            mode='lines',
            name='Media da Luminosidade',
            line=dict(color='blue', dash='dash')
        )

        # Create figure
        fig_luminosity = go.Figure(data=[trace_average, trace_total_average])

        # Update layout
        fig_luminosity.update_layout(
            title='Luminosidade',
            xaxis_title='Timestamp',
            yaxis_title='Luminosity',
            hovermode='closest'
        )

        return fig_luminosity

    return {}

 
if __name__ == '__main__':
    app.run_server(debug=True, host=DASH_HOST, port=8050)
