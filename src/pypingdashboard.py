"""
Dashboard webpage summarizing PingRecorder results

Apache 2.0 License

Copyright: Stephen Aylward
"""

import threading

import numpy as np

import dash
from dash import dcc, html
from dash.dependencies import Input, Output

import plotly.graph_objects as go

from pypingrecorder import PingRecorder

# Create Dash app
app = dash.Dash(__name__)

# Define the layout of the app
app.layout = html.Div(
    className="row",
    children=[
        html.H1("Ping Dashboard"),
        html.Div(
            children=[
                dcc.Graph(id="ping-time-graph", style={"display": "inline-block"}),
                dcc.Graph(id="ping-histo-graph", style={"display": "inline-block"}),
                dcc.Graph(id="speed-time-graph", style={"display": "inline-block"}),
                dcc.Graph(id="speed-histo-graph", style={"display": "inline-block"}),
            ]
        ),
        dcc.Interval(interval=5000),
    ],
)

pr = PingRecorder()


# Define callback to update the graphs
@app.callback(
    [
        Output("ping-time-graph", "figure"),
        Output("ping-histo-graph", "figure"),
        Output("speed-time-graph", "figure"),
        Output("speed-histo-graph", "figure"),
    ],
    [
        Input("ping-time-graph", "relayoutData"),
        Input("ping-histo-graph", "relayoutData"),
        Input("speed-time-graph", "relayoutData"),
        Input("speed-histo-graph", "relayoutData"),
    ],
)
def update_graphs(
    ping_time_layout,
    ping_histo_layout,
    speed_time_layout,
    speed_histo_layout
):
    """ 
    Generate time-series and histograms of ping and up/download tests
    """
    # pylint: disable=unused-argument

    pr.compute_statistics()
    ping_time_fig = go.Figure()
    for website_num, website in enumerate(pr.ping_data):
        color = ping_time_fig.layout["template"]["layout"]["colorway"][website_num]
        err = np.array(pr.ping_data[website]["jitter"])
        err = err / 2.0
        ping_time_fig.add_trace(
            go.Scatter(
                x=pr.ping_data[website]["timestamp"],
                y=pr.ping_data[website]["avg"],
                name=f"{website} Avg",
                line={"color": color, "dash": "solid"},
            )
        )
        ping_time_fig.add_trace(
            go.Scatter(
                x=pr.ping_data[website]["timestamp"],
                y=pr.ping_data[website]["max"],
                name=f"{website} Max",
                line={"color": color, "dash": "dot"},
            )
        )
        ping_time_fig.add_trace(
            go.Scatter(
                x=pr.ping_data[website]["timestamp"],
                y=pr.ping_data[website]["jitter"],
                name=f"{website} Jitter",
                line={"color": color, "dash": "dash"},
            )
        )
        ping_time_fig.add_trace(
            go.Scatter(
                x=pr.ping_data[website]["timestamp"],
                y=pr.ping_data[website]["errors"],
                name=f"{website} Errors",
                line={"color": color, "dash": "dashdot"},
            )
        )
    ping_time_fig.update_layout(
        title="Ping Time and Jitter Time Series",
        xaxis_title="Timestamp",
        yaxis_title="Value",
    )

    # Create a time series plot for download and upload speeds
    speed_time_fig = go.Figure()
    speed_time_fig.add_trace(
        go.Scatter(
            x=pr.speed_data["timestamp"],
            y=pr.speed_data["download"],
            mode="lines",
            name="Download",
        )
    )
    speed_time_fig.add_trace(
        go.Scatter(
            x=pr.speed_data["timestamp"],
            y=pr.speed_data["upload"],
            mode="lines",
            name="Upload",
        )
    )
    speed_time_fig.update_layout(
        title="Speed", xaxis_title="Timestamp", yaxis_title="Speed (Mbps)"
    )

    ## Ping Histo
    ping_histo_fig = go.Figure()
    for website_num, website in enumerate(pr.ping_data):
        color = ping_time_fig.layout["template"]["layout"]["colorway"][website_num]
        ping_histo_fig.add_trace(
            go.Scatter(
                x=pr.ping_histo_bins,
                y=pr.ping_data[website]["avg_histo"],
                name=f"{website} Avg",
                line={"color": color, "dash": "solid"},
            )
        )
        ping_histo_fig.add_trace(
            go.Scatter(
                x=pr.ping_histo_bins,
                y=pr.ping_data[website]["max_histo"],
                name=f"{website} Max",
                line={"color": color, "dash": "dot"},
            )
        )
        ping_histo_fig.add_trace(
            go.Scatter(
                x=pr.ping_histo_bins,
                y=pr.ping_data[website]["jitter_histo"],
                name=f"{website} Jitter",
                line={"color": color, "dash": "dash"},
            )
        )
    ping_histo_fig.update_layout(
        title="Ping Avg and Max Histograms",
        xaxis_title="ms",
        yaxis_title="Frequency",
    )

    speed_histo_fig = go.Figure()
    speed_histo_fig.add_trace(
        go.Scatter(
            x=pr.speed_histo_bins,
            y=pr.speed_data["download_histo"],
            name="Download",
        )
    )
    speed_histo_fig.add_trace(
        go.Scatter(
            x=pr.speed_histo_bins,
            y=pr.speed_data["upload_histo"],
            name="Upload",
        )
    )

    return ping_time_fig, ping_histo_fig, speed_time_fig, speed_histo_fig


record_thread = threading.Thread(target=pr.record_data)
record_thread.start()

# Run the Dash app
app.run_server(debug=True, use_reloader=True)
