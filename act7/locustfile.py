from locust import HttpUser, task, between
import random
import time

class PackageTrackingUser(HttpUser):
    wait_time = between(0.12, 0.13)

    @task
    def track_package(self):
        tracking_number = random.randint(1000000000, 9999999999)
        response = self.client.get(f"/track/{tracking_number}")

        if response.status_code == 200:
            print(f"Package {tracking_number} tracked successfully!")
        else:
            print(f"Failed to track package {tracking_number}, Status Code: {response.status_code}")

    def on_start(self):
        print("Package tracking user started.")

    def on_stop(self):
        print("Package tracking user stopped.")
