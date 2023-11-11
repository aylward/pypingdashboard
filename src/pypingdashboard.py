
import subprocess
import time
from datetime import datetime,timedelta

import numpy as np
import re

import speedtest

import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import plotly.express as px

# Global variables to store the data
timestamps = []
ping_data = {website: {'avg': [], 'jitter': []} for website in ['google.com', 'example.com', 'openai.com']}
speed_data = {'download': [], 'upload': []}

def measure_ping(host):
    ping = subprocess.check_output(["ping", "-n", "5", host]).decode("utf-8") 

    times_start = [m.start() for m in re.finditer("time=",ping)]
    times = [ping[t:].split("=")[1].split(" ")[0] for t in times_start[1:]]
    ping_times = [float(time_[:-2]) for time_ in times]
    
    avg_ping = np.mean(ping_times) # Average ping time
    min_ping = min(ping_times)
    max_ping = max(ping_times)
    jitter = abs(max_ping-min_ping)  # Jitter is the absolute difference between min and max ping times

    return avg_ping, jitter

def measure_speed():
    st = speedtest.Speedtest()
    download_speed = st.download() / 10**6  # convert to Mbps
    upload_speed = st.upload() / 10**6  # convert to Mbps
    return download_speed, upload_speed

def record_data():
    global timestamps, ping_data, speed_data

    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamps.append(timestamp)

        # Remove data older than 240 hours (10 days)
        if timestamps:
            oldest_timestamp = datetime.strptime(timestamps[0], "%Y-%m-%d %H:%M:%S")
            while oldest_timestamp < datetime.now() - timedelta(hours=240):
                timestamps.pop(0)
                for website in ping_data:
                    ping_data[website]['avg'].pop(0)
                    ping_data[website]['jitter'].pop(0)
                speed_data['download'].pop(0)
                speed_data['upload'].pop(0)

        # Measure ping for each website every minute
        for website in ping_data:
            ping_results = measure_ping(website)
            ping_data[website]['avg'].append(ping_results[0])
            ping_data[website]['jitter'].append(ping_results[1])

        # Measure speed every 30 minutes
        if len(timestamps) % 30 == 1: 
            download_speed, upload_speed = measure_speed()
            speed_data['download'].append(download_speed)
            speed_data['upload'].append(upload_speed)

        time.sleep(60)  # Record ping every 5 seconds


# Create Dash app
app = dash.Dash(__name__)

# Define the layout of the app
app.layout = html.Div(children=[
    dcc.Graph(id='ping-graph'),
    dcc.Graph(id='speed-graph')
])

# Define callback to update the graphs
@app.callback(
    [Output('ping-graph', 'figure'),
     Output('speed-graph', 'figure')],
    [Input('ping-graph', 'relayoutData'),
     Input('speed-graph', 'relayoutData')]
)
def update_graphs(ping_layout, speed_layout):
    global timestamps, ping_data, speed_data


    # Create a combined time series plot for average and jitter for each website
    ping_fig = go.Figure()
    for website in ping_data:
        ping_fig.add_trace(go.Scatter(x=timestamps, y=ping_data[website]['avg'],
                                      error_y=dict(
                                          type='data',
                                          array = ping_data[website]['jitter'],
                                          visible=True
                                          ),
                                      name=f'{website}',
                                      ))
    ping_fig.update_layout(title='Ping Time and Jitter Time Series',
                           xaxis_title='Timestamp', yaxis_title='Value')

    # Create a time series plot for download and upload speeds
    speed_fig = go.Figure()
    speed_fig.add_trace(go.Scatter(x=timestamps, y=speed_data['download'],
                                   mode='lines',
                                   name='Download'))
    speed_fig.add_trace(go.Scatter(x=timestamps, y=speed_data['upload'],
                                   mode='lines',
                                   name='Upload'))
    speed_fig.update_layout(title='Speed',
                            xaxis_title='Timestamp', yaxis_title='Speed (Mbps)')

    return ping_fig, speed_fig

if __name__ == '__main__':
    # Start recording data in a separate thread
    import threading
    record_thread = threading.Thread(target=record_data)
    record_thread.start()

    # Run the Dash app
    app.run_server(debug=True, use_reloader=False)

