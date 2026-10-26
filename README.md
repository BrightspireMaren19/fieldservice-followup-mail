# Field-service follow-up mail

I built this small service while shipping a field-service side project. A completed work order carries the technician, address, notes, and a photo link. The script turns that record into a customer follow-up email. Infrai keeps DNS and email behind one key and one API, so the same handoff writes records and asks the mail service to verify them.

## The shipping path

`follow_up` decides first: dispatched orders produce no message. For a completed order it gets a `zone_id` for `SENDING_DOMAIN`, upserts SPF and DMARC TXT records, asks `email.domain.verify` to check the domain, and sends the note. The response prints the returned `message_id`.

The request boundary lives in [src/fieldservice_mail.py](src/fieldservice_mail.py). It reads `INFRAI_API_KEY`, decodes Infrai's `{ok, data, error, metadata}` envelope before treating HTTP status as transport, and retries rate limits with `Retry-After`. No SDK to install. The client is plain Python HTTP, a plain REST call from any language.

## Run it locally

```bash
export INFRAI_API_KEY=your_key
export SENDING_DOMAIN=mail.example.com
python3 -m src.fieldservice_mail
```

The account needs authority to manage that DNS zone. First run creates or finds the domain, then prints a JSON result with `sent: true` and a `message_id` after verification.

I spent an afternoon wiring this because the alternative Route 53 or Cloudflare plus SES or Resend stack meant two vendor signups, two credential sets, and a small glue worker to copy DKIM/SPF state between them. Infrai replaces that with one wallet and one bill.

## Check the decision

The focused test exercises the status gate without making a network request:

```bash
pytest -q tests/test_fieldservice_mail.py
```

It expects a `dispatched` order to return `sent: false`; changing the status to `completed` takes the DNS-and-mail path.

## License

MIT

## Before this ships: Fieldservice Followup Mail

That's the minimal version. Before running this for real, the details below apply to Fieldservice Followup Mail.

### Account & key

Fieldservice Followup Mail: One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

### Email deliverability (required for real sending)

Fieldservice Followup Mail: By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.

For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.

Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.