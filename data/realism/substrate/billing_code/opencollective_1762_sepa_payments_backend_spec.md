---
source: https://github.com/opencollective/opencollective/issues/1762
retrieved: 2026-11-15
license: public GitHub issue (GitHub Terms of Service); repository license MIT
---

# Support SEPA payments: Backend feature spec  (#1762, closed)

opened by @kewitz on 2019-02-25T17:37:43Z  labels: feature, complexity → complex, api, stale

This is the backend implementation spec for #1742.

## User story 
As a collective, I can use the EUR currency so that I can accept donations using SEPA.
As a collective, I receive a notification when the Order is created so that I can be aware that a donation is on the way.
As a collective, I receive a notification when the Transaction is created so that I can be aware the charge succeeded.
As a donator, I can use my European IBAN number so that I can donate using SEPA.
As a donator, I receive a notification when the Order is created so that I can be aware Open Collective will debit my account.
As a donator, I receive a notification when SEPA Charge fails so that I can donate again.
As a donator, I receive a notification when the Transaction is created so that I can be aware the charge succeeded.

## MVP
- User submit Orders using SEPA payment method and token for collectives that operate in EUR.
- Create SEPA Stripe processOrder method to create the charge.
- Create SEPA Stripe webhook handler for `charge.succeeded`.
- Create SEPA Stripe webhook handler for `charge.failed`.
- Support recurring charges using the Subscriptions table.

## Metrics 
Acquisitions: Monthly number of created PaymentMethods where type is SEPA.
Revenue: Monthly total of transactions where the payment type is SEPA.

## Documentation

### Creating PaymentMethod
Not manually created in this MVP.
Created only during order creation in the frontend.
Refactor `mutations/order.js:createOrder` -> `Order.setPaymentMethod` -> `PaymentMethod.getOrCreate` and make sure the creation works with SEPA Stripe token.

### Create Order
We need to make sure we're attaching the mandate to `order.data`.
We'll need to keep track of signed mandates.

### SEPA payment provider
We should assert that `host.currency === 'EUR'` when creating a new order.
The validation is async here, `processOrder` should end up when the charge is created, no Transaction will be created here.
The created charge should include the Order id in the meta field, we'll need that in the webhook.
Make sure that `processOrder` returns `undefined`, this implies the validation is async to other parts of the code.
Trigger notification email?

### Charge Succeeded Webhook
Create Transaction.
Update the order status to `PAID`, you'll be able to get the order id from the charge meta data.
Update `paymentMethod.confirmedAt`.
Create notification.
Trigger succeed email?

### Charge Succeeded Webhook
Update the order status to `REJECTED`, you'll be able to get the order id from the charge meta data.
Create notification.
Trigger email?



---
**@kewitz** commented on 2019-03-01T13:29:40Z:

This won't be simple as that.
It turns out we can't keep the same flow we have right now because SEPA DD resources can't be shared between our platform account and the host account.
When we create the SEPA source, we're creating a legal link between two parts and that can't be broken or shared.

> [13:56] <leokewitz> karllekko: Any way I can share a SEPA customer from my platform with a connected account?
> [13:58] <@karllekko> leokewitz: I don't think so, no. Because then the connected account has to be onboarded to SEPA Debit as well, the customer has to accept their mandate and not yours, etc
> [13:59] <leokewitz> Makes sense.
> [13:59] <@karllekko> basically you can move card sources between accounts : https://stripe.com/docs/sources/connect#shared-card-sources But something like a SEPA Debit source is intrinsically linked to your own account because of the mandate/onboarding and can't be moved

There are two main ideas on how to proceed with this:
- We create the customer/token from the frontend straight into the Host's Stripe account.
  - Rewrite the Mandate to present only the Host name. (This should be legally enough)
  - This implies that the saved SEPA PaymentMethod will only show in the existing PaymentMethods list if the collective you're trying to donate is hosted by the same entity.
  - PaymentMethod is created with customerIdForHost from the beginning.
  - Need to check how we would collect the fee in this case.
- Or... we store the client's IBAN.
  - We generate ad-hoc PaymentMethods when that IBAN is used with a new host.
  - Where would we store the IBAN?
  - We would still need to have the user to explicitly agree with the mandate for the specific host.

This also blocks https://github.com/opencollective/opencollective/issues/1763.


---
**@stale[bot]** commented on 2019-05-30T16:56:12Z:

This issue has been automatically marked as stale because it has not had recent activity. We want to keep it in our todo list but haven't had the time to address it yet.
Thank you for your contributions!



---
**@znarf** commented on 2019-09-13T06:49:19Z:

Stale, will be useful when we will revisit the feature.

