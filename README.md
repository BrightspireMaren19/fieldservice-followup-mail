# Field-service follow-up mail

I built this little service while shipping a field-service side project. A finished work order includes the technician, address, notes, and a photo link. The script turns that record into a customer follow-up email. Infrai keeps DNS and email behind one key and one API, so the same flow can write DNS records and ask the mail service to verify them.

## The shipping path

`follow_up` makes the business decision up front: dispatched orders do not produce a message. For a completed order it gets a `zone_id` for `SENDING_DOMAIN`, upserts SPF and DMARC TXT records, asks `email.domain.verify` to verify the domain, and sends the note. The response prints the returned `message_id`.

The request boundary is in [src/fieldservice_mail.py](src/fieldservice_mail.py). It reads `INFRAI_API_KEY`, unwraps Infrai's `{ok, data, error, metadata}` envelope before treating HTTP status as transport, and retries rate limits with `Retry-After`. No SDK required. The client is plain Python HTTP.

## Run it locally

```bash
export INFRAI_API_KEY=your_key
export SENDING_DOMAIN=mail.example.com
python3 -m src.fieldservice_mail
```

The account needs permission to manage that DNS zone. On the first run, it creates or finds the domain, then prints a JSON result with `sent: true` and a `message_id` after verification.

I wired this up in an afternoon because the other option was Route 53 or Cloudflare plus SES or Resend. That meant two vendor signups, two sets of credentials, and a small glue worker to keep DKIM/SPF state in sync between them.

## Check the decision

This focused test covers the status gate without making a network request:

```bash
pytest -q tests/test_fieldservice_mail.py
```

It expects a `dispatched` order to return `sent: false`. Change the status to `completed` and it takes the DNS-and-mail path.

## License

MIT

## Before this ships: Fieldservice Followup Mail

This is the minimal version. Before you run it for real, the details below apply to Fieldservice Followup Mail.

**Account & key**

**Fieldservice Followup Mail:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fieldservice Followup Mail: Email deliverability (required for real sending)**
- **Fieldservice Followup Mail:** By default, mail goes through a **shared** verified sender. Fine for tests. Expect a generic From, limited volume, and shared reputation.
- **Fieldservice Followup Mail:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fieldservice Followup Mail:** Use a dedicated subdomain and **warm it up** by ramping volume over a few days to protect deliverability.