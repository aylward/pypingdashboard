"""
Run ping and speedtests at regular intervals to monitor network

Apache 2.0 License

Copyright: Stephen Aylward
"""

import subprocess
import time
from datetime import datetime, timedelta

import re
import numpy as np

import speedtest


class PingRecorder:
    """
    Run ping and speedtests at regular intervals to monitor network
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self.ping_data = {
            website: {
                "timestamp": [],
                "value": [],
                "avg": [],
                "max": [],
                "jitter": [],
                "errors": [],
                "avg_histo": [],
                "max_histo": [],
                "jitter_histo": [],
            }
            for website in ["google.com", "example.com", "openai.com"]
        }
        self.speed_data = {
            "timestamp": [],
            "download": [],
            "upload": [],
            "download_histo": [],
            "upload_histo": [],
        }

        self.ping_interval_seconds = 1
        self.ping_kernel_seconds = 10
        self.speed_interval_minutes = 30

        self.statistics_kernel_hours = 0.5

        self.ping_histo_bins = []
        self.speed_histo_bins = []

    def measure_ping(self, host):
        """
        Run ping test for the given host
        """
        try:
            ping = subprocess.check_output(["ping", "-n", "2", host]).decode("utf-8")

            times_start = [m.start() for m in re.finditer("time=", ping)]
            times = [ping[t:].split("=")[1].split(" ")[0] for t in times_start[1:]]
            ping_times = [float(time_[:-2]) for time_ in times]

            ping_value = np.mean(ping_times)
        except: # pylint: disable=bare-except
            ping_value = 0

        return ping_value

    def measure_speed(self):
        """
        Run speedtest
        """
        st = speedtest.Speedtest()
        download_speed = st.download() / 10**6  # convert to Mbps
        upload_speed = st.upload() / 10**6  # convert to Mbps
        return download_speed, upload_speed

    def record_data(self):
        """
        Run ping and speed tests at given intervals, forever
        """
        # pylint: disable=too-many-locals
        time_count = 0
        # while time_count<10:
        while True:
            time_count += 1
            # Remove data older than 240 hours (10 days)
            for website in self.ping_data:
                if self.ping_data[website]["timestamp"]:
                    oldest_timestamp = datetime.strptime(
                        self.ping_data[website]["timestamp"][0], "%Y-%m-%d %H:%M:%S"
                    )
                    while oldest_timestamp < datetime.now() - timedelta(hours=240):
                        self.ping_data[website]["timestamp"].pop(0)
                        self.ping_data[website]["value"].pop(0)
                        self.ping_data[website]["avg"].pop(0)
                        self.ping_data[website]["max"].pop(0)
                        self.ping_data[website]["jitter"].pop(0)
                        self.ping_data[website]["errors"].pop(0)
            if self.speed_data["timestamp"]:
                oldest_timestamp = datetime.strptime(
                    self.speed_data["timestamp"][0], "%Y-%m-%d %H:%M:%S"
                )
                while oldest_timestamp < datetime.now() - timedelta(hours=240):
                    self.speed_data["timestamp"].pop(0)
                    self.speed_data["download"].pop(0)
                    self.speed_data["upload"].pop(0)

            for website in self.ping_data:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ping_value = self.measure_ping(website)
                self.ping_data[website]["timestamp"].append(timestamp)
                self.ping_data[website]["value"].append(ping_value)
                winsize = int(
                    min(
                        len(self.ping_data[website]["value"]),
                        self.ping_kernel_seconds / self.ping_interval_seconds,
                    )
                )
                data = self.ping_data[website]["value"][-winsize:]
                data_errors = np.count_nonzero(data == 0) * 10
                data_max = np.max(data)
                if data_errors > 0:
                    data = np.where(data != 0, data, data_max)
                data_min = np.min(data)
                data_avg = np.mean(data)
                data_jitter = data_max - data_min
                self.ping_data[website]["avg"].append(data_avg)
                self.ping_data[website]["max"].append(data_max)
                self.ping_data[website]["jitter"].append(data_jitter)
                self.ping_data[website]["errors"].append(data_errors)

            speed_interval_count = self.speed_interval_minutes * (
                60 / self.ping_interval_seconds
            )
            if time_count > speed_interval_count:
                time_count = 0
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                download_speed, upload_speed = self.measure_speed()
                self.speed_data["timestamp"].append(timestamp)
                self.speed_data["download"].append(download_speed)
                self.speed_data["upload"].append(upload_speed)

            time.sleep(self.ping_interval_seconds)

    def compute_statistics(self):
        """
        Compute histograms from historic ping and speed values
        """
        rng_max = 0
        for website in self.ping_data:
            winsize = int(
                min(
                    self.statistics_kernel_hours * 3600 / self.ping_interval_seconds,
                    len(self.ping_data[website]["value"]),
                )
            )
            data = self.ping_data[website]["max"][-winsize:]
            if len(data) > 0:
                rng_max = max(rng_max, np.max(np.array(data)))
        for website in self.ping_data:
            winsize = int(
                min(
                    self.statistics_kernel_hours * 3600 / self.ping_interval_seconds,
                    len(self.ping_data[website]["value"]),
                )
            )
            data = self.ping_data[website]["max"][-winsize:]
            self.ping_data[website]["max_histo"], self.ping_histo_bins = np.histogram(
                data, bins=50, range=(0, rng_max)
            )
            data = self.ping_data[website]["avg"][-winsize:]
            self.ping_data[website]["avg_histo"] = np.histogram(
                data,
                bins=self.ping_histo_bins,
            )[0]
            data = self.ping_data[website]["jitter"][-winsize:]
            self.ping_data[website]["jitter_histo"] = np.histogram(
                data,
                bins=self.ping_histo_bins,
            )[0]

        winsize = int(
            min(
                self.statistics_kernel_hours * 60 / self.speed_interval_minutes,
                len(self.speed_data["upload"]),
            )
        )
        data = self.speed_data["download"][-winsize:]
        self.speed_data["download_histo"], self.speed_histo_bins = np.histogram(
            data,
            bins=50,
        )
        data = self.speed_data["upload"][-winsize:]
        self.speed_data["upload_histo"] = np.histogram(
            data,
            bins=self.speed_histo_bins,
        )[0]
