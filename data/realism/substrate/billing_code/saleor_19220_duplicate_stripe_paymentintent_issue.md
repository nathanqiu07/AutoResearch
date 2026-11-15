---
source: https://github.com/saleor/saleor/issues/19220
retrieved: 2026-11-15
license: public GitHub issue (GitHub Terms of Service); repository license BSD-3-Clause
---

# Bug: Duplicate Stripe PaymentIntent can occur during concurrent webhook and checkoutComplete flows  (#19220, closed)

opened by @gurumurugan123 on 2026-05-18T08:58:33Z  labels: bug, triage, wontfix

### What are you trying to achieve?

I investigated the Stripe payment flow and noticed that concurrent execution between Stripe webhooks and checkoutComplete may create duplicate Stripe PaymentIntents for the same checkout/payment.

The issue appears to happen when automatic payment capture is enabled (Payment.to_confirm=False).

In this flow:

Stripe webhook processing may already finalize and capture the payment
checkoutComplete may still continue processing payment
process_payment unconditionally creates a new Stripe PaymentIntent

Unlike confirm_payment, the process_payment flow does not appear to enforce idempotency checks before creating a new payment intent.

This may lead to duplicate Stripe payment creation and potential duplicate customer charges during concurrent execution scenarios.

### Steps to reproduce the problem

Steps to reproduce the problem
Start a local Saleor instance with Stripe configured.
Enable automatic payment capture for the Stripe plugin.
Create:
a channel
a product
a checkout
Add a Stripe payment to the checkout.
Complete payment using a Stripe test card.
Trigger concurrent execution between:
Stripe payment_intent.succeeded webhook
GraphQL checkoutComplete
Observe Stripe Dashboard and Saleor payment transactions.

Example local webhook forwarding:
stripe listen --forward-to "http://localhost:8000/plugins/channel/<channel-slug>/saleor.payments.stripe/webhooks/"
Under concurrent timing conditions, a second Stripe PaymentIntent may be created for the same payment/checkout.

### What did you expect to happen?

If a successful AUTH/CAPTURE/PENDING transaction already exists for the payment, Saleor should not create another Stripe PaymentIntent.

The payment flow should behave idempotently and avoid duplicate payment processing during concurrent webhook and checkout completion execution.

Behavior should match the protection logic already implemented in confirm_payment.

Instead of creating another payment intent, the system should:

detect already processed payments
skip duplicate payment processing
avoid duplicate Stripe charges/authorizations
maintain consistent payment state

### Logs

_No response_

### Environment

Saleor version: …
OS and version: …



---
**@lkostrowski** commented on 2026-05-18T12:53:10Z:

Stripe plugin is deprecated, please use the app


---
**@NikhilDendeti** commented on 2026-07-02T10:17:26Z:

I'd like to work on this — it's a real correctness bug that can cause double-charges, so worth prioritizing. Since confirm_payment already has protection against this and process_payment doesn't, the fix is bringing process_payment in line: check for an existing non-terminal PaymentIntent tied to this checkout/payment before creating a new one, using the same idempotency approach confirm_payment uses rather than inventing a new mechanism. I'll add a test that simulates the race with both entry points firing close together.


---
**@NyanKiyoshi** commented on 2026-07-02T10:24:02Z:

This will not be fixed, deprecated plugins aren't supported anymore and will be dropped in a future release

