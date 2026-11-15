---
source: https://github.com/getlago/lago-api/pull/5456
retrieved: 2026-11-15
license: public GitHub issue (GitHub Terms of Service); repository license AGPL-3.0
---

# feat(payments): add Paystack provider  (#5456, open)

opened by @realsama on 2026-05-04T20:43:16Z  labels: 

## Context

Lago Community supports multiple native payment providers, but [Paystack](https://paystack.com/) is not available for merchants that need Nigeria-focused checkout, saved card billing, webhooks, and refunds.

## Description

Added Paystack as a native payment provider for invoices, payment requests, wallet top-up checkout, reusable card authorization, signed webhooks, and credit note refunds. Wired the provider through GraphQL, factories, webhook routing, customer serialization, and provider-specific tests without changing core billing, subscription, wallet, or dunning behavior.

## Roadmap Task

👉  [https://getlago.canny.io/feature-requests/p/add-paystack-as-a-native-payment-provider](https://getlago.canny.io/feature-requests/p/add-paystack-as-a-native-payment-provider)



---
**@cla-check-bot[bot]** commented on 2026-05-04T20:43:20Z:

## Welcome back, @realsama!

It looks like we still need your FLA signature on file. Please sign it here:

[Sign the FLA](https://getlago.com/fla?github_username=realsama)

Once signed, this PR will be automatically updated.

<!-- CLA-BOT -->


---
**@cla-check-bot[bot]** commented on 2026-05-04T20:44:18Z:

## Thanks, @realsama! 🎉

Your CLA has been signed and is now on file. We'll proceed with the review shortly.

<!-- CLA-BOT-SIGNED -->


---
**@realsama** commented on 2026-05-11T14:33:00Z:

cc @vincent-pochet 


---
**@realsama** commented on 2026-05-18T14:02:42Z:

Regenerated the missing 'schema.graphql' and 'schema.json' files.


---
**@realsama** commented on 2026-06-24T18:31:16Z:

Hey @mikeh-lago just wanted to gently bump this PR. Happy to rebase or make any changes if that would help move it along whenever you get a chance.


---
**@realsama** commented on 2026-07-22T23:22:11Z:

Thanks @vincent-pochet. I’ve addressed the review comments and added the requested coverage. Could you take another look when you have a chance?


---
**@realsama** commented on 2026-09-18T15:29:16Z:

Hi @vincent-pochet, the updates are pushed and I've replied to each thread. All 277 targeted tests and RuboCop pass locally. Could you approve the workflows and take another look when you have a chance?



## Review comments (inline, on diff)

---
**@vincent-pochet** on `app/controllers/webhooks_controller.rb`:

```diff
@@ -108,4 +108,21 @@ def moneyhash
 
     head(:ok)
   end
+
+  def paystack
```

Could you add some tests related to this method in `/spec/requests/webhooks_controller_spec.rb`


---
**@vincent-pochet** on `app/jobs/credit_notes/refunds/paystack_create_job.rb`:

```diff
@@ -0,0 +1,14 @@
+# frozen_string_literal: true
+
+module CreditNotes
+  module Refunds
+    class PaystackCreateJob < ApplicationJob
```

Could you add the related specs in `spec/jobs/credit_notes/refunds/stripe_create_job_spec.rb`?


---
**@vincent-pochet** on `app/jobs/payment_provider_customers/paystack_checkout_url_job.rb`:

```diff
@@ -0,0 +1,14 @@
+# frozen_string_literal: true
+
+module PaymentProviderCustomers
+  class PaystackCheckoutUrlJob < ApplicationJob
```

A spec file should be added for this job as well


---
**@vincent-pochet** on `app/jobs/payment_provider_customers/paystack_create_job.rb`:

```diff
@@ -0,0 +1,14 @@
+# frozen_string_literal: true
+
+module PaymentProviderCustomers
+  class PaystackCreateJob < ApplicationJob
```

A spec file should be added for this job as well


---
**@vincent-pochet** on `app/models/payment_provider_customers/paystack_customer.rb`:

```diff
+
+module PaymentProviderCustomers
+  class PaystackCustomer < BaseCustomer
+    settings_accessors :authorization_code, :payment_method_id
+
+    def provider_payment_methods
```

Since this method returns a constant value, can't we simply turn the `card` value into a constant rather than an instance method?


---
**@vincent-pochet** on `app/models/customer.rb`:

```diff
@@ -278,6 +278,8 @@ def provider_customer
       adyen_customer
     when :moneyhash
       moneyhash_customer
+    when :paystack
```

Can you update the specs for this case?


---
**@vincent-pochet** on `app/services/payment_requests/payments/payment_providers/factory.rb`:

```diff
@@ -22,6 +22,8 @@ def self.service_class(payment_provider)
             PaymentRequests::Payments::GocardlessService
           when "moneyhash"
             PaymentRequests::Payments::MoneyhashService
+          when "paystack"
```

Can you update the specs in `spec/services/payment_requests/payments/payment_providers/factory_spec.rb`


---
**@vincent-pochet** on `app/services/credit_notes/refunds/paystack_service.rb`:

```diff
+        paystack_result = client.create_refund(paystack_refund_payload)
+        refund_data = paystack_result["data"]
+
+        refund = Refund.new(
+          organization_id: credit_note.organization_id,
+          credit_note:,
```

Could you assign the `refundable` as well?


---
**@vincent-pochet** on `app/services/credit_notes/refunds/paystack_service.rb`:

```diff
+          return refund if refund
+        end
+
+        return if transaction_reference.blank?
+
+        payment = Payment.find_by("provider_payment_data ->> 'reference' = ?", transaction_reference)
```

Maybe you should scope the payment lookup to the organization to avoid cross organization assignment.


---
**@vincent-pochet** on `app/services/invoices/payments/paystack_service.rb`:

```diff
+        payment.payable_payment_status = payment.payment_provider&.payable_payment_status(payment.status)
+        payment.provider_payment_data = provider_payment_data(paystack_payment)
+        payment.save!
+
+        update_payment_method(paystack_payment.authorization) if payment.payable_payment_status == "succeeded"
+        deliver_webhook if payment.payable_payment_status.to_sym == :succeeded
```

```suggestion
        if payment.payable_payment_status.to_sym == :succeeded
          update_payment_method(paystack_payment.authorization)
          deliver_webhook
        end
```


---
**@vincent-pochet** on `app/services/invoices/payments/paystack_service.rb`:

```diff
+          payable: @invoice,
+          customer:,
+          payment_provider_id: paystack_payment_provider.id,
+          payment_provider_customer_id: customer.paystack_customer.id,
+          amount_cents: @invoice.total_due_amount_cents,
+          amount_currency: @invoice.currency,
```

Due to a recent update on the payment management (partial payment), you might have to accept a new "amount_cents" argument in this service and assign it here.


---
**@vincent-pochet** on `app/services/payment_providers/paystack/client.rb`:

```diff
@@ -0,0 +1,102 @@
+# frozen_string_literal: true
+
+module PaymentProviders
+  module Paystack
+    class Client
```

Maybe you could add some tests around this client. What do you think?


---
**@vincent-pochet** on `app/services/payment_providers/paystack/handle_event_service.rb`:

```diff
+
+      def call
+        return handle_charge_event if CHARGE_EVENTS.include?(event_type)
+        return handle_refund_event if REFUND_EVENTS.include?(event_type)
+
+        Rails.logger.warn("Unexpected paystack event type: #{event_type}")
```

Should we return service failure with `webhook_error` code in case of unhanded event?


---
**@vincent-pochet** on `app/services/payment_requests/payments/paystack_service.rb`:

```diff
+        payment ||= handle_missing_payment(organization_id, paystack_payment)
+        return result unless payment
+
+        if payment.payable.payment_succeeded?
+          result.payment = payment if payment.persisted?
+          result.payable = payment.payable if payment.persisted?
```

```suggestion
          if payment.persisted?
            result.payment = payment
            result.payable = payment.payable
          end
```


---
**@realsama** on `app/controllers/webhooks_controller.rb`:

```diff
@@ -108,4 +108,21 @@ def moneyhash
 
     head(:ok)
   end
+
+  def paystack
```

Added request specs for valid and invalid Paystack webhooks.


---
**@realsama** on `app/jobs/credit_notes/refunds/paystack_create_job.rb`:

```diff
@@ -0,0 +1,14 @@
+# frozen_string_literal: true
+
+module CreditNotes
+  module Refunds
+    class PaystackCreateJob < ApplicationJob
```

Added the corresponding Paystack refund job spec.


---
**@realsama** on `app/jobs/payment_provider_customers/paystack_checkout_url_job.rb`:

```diff
@@ -0,0 +1,14 @@
+# frozen_string_literal: true
+
+module PaymentProviderCustomers
+  class PaystackCheckoutUrlJob < ApplicationJob
```

Added a spec for this job.


---
**@realsama** on `app/jobs/payment_provider_customers/paystack_create_job.rb`:

```diff
@@ -0,0 +1,14 @@
+# frozen_string_literal: true
+
+module PaymentProviderCustomers
+  class PaystackCreateJob < ApplicationJob
```

Added a spec for this job.


---
**@realsama** on `app/models/payment_provider_customers/paystack_customer.rb`:

```diff
+
+module PaymentProviderCustomers
+  class PaystackCustomer < BaseCustomer
+    settings_accessors :authorization_code, :payment_method_id
+
+    def provider_payment_methods
```

Done. Replaced the instance method with PAYMENT_METHODS and updated its consumers.


---
**@realsama** on `app/models/customer.rb`:

```diff
@@ -278,6 +278,8 @@ def provider_customer
       adyen_customer
     when :moneyhash
       moneyhash_customer
+    when :paystack
```

Added the Paystack case to the customer specs.


---
**@realsama** on `app/services/payment_requests/payments/payment_providers/factory.rb`:

```diff
@@ -22,6 +22,8 @@ def self.service_class(payment_provider)
             PaymentRequests::Payments::GocardlessService
           when "moneyhash"
             PaymentRequests::Payments::MoneyhashService
+          when "paystack"
```

Added Paystack coverage to the factory spec.


---
**@realsama** on `app/services/credit_notes/refunds/paystack_service.rb`:

```diff
+        paystack_result = client.create_refund(paystack_refund_payload)
+        refund_data = paystack_result["data"]
+
+        refund = Refund.new(
+          organization_id: credit_note.organization_id,
+          credit_note:,
```

Done. The refund now assigns the credit note as refundable.


---
**@realsama** on `app/services/credit_notes/refunds/paystack_service.rb`:

```diff
+          return refund if refund
+        end
+
+        return if transaction_reference.blank?
+
+        payment = Payment.find_by("provider_payment_data ->> 'reference' = ?", transaction_reference)
```

Done. The payment lookup is now scoped to the organization.


---
**@realsama** on `app/services/invoices/payments/paystack_service.rb`:

```diff
+        payment.payable_payment_status = payment.payment_provider&.payable_payment_status(payment.status)
+        payment.provider_payment_data = provider_payment_data(paystack_payment)
+        payment.save!
+
+        update_payment_method(paystack_payment.authorization) if payment.payable_payment_status == "succeeded"
+        deliver_webhook if payment.payable_payment_status.to_sym == :succeeded
```

Applied. Payment-method updates and webhook delivery now share the success branch.


---
**@realsama** on `app/services/invoices/payments/paystack_service.rb`:

```diff
+          payable: @invoice,
+          customer:,
+          payment_provider_id: paystack_payment_provider.id,
+          payment_provider_customer_id: customer.paystack_customer.id,
+          amount_cents: @invoice.total_due_amount_cents,
+          amount_currency: @invoice.currency,
```

Done. The service now accepts amount_cents and records the provider-reported amount.


---
**@realsama** on `app/services/payment_providers/paystack/client.rb`:

```diff
@@ -0,0 +1,102 @@
+# frozen_string_literal: true
+
+module PaymentProviders
+  module Paystack
+    class Client
```

Added client specs covering the supported operations, responses, and provider errors.


---
**@realsama** on `app/services/payment_providers/paystack/handle_event_service.rb`:

```diff
+
+      def call
+        return handle_charge_event if CHARGE_EVENTS.include?(event_type)
+        return handle_refund_event if REFUND_EVENTS.include?(event_type)
+
+        Rails.logger.warn("Unexpected paystack event type: #{event_type}")
```

I kept signed unsupported events as successful no-ops. Returning a failure would repeatedly retry an event we intentionally do not handle.


---
**@realsama** on `app/services/payment_requests/payments/paystack_service.rb`:

```diff
+        payment ||= handle_missing_payment(organization_id, paystack_payment)
+        return result unless payment
+
+        if payment.payable.payment_succeeded?
+          result.payment = payment if payment.persisted?
+          result.payable = payment.payable if payment.persisted?
```

Applied. The repeated payment.persisted? branches are now consolidated.


---
**@vincent-pochet** on `app/services/invoices/payments/paystack_service.rb`:

```diff
+# frozen_string_literal: true
+
+module Invoices
+  module Payments
+    class PaystackService < BaseService
+      include Customers::PaymentProviderFinder
```

To align with some recent change in the Result definition for services, you now have to include `TypedResults` and define the result types for each method


---
**@vincent-pochet** on `app/services/payment_providers/paystack/customers/create_service.rb`:

```diff
+# frozen_string_literal: true
+
+module PaymentProviders
+  module Paystack
+    module Customers
+      class CreateService < BaseService
```

You have to define the Result:

```ruby
Result = BaseResult[:provider_customer]
```


---
**@vincent-pochet** on `app/services/payment_providers/paystack/payments/create_service.rb`:

```diff
+# frozen_string_literal: true
+
+module PaymentProviders
+  module Paystack
+    module Payments
+      class CreateService < BaseService
```

Same comment for the Result:

```ruby
Result = BaseResult[:payment, :error_message, :error_code, :reraise, :should_retry]
```


---
**@vincent-pochet** on `app/services/payment_providers/paystack_service.rb`:

```diff
@@ -0,0 +1,40 @@
+# frozen_string_literal: true
+
+module PaymentProviders
+  class PaystackService < BaseService
+    def create_or_update(**args)
```

Same comment for the Result
```ruby
Result = BaseResult[:paystack_provider]
```


---
**@vincent-pochet** on `app/services/payment_requests/payments/paystack_service.rb`:

```diff
+
+module PaymentRequests
+  module Payments
+    class PaystackService < BaseService
+      include Customers::PaymentProviderFinder
+      include Updatable
```

You also need the `TypedResults` include here


---
**@vincent-pochet** on `app/services/payment_providers/paystack/payments/create_service.rb`:

```diff
+        def charge_authorization_payload
+          {
+            amount: payment.amount_cents,
+            email: customer.email&.strip&.split(",")&.first,
+            authorization_code: authorization_code,
+            reference: reference,
```

When called from the `Invoices::Payments::CreateService`, this reference will have the format "Entity Name - Invoice xxxx", you should check if it can be used a reference (as an idem-potency key) in this case.

In other services, for example, you are using `reference: "lago-invoice-#{payment_intent.id}"


---
**@vincent-pochet** on `app/models/payment_provider_customers/paystack_customer.rb`:

```diff
+module PaymentProviderCustomers
+  class PaystackCustomer < BaseCustomer
+    PAYMENT_METHODS = %w[card].freeze
+
+    settings_accessors :authorization_code, :payment_method_id
+  end
```

You should override the `provider_payment_methods` from the parent class:

```ruby
def provider_payment_methods
  PAYMENT_METHODS
end
```

This would fix an inconsistency between the serializer (forcing `PAYMENT_METHODS`) and the GraphQL type (returning `nil`)


---
**@vincent-pochet** on `app/models/organization.rb`:

```diff
@@ -232,6 +233,8 @@ def payment_provider(provider)
       cashfree_payment_provider
     when "adyen"
       adyen_payment_provider
+    when "paystack"
```

This method is a legacy dead code, you can omit this line. We will clean up the method is a new pull request.


---
**@vincent-pochet** on `app/services/payment_providers/paystack/handle_event_service.rb`:

```diff
+        end
+
+        payable = find_payable(verified_metadata)
+        return result unless payable
+        return result if payable.payment_succeeded?
+        return amount_mismatch_failure(payable, verified_transaction) unless amount_matches?(payable, verified_transaction)
```

At this step, we are comparing the webhook amount to the `invoice.total_due_amount_cents` at processing time. Any credit note, partial payment, or wallet application landing between checkout and the webhook, would lead to a mismatch and finally a `service_failure!`. The `HandleEventJob` will raise and Sidekiq would retry forever, meaning that the real customer payment will never be recorded.
Other providers does not gates on this. You should compare against the payment/intent amount, or simply log-and-continue.


---
**@vincent-pochet** on `app/services/payment_provider_customers/paystack_service.rb`:

```diff
+      return unsupported_currency_result unless supported_currency?(authorization_currency)
+
+      create(paystack_customer) if paystack_customer.provider_customer_id.blank?
+      return result unless result.success?
+
+      paystack_result = client.initialize_transaction(setup_transaction_payload)
```

This path is capturing a "setup" amount, depending on the currency, but it seems that this amount is never refunded, reversed. Can you check and confirm the process?


---
**@realsama** on `app/services/invoices/payments/paystack_service.rb`:

```diff
+# frozen_string_literal: true
+
+module Invoices
+  module Payments
+    class PaystackService < BaseService
+      include Customers::PaymentProviderFinder
```

Added `TypedResults` and per-method result definitions in c7c54d37c. Both methods now use the shared service dispatcher.


---
**@realsama** on `app/services/payment_providers/paystack/customers/create_service.rb`:

```diff
+# frozen_string_literal: true
+
+module PaymentProviders
+  module Paystack
+    module Customers
+      class CreateService < BaseService
```

Added `Result = BaseResult[:provider_customer]` in c7c54d37c.


---
**@realsama** on `app/services/payment_providers/paystack/payments/create_service.rb`:

```diff
+# frozen_string_literal: true
+
+module PaymentProviders
+  module Paystack
+    module Payments
+      class CreateService < BaseService
```

Added the requested result fields in c7c54d37c.


---
**@realsama** on `app/services/payment_providers/paystack_service.rb`:

```diff
@@ -0,0 +1,40 @@
+# frozen_string_literal: true
+
+module PaymentProviders
+  class PaystackService < BaseService
+    def create_or_update(**args)
```

Added `Result = BaseResult[:paystack_provider]` in c7c54d37c.


---
**@realsama** on `app/services/payment_requests/payments/paystack_service.rb`:

```diff
+
+module PaymentRequests
+  module Payments
+    class PaystackService < BaseService
+      include Customers::PaymentProviderFinder
+      include Updatable
```

Added `TypedResults` with per-method result definitions and updated the callers in c7c54d37c.


---
**@realsama** on `app/services/payment_providers/paystack/payments/create_service.rb`:

```diff
+        def charge_authorization_payload
+          {
+            amount: payment.amount_cents,
+            email: customer.email&.strip&.split(",")&.first,
+            authorization_code: authorization_code,
+            reference: reference,
```

The reference is now `lago-payment-#{payment.id}`, stable for each payment. A duplicate response triggers verification of the original transaction, including identity, amount and currency checks, instead of creating a new charge (c842cb33f).


---
**@realsama** on `app/models/payment_provider_customers/paystack_customer.rb`:

```diff
+module PaymentProviderCustomers
+  class PaystackCustomer < BaseCustomer
+    PAYMENT_METHODS = %w[card].freeze
+
+    settings_accessors :authorization_code, :payment_method_id
+  end
```

Added the override returning `PAYMENT_METHODS`, with a model test, in c7c54d37c.


---
**@realsama** on `app/models/organization.rb`:

```diff
@@ -232,6 +233,8 @@ def payment_provider(provider)
       cashfree_payment_provider
     when "adyen"
       adyen_payment_provider
+    when "paystack"
```

Removed the Paystack branch from this legacy method in c7c54d37c.


---
**@realsama** on `app/services/payment_providers/paystack/handle_event_service.rb`:

```diff
+        end
+
+        payable = find_payable(verified_metadata)
+        return result unless payable
+        return result if payable.payment_succeeded?
+        return amount_mismatch_failure(payable, verified_transaction) unless amount_matches?(payable, verified_transaction)
```

Changed this to log and continue with the verified payment amount. Added tests for a partial payment and an invoice balance changing after checkout starts (c7c54d37c).


---
**@realsama** on `app/services/payment_provider_customers/paystack_service.rb`:

```diff
+      return unsupported_currency_result unless supported_currency?(authorization_currency)
+
+      create(paystack_customer) if paystack_customer.provider_customer_id.blank?
+      return result unless result.success?
+
+      paystack_result = client.initialize_transaction(setup_transaction_payload)
```

The old setup flow captured the amount and did not refund it. I removed that flow for now; setup requests return `feature_not_supported`, matching Cashfree. Saving reusable cards from genuine payments is unchanged (7c4d5303f).

