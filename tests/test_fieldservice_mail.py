from src.fieldservice_mail import WorkOrder, follow_up


class NoCallClient:
    def __getattr__(self, name):
        raise AssertionError(f"API should not be called: {name}")


def test_follow_up_waits_for_completed_status():
    order = WorkOrder("WO-1", "a@example.com", "1 Main", "Lee", "dispatched", "photo", "arriving")
    assert follow_up(NoCallClient(), order, "field.example") == {"sent": False, "reason": "work order is not completed"}
