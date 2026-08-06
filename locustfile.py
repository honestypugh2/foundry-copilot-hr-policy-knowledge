"""Optional local/non-production HTTP load workload for HR policy routes."""

from locust import HttpUser, between, events, task

from src.benchmarking.load import validate_load_target


@events.test_start.add_listener
def guard_target(environment, **_kwargs):
    validate_load_target(environment.host)


class HRPolicyUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task(3)
    def chat(self):
        self.client.post(
            "/api/chat",
            json={"message": "What is the PTO policy?", "conversation_history": []},
            name="POST /api/chat",
        )

    @task(1)
    def lookup(self):
        self.client.post(
            "/api/lookup",
            json={"message": "Where is Policy 50010?", "conversation_history": []},
            name="POST /api/lookup",
        )