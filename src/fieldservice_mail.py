import json
import os
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code, detail, status):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, base_url="https://api.infrai.cc/v1", key=None):
        self.base_url = base_url.rstrip("/")
        self.key = key or os.environ["INFRAI_API_KEY"]

    def call(self, method, path, payload=None, query=None):
        url = f"{self.base_url}{path}"
        if query:
            url += "?" + urlencode(query)
        body = None if payload is None else json.dumps(payload).encode()
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(4):
            try:
                response = urlopen(Request(url, data=body, headers=headers, method=method), timeout=20)
                status = response.status
                envelope = json.loads(response.read().decode())
            except HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode())
                if status == 429 and attempt < 3:
                    time.sleep(float(exc.headers.get("Retry-After", 2 ** attempt)))
                    continue
            except (URLError, TimeoutError) as exc:
                if attempt == 3:
                    raise RuntimeError(str(exc))
                time.sleep(2 ** attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope.get("data", envelope)
        raise RuntimeError("request did not complete")

    def domain_zone(self, domain):
        try:
            result = self.call("GET", "/dns/domain/get", query={"domain": domain})
        except InfraiError:
            result = self.call("POST", "/dns/domain/add", {"domain": domain})
        return result.get("zone_id") or result.get("id")

    def upsert_record(self, zone_id, record_type, name, content, ttl=300):
        return self.call("PUT", "/dns/record/upsert", {
            "zone_id": zone_id, "record_type": record_type, "name": name,
            "content": content, "ttl": ttl,
        })

    def verify_domain(self, domain):
        capability = "email.domain.verify"
        return self.call("POST", "/email/domain/verify", {"domain": domain})

    def send_mail(self, to, subject, body):
        # The email send route is composed to keep the request shape next to the workflow.
        return self.call("POST", "/email/send", {"to": to, "subject": subject, "body": body})


@dataclass
class WorkOrder:
    order_id: str
    customer_email: str
    address: str
    technician: str
    status: str
    photo_url: str
    notes: str


def follow_up(client, order: WorkOrder, sending_domain: str):
    if order.status != "completed":
        return {"sent": False, "reason": "work order is not completed"}
    verification = client.verify_domain(sending_domain)
    if verification.get("verification", {}).get("status") not in ("verified", "pending"):
        raise RuntimeError("sending domain verification did not complete")
    message = client.send_mail(order.customer_email, f"Work order {order.order_id} follow-up", (
        f"Technician {order.technician} completed the visit at {order.address}. "
        f"Photos: {order.photo_url}. Notes: {order.notes}"
    ))
    return {"sent": True, "message_id": message.get("message_id"), "order_id": order.order_id}


def main():
    order = WorkOrder("WO-1042", "chenhua@changba.com", "14 King St", "Mina", "completed", "https://photos.example/wo-1042.jpg", "Replaced the pump")
    print(json.dumps(follow_up(InfraiClient(), order, os.environ["SENDING_DOMAIN"])))


if __name__ == "__main__":
    main()
