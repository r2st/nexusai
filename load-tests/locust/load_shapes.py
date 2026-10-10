"""
Custom Load Shapes for NexusAI Load Tests
==========================================
Defines realistic traffic patterns: spike, stepped ramp, diurnal cycle.

Usage:
    locust -f locustfile.py,load_shapes.py --headless -t 600s
"""

import math
from locust import LoadTestShape


class SpikeLoadShape(LoadTestShape):
    """
    Simulates a traffic spike: gradual ramp, sudden spike to 10K users,
    sustained hold, then gradual cooldown.

    Timeline:
        0-60s:    Ramp to 100 users    (warm-up)
        60-90s:   Spike to 10,000      (sudden traffic burst)
        90-210s:  Hold at 10,000       (sustained peak)
        210-270s: Ramp down to 1,000   (post-spike)
        270-330s: Ramp down to 0       (cooldown)
    """

    stages = [
        {"duration": 60, "users": 100, "spawn_rate": 5},
        {"duration": 90, "users": 10000, "spawn_rate": 500},
        {"duration": 210, "users": 10000, "spawn_rate": 100},
        {"duration": 270, "users": 1000, "spawn_rate": 100},
        {"duration": 330, "users": 0, "spawn_rate": 50},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]

        return None


class SteppedLoadShape(LoadTestShape):
    """
    Stepped ramp-up to find the breaking point.
    Increases load by 1,000 users every 2 minutes.

    Steps: 1K -> 2K -> 3K -> 5K -> 7.5K -> 10K -> 12K -> 15K
    """

    steps = [
        {"duration": 120, "users": 1000, "spawn_rate": 50},
        {"duration": 240, "users": 2000, "spawn_rate": 50},
        {"duration": 360, "users": 3000, "spawn_rate": 50},
        {"duration": 480, "users": 5000, "spawn_rate": 100},
        {"duration": 600, "users": 7500, "spawn_rate": 100},
        {"duration": 720, "users": 10000, "spawn_rate": 150},
        {"duration": 840, "users": 12000, "spawn_rate": 150},
        {"duration": 960, "users": 15000, "spawn_rate": 200},
        {"duration": 1080, "users": 15000, "spawn_rate": 0},  # Hold at max
        {"duration": 1200, "users": 0, "spawn_rate": 100},     # Cooldown
    ]

    def tick(self):
        run_time = self.get_run_time()

        for step in self.steps:
            if run_time < step["duration"]:
                return step["users"], step["spawn_rate"]

        return None


class DiurnalLoadShape(LoadTestShape):
    """
    Simulates a 24-hour traffic pattern compressed into 10 minutes.
    Models typical business-hour traffic with morning ramp, lunch dip,
    afternoon peak, and overnight low.
    """

    # Total simulation duration in seconds
    TOTAL_DURATION = 600  # 10 minutes
    PEAK_USERS = 10000
    MIN_USERS = 500

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.TOTAL_DURATION:
            return None

        # Map run_time to 0-24 hour range
        hour = (run_time / self.TOTAL_DURATION) * 24

        # Simulate diurnal pattern using sine waves
        # Peak at 10am (hour=10) and 2pm (hour=14)
        # Trough at 3am (hour=3)
        traffic_factor = (
            0.5
            + 0.3 * math.sin(math.pi * (hour - 6) / 12)  # Main daily cycle
            + 0.1 * math.sin(math.pi * (hour - 8) / 6)     # Morning spike
            + 0.1 * math.cos(math.pi * (hour - 12) / 4)    # Lunch dip recovery
        )

        # Clamp between 0 and 1
        traffic_factor = max(0.05, min(1.0, traffic_factor))

        users = int(self.MIN_USERS + (self.PEAK_USERS - self.MIN_USERS) * traffic_factor)
        spawn_rate = max(10, int(users * 0.1))  # 10% spawn rate

        return users, spawn_rate
