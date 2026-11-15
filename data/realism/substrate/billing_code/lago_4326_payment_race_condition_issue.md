---
source: https://github.com/getlago/lago-api/issues/4326
retrieved: 2026-11-15
license: public GitHub issue (GitHub Terms of Service); repository license AGPL-3.0
---

# [BUG]: Potential Race Condition in Payment Processing Flow Allows Credit Application Before Payment Confirmation  (#4326, closed)

opened by @Shasheen8 on 2025-09-15T23:28:44Z  labels: 

**Describe the bug**

I've identified a potential vulnerability in the payment processing flow that could allow credits to be applied to wallets before payment confirmation is fully verified. This issue relates to the asynchronous nature of webhook processing and credit application.

**To Reproduce**

The vulnerability exists in the timing gap between payment initiation and credit application:
- Payment Creation: When a payment is initiated, a wallet transaction is created with `status: :pending`
- Asynchronous Processing: The `BillPaidCreditJob` is queued for processing
- Webhook Delay: Payment confirmation via webhook (e.g., `Stripe's payment_intent.succeeded`) may arrive after credits are already being processed
- Race Condition: Credits might become available before payment is actually confirmed

The issue is compounded by:
- Reliance on asynchronous webhook processing for payment status updates
- No real-time payment verification before credit application
- Potential for webhook delivery delays or failures

**Screenshots**
In `app/services/wallet_transactions/create_from_params_service.rb`:
```ruby
def handle_paid_credits(wallet:, credits_amount:, invoice_requires_successful_payment:)
  # Creates pending transaction
  wallet_transaction = WalletTransactions::CreateService.call!(
    wallet:,
    wallet_credit:,
    transaction_type: :inbound,
    status: :pending,  # Initial status
    source:,
    transaction_status: :purchased,
    invoice_requires_successful_payment:,
    metadata:,
    priority:,
    name:
  ).wallet_transaction

  # Queues job for billing - potential race condition here
  BillPaidCreditJob.perform_after_commit(wallet_transaction, Time.current.to_i)
  
  wallet_transaction
end
```

**Additional context/consideration:**
1. The existing signature verification (ValidateIncomingWebhookService) is good but doesn't prevent this timing issue
2. The unique index on provider_payment_id helps but may not catch all race conditions
3. Consider implementing a state machine for payment/credit lifecycle management

Related files:
```bash
app/services/wallet_transactions/create_from_params_service.rb
app/jobs/bill_paid_credit_job.rb
app/services/payment_providers/stripe/webhooks/payment_intent_succeeded_service.rb
app/services/inbound_webhooks/process_service.rb
db/migrate/20250220085848_add_unique_index_to_provider_payment_id.rb
```

**Security Note:**
This issue was discovered through internal security review. 

The system includes several security measures that partially mitigate this issue:
1. Webhook signature verification for all payment providers
2. Idempotency framework with unique key generation
3. Database-level unique constraints on payment provider IDs
4. Retry mechanisms for failed jobs (up to 15 attempts with polynomial backoff)
However, these measures don't fully prevent the race condition between payment initiation and credit application.


**Version**
- Lago: `≥ v1.32.0`



---
**@vincent-pochet** commented on 2025-09-16T13:27:06Z:

Hello @Shasheen8,

Thank you for reporting this.
We will investigate. Can you confirm the Lago version you are using as v1.7.0 was released in July 2024 is not supported any more.


---
**@Shasheen8** commented on 2025-09-16T20:11:49Z:

Hi @vincent-pochet my apologies, the version is `≥ v1.32.0` 

Updated my original post.  


---
**@vincent-pochet** commented on 2025-09-19T08:21:15Z:

Are you passing the `invoice_requires_successful_payment` argument when calling the API?
See https://getlago.com/docs/api-reference/wallets/top-up#body-wallet-transaction-invoice-requires-successful-payment for more details.

If you use this parameter, the credit is created with a "pending" status and it will become available only if the invoice if the payment attempt  is successful.

The behavior you are reporting is expected when creating a wallet transaction without this argument. The credit is emitted immediately and an invoice is created. The payment collection is then handled at the invoice level. And it's up to you to reach to the customer in case of payment failure.


---
**@vincent-pochet** commented on 2025-10-28T14:39:31Z:

I'm closing it since it seems that the reported behavior is the expected one

