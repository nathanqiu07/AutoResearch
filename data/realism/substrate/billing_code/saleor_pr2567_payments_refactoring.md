---
source: https://github.com/saleor/saleor/pull/2567
retrieved: 2026-11-15
license: public GitHub issue (GitHub Terms of Service); repository license BSD-3-Clause
---

# Payments refactoring  (#2567, closed)

opened by @artursmet on 2018-08-14T14:53:12Z  labels: 

Completly refactored the payments process.
- Django payments was dropped
- Payment process consists of Payment instances, which are storing the information about the price/billing information and Transactions, which are single actions performed on the Payment (eg. capture payment/authorize payment/void payment)

New payment approach is API-based.

close #2557 
close #2556 
close #3066 

## TODO:
- [x] Documentation for implementing new payment method
- [x] Adding Braintree payment gateway to the old checkout (or at least providing how-to guide)
- [ ] How-to-guide on adding a new payment gateway to the old checkout 
- [ ] Guide about using Braintree on a sandbox environment (it's tricky)
- [x] Transform Payment and Transactions into immutable Decimal fields with currency as CharField
- [ ] Tests
- [x] Error handling on not successful transactions
- [ ] Tests. Loads of tests
- [x] Importing data from Payment to PaymentMethod
- [ ] List transactions on the old dashboard?
- [x] Rename PaymentMethod back to Payment?
- [ ] Adjust storefront 2.0 to the new payment flow


---
**@codecov[bot]** commented on 2018-08-23T12:35:43Z:

# [Codecov](https://codecov.io/gh/mirumee/saleor/pull/2567?src=pr&el=h1) Report
> :exclamation: No coverage uploaded for pull request base (`master@baeefb8`). [Click here to learn what that means](https://docs.codecov.io/docs/error-reference#section-missing-base-commit).
> The diff coverage is `82.02%`.

[![Impacted file tree graph](https://codecov.io/gh/mirumee/saleor/pull/2567/graphs/tree.svg?width=650&token=qkNcTJ4TmI&height=150&src=pr)](https://codecov.io/gh/mirumee/saleor/pull/2567?src=pr&el=tree)

```diff
@@            Coverage Diff            @@
##             master    #2567   +/-   ##
=========================================
  Coverage          ?   89.33%           
=========================================
  Files             ?      222           
  Lines             ?    12391           
  Branches          ?     1230           
=========================================
  Hits              ?    11070           
  Misses            ?      933           
  Partials          ?      388
```


| [Impacted Files](https://codecov.io/gh/mirumee/saleor/pull/2567?src=pr&el=tree) | Coverage Δ | |
|---|---|---|
| [saleor/shipping/models.py](https://codecov.io/gh/mirumee/saleor/pull/2567/diff?src=pr&el=tree#diff-c2FsZW9yL3NoaXBwaW5nL21vZGVscy5weQ==) | `84.7% <ø> (ø)` | |
| [saleor/product/models.py](https://codecov.io/gh/mirumee/saleor/pull/2567/diff?src=pr&el=tree#diff-c2FsZW9yL3Byb2R1Y3QvbW9kZWxzLnB5) | `92.33% <ø> (ø)` | |
| [saleor/dashboard/order/urls.py](https://codecov.io/gh/mirumee/saleor/pull/2567/diff?src=pr&el=tree#diff-c2FsZW9yL2Rhc2hib2FyZC9vcmRlci91cmxzLnB5) | `100% <ø> (ø)` | |
| [saleor/discount/models.py](https://codecov.io/gh/mirumee/saleor/pull/2567/diff?src=pr&el=tree#diff-c2FsZW9yL2Rpc2NvdW50L21vZGVscy5weQ==) | `81.98% <ø> (ø)` | |
| [saleor/payment/gateways/braintree/errors.py](https://codecov.io/gh/mirumee/saleor/pull/2567/diff?src=pr&el=tree#diff-c2FsZW9yL3BheW1lbnQvZ2F0ZXdheXMvYnJhaW50cmVlL2Vycm9ycy5weQ==) | `0% <0%> (ø)` | |
| [saleor/core/utils/taxes.py](https://codecov.io/gh/mirumee/saleor/pull/2567/diff?src=pr&el=tree#diff-c2FsZW9yL2NvcmUvdXRpbHMvdGF4ZXMucHk=) | `98.18% <100%> (ø)` | |
| [saleor/dashboard/views.py](https://codecov.io/gh/mirumee/saleor/pull/2567/diff?src=pr&el=tree#diff-c2FsZW9yL2Rhc2hib2FyZC92aWV3cy5weQ==) | `50% <100%> (ø)` | |
| [saleor/graphql/checkout/resolvers.py](https://codecov.io/gh/mirumee/saleor/pull/2567/diff?src=pr&el=tree#diff-c2FsZW9yL2dyYXBocWwvY2hlY2tvdXQvcmVzb2x2ZXJzLnB5) | `100% <100%> (ø)` | |
| [saleor/dashboard/order/views.py](https://codecov.io/gh/mirumee/saleor/pull/2567/diff?src=pr&el=tree#diff-c2FsZW9yL2Rhc2hib2FyZC9vcmRlci92aWV3cy5weQ==) | `79.25% <100%> (ø)` | |
| [saleor/payment/gateways/dummy/forms.py](https://codecov.io/gh/mirumee/saleor/pull/2567/diff?src=pr&el=tree#diff-c2FsZW9yL3BheW1lbnQvZ2F0ZXdheXMvZHVtbXkvZm9ybXMucHk=) | `100% <100%> (ø)` | |
| ... and [27 more](https://codecov.io/gh/mirumee/saleor/pull/2567/diff?src=pr&el=tree-more) | |

------

[Continue to review full report at Codecov](https://codecov.io/gh/mirumee/saleor/pull/2567?src=pr&el=continue).
> **Legend** - [Click here to learn more](https://docs.codecov.io/docs/codecov-delta)
> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`
> Powered by [Codecov](https://codecov.io/gh/mirumee/saleor/pull/2567?src=pr&el=footer). Last update [baeefb8...8e6c163](https://codecov.io/gh/mirumee/saleor/pull/2567?src=pr&el=lastupdated). Read the [comment docs](https://docs.codecov.io/docs/pull-request-comments).



---
**@NyanKiyoshi** commented on 2018-10-17T15:31:12Z:

Do you have any idea around what date range this will get merged to the master branch? So we can know whenever we will be able to start getting ready and spare time to release a new version of our django-payments dependent packages.

My guess is that it won't be until 2019 and a good few months, by looking at the roadmap?


---
**@Pacu2** commented on 2018-10-17T16:00:06Z:

@NyanKiyoshi It needs to be merged before the end of October. Getting there slowly


---
**@NyanKiyoshi** commented on 2018-10-17T16:27:39Z:

Okay. That sounds really close! Could you post an update or a ping whenever you think this PR is stable enough and in a working state to start releasing our own providers? (maybe it's already? I didn't have the time to check out yet).


---
**@Pacu2** commented on 2018-10-17T16:41:49Z:

@NyanKiyoshi I've made a mistake in my previous post, I meant end of October (so 2 weeks from now). I think it will be merged once it's stable-enough, with small fixes and improvements being added later. 


---
**@NyanKiyoshi** commented on 2018-10-18T13:22:33Z:

@Pacu2 alright, thank you. I'll probably be able to take a look at this in < 2 weeks. Thanks for the info.


---
**@NyanKiyoshi** commented on 2018-10-25T10:02:26Z:

@maarcingebala what do you think about enabling ReadTheDocs on `checkout-2.0` while it's a WiP ?


---
**@Pacu2** commented on 2018-10-25T10:04:24Z:

@NyanKiyoshi It will be merged in the next few days so I don't think it's worth it 


---
**@NyanKiyoshi** commented on 2018-10-25T10:09:22Z:

@Pacu2 alright, got it. Not this week though? (hopefully!)


---
**@Pacu2** commented on 2018-10-25T10:10:51Z:

@NyanKiyoshi Can't tell tho. Still have few fixes, and need to add Braintree to regular checkout 


---
**@NyanKiyoshi** commented on 2018-10-25T10:12:20Z:

Alright, time will tell. I should hopefully have time to request a little change on the documentation on Monday, but if it's merged before that, I will create a PR. It's fine!


---
**@NyanKiyoshi** commented on 2018-10-27T20:09:10Z:

That "Payment details" button is really light, thus almost invisible/ unreadable. Maybe it could be put a bit darker? Or as a button or something else? (in order details of a paid order).
![screenshot_2018-10-27_22-05-12](https://user-images.githubusercontent.com/6186720/47608844-7328ac00-da34-11e8-8987-7c1f6220d008.png)

https://github.com/mirumee/saleor/blob/ef38d4395bcfd9c986ab750c5326bcd30d7246d4/saleor/static/scss/components/_buttons.scss#L67-L70



## Review comments (inline, on diff)

---
**@maarcingebala** on `saleor/graphql/checkout/mutations.py`:

```diff
+        errors = []
+        checkout = cls.get_node_or_error(
+            info, checkout_id, errors, 'checkout_id', only_type=Checkout)
+        line = cls.get_node_or_error(
+            info, line_id, errors, 'line_id', only_type=CheckoutLine)
+        line.delete()
```

Two checks should be added before we can delete the line:
- ensure that this line belongs to this checkout
- ensure that the `line` is not None- it could be if there were errors returned by `get_node_or_error`.

Ideally we would pass a queryset of `checkout.lines.all()` to `get_nodes_or_error()` just as we do with `get_object_or_404()`, but that's a general improvement I want to add later.



---
**@akjanik** on `saleor/checkout/utils.py`:

```diff
+        if not cart.shipping_address:
+            return False, pgettext_lazy(
+                'order placement error', 'Shipping address is not set')
+    if not is_fully_paid(cart):
+        return False, pgettext_lazy(
+            'order placement error', 'CHeckout is not fully paid')
```

Typo `CHeckout`


---
**@akjanik** on `saleor/graphql/api.py`:

```diff
@@ -163,6 +188,12 @@ def resolve_category(self, info, id):
     def resolve_categories(self, info, level=None, query=None, **kwargs):
         return resolve_categories(info, level=level, query=query)
 
+    def resolve_cart_line(self, info, id):
```

I feel you mean `checkout_line`. There is also resolver missing, `checkout_lines`


---
**@akjanik** on `saleor/graphql/api.py`:

```diff
+    def resolve_payment_client_token(self, info, gateway=None):
+        return resolve_payment_client_token(gateway)
+
+    def resolve_payments(self, info, query=None, **kwargs):
+        return resolve_payment_methods(info, query)
+
```

Add simple tests to ensure queries are working, especially for `resolve_payment_client_token`, as it looks a little unusual.


---
**@akjanik** on `saleor/graphql/checkout/mutations.py`:

```diff
+
+
+class CheckoutCreate(ModelMutation):
+    class Arguments:
+        input = CheckoutCreateInput(
+            required=True, description='Data required to create Checkout')
```

To be consistent, please change to `Fields required to create a checkout.`.


---
**@Pacu2** on `saleor/checkout/utils.py`:

```diff
         add_variant_to_order(
             order, line.variant, line.quantity, discounts, taxes)
 
+    for payment_method in cart.payment_methods.all():
+        payment_method.order = order
+        payment_method.save(update_fields=['order'])
```

Can we use queryset's `update` function instead?


---
**@rafalp** on `saleor/checkout/utils.py`:

```diff
@@ -881,3 +885,22 @@ def create_order(cart, tracking_code, discounts, taxes):
 
     _fill_order_with_cart_data(order, cart, discounts, taxes)
     return order
+
+def is_fully_paid(cart: Cart):
```

Module-level function definitions not separated by two blank lines? Or are you leaving this to Yapf?


---
**@rafalp** on `saleor/checkout/forms.py`:

```diff
@@ -16,6 +16,7 @@
 from ..shipping.models import ShippingMethod, ShippingZone
 from ..shipping.utils import get_shipping_price_estimate
 from .models import Cart
+from ..payment.models import PaymentMethod
```

Import order seems weird. Shouldn't those be also grouped by depth?


---
**@rafalp** on `saleor/graphql/payment/resolvers.py`:

```diff
+from ..utils import filter_by_query_param
+
+PAYMENT_SEARCH_FIELDS = ['id']
+
+
+# @login_required
```

Code commented out.


---
**@NyanKiyoshi** on `docs/architecture/payments.rst`:

```diff
 ========
 
+Supported Gateways
+------------------
+
+The default configuration uses the *dummy* backend.
```

Maybe we would prefer
```suggestion
The default configuration uses the `dummy` backend.
```


---
**@NyanKiyoshi** on `docs/architecture/payments.rst`:

```diff
+------------------
+
+The default configuration uses the *dummy* backend.
+It's meant to allow developers to easily simulate different payment results.
+
+Here is a list of supported payment providers:
```

Could you put this under a sub section instead? So we can easily insert a third party payment provider section later on.

```suggestion
Supported payment providers
+++++++++++++++++++++++++++
```


---
**@NyanKiyoshi** on `docs/architecture/payments.rst`:

```diff
+
+Authorization and capture is a two-step process.
+
+Firstly the funds are locked on the payer's account but are not transferred to your bank.
+
+Then depending on the provider and card type you have between a few days and a month to charge the card for an amount not exceeding the authorized amount.
```

I would suggest this:

```suggestion
Then depending on the provider and the card type, you have between a few days, and a month to charge the card for an amount not exceeding the authorized amount.
```


---
**@NyanKiyoshi** on `docs/architecture/payments.rst`:

```diff
+Firstly the funds are locked on the payer's account but are not transferred to your bank.
+
+Then depending on the provider and card type you have between a few days and a month to charge the card for an amount not exceeding the authorized amount.
+
+This is very useful when an exact price cannot be determined until after the order is prepared.
+It is also useful if your business prefers to manually screen orders for fraud attempts.
```

Or maybe also when we want to only capture the money as soon as we ship the order, like amazon does?


---
**@NyanKiyoshi** on `docs/architecture/payments.rst`:

```diff
+
+Refunds
+-------
+
+You can issue partial or full refunds for all captured payments.
+When you edit an order and remove items Saleor will also offer to automatically issue a partial refund.
```

```suggestion
When editing an order and removing items, Saleor will also offer to automatically issue a partial refund.
```


---
**@NyanKiyoshi** on `docs/guides/payments.rst`:

```diff
+.. _adding-payments:
+
+Payments
+========
+
+Integrating new Payment Gateway into Saleor
```

```suggestion
Integrating a new Payment Gateway into Saleor
```


---
**@NyanKiyoshi** on `docs/guides/payments.rst`:

```diff
+-------------------------------------------
+
+We are using a universal flow, that each provider should fulfill, there are
+several methods that should be implemented.
+
+Your changes should live under the
```

under the... namespace? Package? Not sure how it's called in Python?


---
**@NyanKiyoshi** on `docs/guides/payments.rst`:

```diff
+``saleor.payment.providers.<provider name>``.
+
+.. note::
+
+    After completing those changes your new payment gateway will be available
+    only from the API level. You also need to integrate it into your
```

I would say:
After completing those ~~changes~~ steps*,* your new payment gateway will **only** be available from API level. **You will also need to...**


---
**@Pacu2** on `docs/guides/payments.rst`:

```diff
+-------------------------------------------
+
+We are using a universal flow, that each provider should fulfill, there are
+several methods that should be implemented.
+
+Your changes should live under the
```

Module is good I think


---
**@Pacu2** on `docs/architecture/payments.rst`:

```diff
+Firstly the funds are locked on the payer's account but are not transferred to your bank.
+
+Then depending on the provider and card type you have between a few days and a month to charge the card for an amount not exceeding the authorized amount.
+
+This is very useful when an exact price cannot be determined until after the order is prepared.
+It is also useful if your business prefers to manually screen orders for fraud attempts.
```

That will do, thanks


---
**@NyanKiyoshi** on `saleor/payment/migrations/0002_transfer_payment_to_payment_method.py`:

```diff
+    if payment.status == PaymentStatus.INPUT:
+        return
+
+    # Other payments needed to be authorized first
+    created = payment.created
+    create_transaction(
```

I get this:

```
  Applying payment.0001_initial... OK
Traceback (most recent call last):
  File "/develop/saleor/manage.py", line 10, in <module>
    execute_from_command_line(sys.argv)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/core/management/__init__.py", line 371, in execute_from_command_line
    utility.execute()
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/core/management/__init__.py", line 365, in execute
    self.fetch_command(subcommand).run_from_argv(self.argv)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/core/management/base.py", line 288, in run_from_argv
    self.execute(*args, **cmd_options)
  Applying payment.0002_transfer_payment_to_payment_method...  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/core/management/base.py", line 335, in execute
    output = self.handle(*args, **options)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/core/management/commands/migrate.py", line 200, in handle
    fake_initial=fake_initial,
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/db/migrations/executor.py", line 117, in migrate
    state = self._migrate_all_forwards(state, plan, full_plan, fake=fake, fake_initial=fake_initial)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/db/migrations/executor.py", line 147, in _migrate_all_forwards
    state = self.apply_migration(state, migration, fake=fake, fake_initial=fake_initial)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/db/migrations/executor.py", line 244, in apply_migration
    state = migration.apply(state, schema_editor)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/db/migrations/migration.py", line 122, in apply
    operation.database_forwards(self.app_label, schema_editor, old_state, project_state)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/db/migrations/operations/special.py", line 190, in database_forwards
    self.code(from_state.apps, schema_editor)
  File "/develop/saleor/saleor/payment/migrations/0002_transfer_payment_to_payment_method.py", line 120, in transfer_payments_to_payment_methods
    create_transactions(payment_method, pay)
  File "/develop/saleor/saleor/payment/migrations/0002_transfer_payment_to_payment_method.py", line 61, in create_transactions
    is_success=True, token=payment.transaction_id)
TypeError: create_transaction() got an unexpected keyword argument 'currency'
```


---
**@NyanKiyoshi** on `saleor/settings.py`:

```diff
+            'public_key': os.environ.get('BRAINTREE_PUBLIC_KEY'),
+            'private_key': os.environ.get('BRAINTREE_PRIVATE_KEY')
+        }
+    }
+}
+if not DEBUG:
```

Is this whole block documented? I also feel like this code should be tested, it sounds really like something that would break and go unnoticed until the production phase.


---
**@NyanKiyoshi** on `saleor/payment/providers/braintree/__init__.py`:

```diff
+
+
+def transaction_and_incorrect_token_error(
+        payment: Payment,
+        token: str,
+        type: TransactionType,
```

I don't fully agree with that. It's not of type `TransactionType` but of `str`. What do you think about this issue?


---
**@NyanKiyoshi** on `saleor/payment/providers/braintree/__init__.py`:

```diff
+    if not errors:
+        return ''
+    default_msg = pgettext_lazy(
+        'payment error',
+        'Unable to process transaction. Please try again in a moment')
+    for error in errors:
```

Could we log errors to `stderr`? For example, I get this because I the DB is anonymized:
```python 
[{'code': '81813',
  'message': 'Postal code can only contain letters, numbers, spaces, and hyphens.'},
 {'code': '81813',
  'message': 'Postal code can only contain letters, numbers, spaces, and hyphens.'}]
```


---
**@NyanKiyoshi** on `saleor/payment/providers/braintree/__init__.py`:

```diff
+    gateway = get_gateway(**connection_params)
+    auth_transaction = payment.transactions.filter(
+        transaction_type=TransactionType.AUTH, is_success=True).first()
+    try:
+        result = gateway.transaction.void(
+            transaction_id=auth_transaction.token)
```

How to reproduce this error:
1. Fail a payment in braintree (get the `Unable to process transaction. Please try again in a moment` error):
2. Go to the order details;
3. Click on `Payment details`;
4. Click the big button `I understand, allow me to pay again`;
5. The error should occur.

```
ERROR django.request Internal Server Error: /en/order/f6b4d02a-3013-430d-8bf9-0281b0126343/cancel-payment/ [PID:10962:Thread-244]
Traceback (most recent call last):
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/core/handlers/exception.py", line 35, in inner
    response = get_response(request)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/core/handlers/base.py", line 119, in _get_response
    response = middleware_method(request, callback, callback_args, callback_kwargs)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/debug_toolbar/middleware.py", line 84, in process_view
    response = panel.process_view(request, view_func, view_args, view_kwargs)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/debug_toolbar/panels/profiling.py", line 155, in process_view
    return self.profiler.runcall(view_func, *args, **view_kwargs)
  File "/usr/lib64/python3.6/cProfile.py", line 109, in runcall
    return func(*args, **kw)
  File "/develop/saleor/saleor/order/utils.py", line 35, in decorator
    return func(*args, **kwargs)
  File "/develop/saleor/saleor/order/views.py", line 127, in cancel_payment
    form.save()
  File "/develop/saleor/saleor/order/forms.py", line 48, in save
    payment.void()
  File "/develop/saleor/saleor/payment/models.py", line 103, in void
    return utils.gateway_void(payment=self)
  File "/develop/saleor/saleor/payment/utils.py", line 61, in func
    return view(payment, *args, **kwargs)
  File "/develop/saleor/saleor/payment/utils.py", line 146, in gateway_void
    txn, error = provider.void(payment, **provider_params)
  File "/develop/saleor/saleor/payment/providers/braintree/__init__.py", line 215, in void
    transaction_id=auth_transaction.token)
AttributeError: 'NoneType' object has no attribute 'token'
ERROR django.request Internal Server Error: /en/order/f6b4d02a-3013-430d-8bf9-0281b0126343/cancel-payment/ [PID:10962:Thread-244]
Traceback (most recent call last):
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/core/handlers/exception.py", line 35, in inner
    response = get_response(request)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/django/core/handlers/base.py", line 119, in _get_response
    response = middleware_method(request, callback, callback_args, callback_kwargs)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/debug_toolbar/middleware.py", line 84, in process_view
    response = panel.process_view(request, view_func, view_args, view_kwargs)
  File "/develop/virtualenvs/dummy-saleor-env/lib/python3.6/site-packages/debug_toolbar/panels/profiling.py", line 155, in process_view
    return self.profiler.runcall(view_func, *args, **view_kwargs)
  File "/usr/lib64/python3.6/cProfile.py", line 109, in runcall
    return func(*args, **kw)
  File "/develop/saleor/saleor/order/utils.py", line 35, in decorator
    return func(*args, **kwargs)
  File "/develop/saleor/saleor/order/views.py", line 127, in cancel_payment
    form.save()
  File "/develop/saleor/saleor/order/forms.py", line 48, in save
    payment.void()
  File "/develop/saleor/saleor/payment/models.py", line 103, in void
    return utils.gateway_void(payment=self)
  File "/develop/saleor/saleor/payment/utils.py", line 61, in func
    return view(payment, *args, **kwargs)
  File "/develop/saleor/saleor/payment/utils.py", line 146, in gateway_void
    txn, error = provider.void(payment, **provider_params)
  File "/develop/saleor/saleor/payment/providers/braintree/__init__.py", line 215, in void
    transaction_id=auth_transaction.token)
AttributeError: 'NoneType' object has no attribute 'token'
```


---
**@NyanKiyoshi** on `docs/guides/payments.rst`:

```diff
+    def get_transaction_token(**connection_params: Dict) -> str:
+        gateway = get_gateway(**connection_params)
+        transaction_token = gateway.transaction_token.generate()
+        return transaction_token
+
+authorize(payment, transaction_token, **connection_params)
```

Over the docs, there are multiple warnings about put Python kwargs being empty bold instructions. Which also produces what seems to be an unwanted rendering.

The below patch fixes that.
```patch
Index: docs/guides/payments.rst
<+>UTF-8
===================================================================
--- docs/guides/payments.rst	(revision a4f77a9d22216905738c6442867871f0b48ea1fb)
+++ docs/guides/payments.rst	(date 1540673610000)
@@ -18,8 +18,8 @@
     available from the API level. You will also need to integrate it into your
     Frontend's workflow.
 
-get_transaction_token(**connection_params)
-^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
+get_transaction_token(\*\*connection_params)
+^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 
 A transaction token is a signed data blob that includes configuration and
 authorization information required by the payment provider.
@@ -37,8 +37,8 @@
         transaction_token = gateway.transaction_token.generate()
         return transaction_token
 
-authorize(payment, transaction_token, **connection_params)
-^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
+authorize(payment, transaction_token, \*\*connection_params)
+^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 
 A process of reserving the amount of money against the customer's funding
 source. Money does not change hands until the authorization is captured.
@@ -67,8 +67,8 @@
         return txn, response['error']
 
 
-refund(payment, amount, **connection_params)
-^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
+refund(payment, amount, \*\*connection_params)
+^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 
 Full or partial return of captured funds to the customer.
 
@@ -100,8 +100,8 @@
             gateway_response=get_gateway_response(response))
         return txn, response['error']
 
-capture(payment, amount, **connection_params)
-^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
+capture(payment, amount, \*\*connection_params)
+^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 
 A transfer of the money that was reserved during the authorization stage.
 
@@ -133,8 +133,8 @@
             gateway_response=get_gateway_response(response))
         return txn, response['error']
 
-void(payment, **connection_params)
-^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
+void(payment, \*\*connection_params)
+^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 
 A cancellation of a pending authorization or capture.
```


---
**@NyanKiyoshi** on `docs/guides/payments.rst`:

```diff
+Parameters
+^^^^^^^^^^
++-----------------------+-----------+------------------------------------------------------------------------------------------------+
+| name                  | type      | description                                                                                    |
++-----------------------+-----------+------------------------------------------------------------------------------------------------+
+| ``payment``           | `Payment` | Payment instance, for which the transaction will be created.                                   |
```

Not sure if that's accidental or not, but wouldn't it be better to put it in an inline code?

Below is a patch.
```patch
Index: docs/guides/payments.rst
<+>UTF-8
===================================================================
--- docs/guides/payments.rst	(revision a4f77a9d22216905738c6442867871f0b48ea1fb)
+++ docs/guides/payments.rst	(date 1540674255000)
@@ -167,29 +167,29 @@
 
 Parameters
 ^^^^^^^^^^
-+-----------------------+-----------+------------------------------------------------------------------------------------------------+
-| name                  | type      | description                                                                                    |
-+-----------------------+-----------+------------------------------------------------------------------------------------------------+
-| ``payment``           | `Payment` | Payment instance, for which the transaction will be created.                                   |
-+-----------------------+-----------+------------------------------------------------------------------------------------------------+
-| ``transaction_token`` | `str`     | Unique transaction's token that will be used on the purpose of completing the payment process. |
-+-----------------------+-----------+------------------------------------------------------------------------------------------------+
-| ``connection_params`` | `dict`    | List of parameters used for connecting to the payment's gateway.                               |
-+-----------------------+-----------+------------------------------------------------------------------------------------------------+
-| ``amount``            | `Decimal` | Amount of Money to be refunded/captured.                                                       |
-+-----------------------+-----------+------------------------------------------------------------------------------------------------+
++-----------------------+-------------+------------------------------------------------------------------------------------------------+
+| name                  | type        | description                                                                                    |
++-----------------------+-------------+------------------------------------------------------------------------------------------------+
+| ``payment``           | ``Payment`` | Payment instance, for which the transaction will be created.                                   |
++-----------------------+-------------+------------------------------------------------------------------------------------------------+
+| ``transaction_token`` | ``str``     | Unique transaction's token that will be used on the purpose of completing the payment process. |
++-----------------------+-------------+------------------------------------------------------------------------------------------------+
+| ``connection_params`` | ``dict``    | List of parameters used for connecting to the payment's gateway.                               |
++-----------------------+-------------+------------------------------------------------------------------------------------------------+
+| ``amount``            | ``Decimal`` | Amount of Money to be refunded/captured.                                                       |
++-----------------------+-------------+------------------------------------------------------------------------------------------------+
 
 Returns
 ^^^^^^^
-+-----------------------+---------------+-----------------------------------------------------------------------------------------------------------+
-| name                  | type          | description                                                                                               |
-+-----------------------+---------------+-----------------------------------------------------------------------------------------------------------+
-| ``txn``               | `Transaction` | Transaction created during the payment process, with ``is_success`` set to ``True`` if no error occurred. |
-+-----------------------+---------------+-----------------------------------------------------------------------------------------------------------+
-| ``error``             | `str`         | Error message to be displayed in the UI, empty if no error occurred.                                      |
-+-----------------------+---------------+-----------------------------------------------------------------------------------------------------------+
-| ``transaction_token`` | `str`         | Unique transaction's token that will be used on the purpose of completing the payment process.            |
-+-----------------------+---------------+-----------------------------------------------------------------------------------------------------------+
++-----------------------+-----------------+-----------------------------------------------------------------------------------------------------------+
+| name                  | type            | description                                                                                               |
++-----------------------+-----------------+-----------------------------------------------------------------------------------------------------------+
+| ``txn``               | ``Transaction`` | Transaction created during the payment process, with ``is_success`` set to ``True`` if no error occurred. |
++-----------------------+-----------------+-----------------------------------------------------------------------------------------------------------+
+| ``error``             | ``str``         | Error message to be displayed in the UI, empty if no error occurred.                                      |
++-----------------------+-----------------+-----------------------------------------------------------------------------------------------------------+
+| ``transaction_token`` | ``str``         | Unique transaction's token that will be used on the purpose of completing the payment process.            |
++-----------------------+-----------------+-----------------------------------------------------------------------------------------------------------+
 
 Adding new payment provider in the settings
 -------------------------------------------
```


---
**@NyanKiyoshi** on `saleor/payment/forms.py`:

```diff
+    def process_payment(self):
+        # FIXME add tests
+        self.instance.authorize(self.cleaned_data['payment_method_nonce'])
+        try:
+            self.instance.capture(self.instance.total)
+        except PaymentError as exc:
```

Note `PaymentError` is undefined.


---
**@NyanKiyoshi** on `saleor/payment/forms.py`:

```diff
+from . import ChargeStatus, TransactionType, get_provider
+from .models import Payment
+from .utils import gateway_authorize, gateway_capture, gateway_refund
+
+
+def get_form_for_payment(payment):
```

Is this debug or is it supposed to stay like that?

Edit: I would like to add that the docs doesn't tell us that we need to add forms to integrate a new payment provider, plus, we probably should have something acting as a simple base payment form that would act a bit like we had for the Stripe provider modal form, which was reusable for other custom providers.


---
**@NyanKiyoshi** on `saleor/payment/forms.py`:

```diff
+    elif payment.variant == settings.BRAINTREE:
+        return BraintreePaymentForm
+    raise ValueError('Unknown payment provider')
+
+
+class DummyPaymentForm(forms.Form):
```

That's really odd and sounds hard to maintain/ understand because we don't have an abstract base.


---
**@NyanKiyoshi** on `saleor/order/views.py`:

```diff
+                or payment.charge_status == ChargeStatus.FULLY_REFUNDED):
+            return redirect(order.get_absolute_url())
+        provider, provider_params = get_provider(payment.variant)
+        transaction_token = provider.get_transaction_token(**provider_params)
+        form = get_form_for_payment(payment)
+        form = form(data=request.POST or None, instance=payment)
```

What about `payment=payment` instead of (`django.forms.Form`) `instance=payment`? `instance` is really confusing, what is it? A provider? A payment? Something else?


---
**@NyanKiyoshi** on `saleor/order/views.py`:

```diff
+                or payment.charge_status == ChargeStatus.FULLY_REFUNDED):
+            return redirect(order.get_absolute_url())
+        provider, provider_params = get_provider(payment.variant)
+        transaction_token = provider.get_transaction_token(**provider_params)
+        form = get_form_for_payment(payment)
+        form = form(data=request.POST or None, instance=payment)
```

What do you think about passing `provider_params`? Like that:

```suggestion
        form = form(data=request.POST or None, provider_params=provider_params, instance=payment)
```
So we could access data to construct the form (e.g.: the public key to put in the `django.forms.widgets.Widget`'s `attrs` constructor parameter).


---
**@NyanKiyoshi** on `saleor/payment/utils.py`:

```diff
+def gateway_void(payment) -> Transaction:
+    if not can_be_voided(payment):
+        raise PaymentError('Only pre-authorized transactions can be voided.')
+    provider, provider_params = get_provider(payment.variant)
+    with transaction.atomic():
+        txn, error = provider.void(payment, **provider_params)
```

Wouldn't it be better to have a base behavior for non-mandatory features? Canceling an order is not supported by every provider, it would make sense to have a default behavior thanks to a `getattr`.


---
**@NyanKiyoshi** on `saleor/payment/utils.py`:

```diff
+            payment.total - payment.captured_amount):
+        raise PaymentError('Unable to capture more than authorized amount.')
+
+    provider, provider_params = get_provider(payment.variant)
+    with transaction.atomic():
+        txn, error = provider.capture(
```

In dashboard, if the provider doesn't support manual capturing, it now crashes when we try to capture. `django-payments` was checking whether manual capturing was supported or not.


---
**@Pacu2** on `saleor/payment/utils.py`:

```diff
+            payment.total - payment.captured_amount):
+        raise PaymentError('Unable to capture more than authorized amount.')
+
+    provider, provider_params = get_provider(payment.variant)
+    with transaction.atomic():
+        txn, error = provider.capture(
```

It's fixed on my local instance


---
**@Pacu2** on `saleor/order/views.py`:

```diff
+                or payment.charge_status == ChargeStatus.FULLY_REFUNDED):
+            return redirect(order.get_absolute_url())
+        provider, provider_params = get_provider(payment.variant)
+        transaction_token = provider.get_transaction_token(**provider_params)
+        form = get_form_for_payment(payment)
+        form = form(data=request.POST or None, instance=payment)
```

It's fixed on my local instance


---
**@Pacu2** on `saleor/payment/forms.py`:

```diff
+    elif payment.variant == settings.BRAINTREE:
+        return BraintreePaymentForm
+    raise ValueError('Unknown payment provider')
+
+
+class DummyPaymentForm(forms.Form):
```

Good point, I'll create an abstract base for this


---
**@Pacu2** on `saleor/payment/forms.py`:

```diff
+from . import ChargeStatus, TransactionType, get_provider
+from .models import Payment
+from .utils import gateway_authorize, gateway_capture, gateway_refund
+
+
+def get_form_for_payment(payment):
```

It's supposed to stay like that. Docs will be expanded once I'll have a more steady version of the old checkout. Preferably Monday 


---
**@Pacu2** on `saleor/payment/forms.py`:

```diff
+    def process_payment(self):
+        # FIXME add tests
+        self.instance.authorize(self.cleaned_data['payment_method_nonce'])
+        try:
+            self.instance.capture(self.instance.total)
+        except PaymentError as exc:
```

It's fixed on my local instance


---
**@Pacu2** on `docs/guides/payments.rst`:

```diff
+    def get_transaction_token(**connection_params: Dict) -> str:
+        gateway = get_gateway(**connection_params)
+        transaction_token = gateway.transaction_token.generate()
+        return transaction_token
+
+authorize(payment, transaction_token, **connection_params)
```

Good point, thanks


---
**@Pacu2** on `saleor/payment/providers/braintree/__init__.py`:

```diff
+    gateway = get_gateway(**connection_params)
+    auth_transaction = payment.transactions.filter(
+        transaction_type=TransactionType.AUTH, is_success=True).first()
+    try:
+        result = gateway.transaction.void(
+            transaction_id=auth_transaction.token)
```

It's fixed on my local instance


---
**@Pacu2** on `saleor/payment/providers/braintree/__init__.py`:

```diff
+
+
+def transaction_and_incorrect_token_error(
+        payment: Payment,
+        token: str,
+        type: TransactionType,
```

I think that TransactionType is a proper typing, as we are not expecting any string, but the one being part of transaction type choices


---
**@Pacu2** on `saleor/settings.py`:

```diff
+            'public_key': os.environ.get('BRAINTREE_PUBLIC_KEY'),
+            'private_key': os.environ.get('BRAINTREE_PRIVATE_KEY')
+        }
+    }
+}
+if not DEBUG:
```

It's debug-ish, will see if we want to leave it for good


---
**@Pacu2** on `docs/guides/payments.rst`:

```diff
+Parameters
+^^^^^^^^^^
++-----------------------+-----------+------------------------------------------------------------------------------------------------+
+| name                  | type      | description                                                                                    |
++-----------------------+-----------+------------------------------------------------------------------------------------------------+
+| ``payment``           | `Payment` | Payment instance, for which the transaction will be created.                                   |
```

Seems better, thanks


---
**@Pacu2** on `saleor/order/views.py`:

```diff
+                or payment.charge_status == ChargeStatus.FULLY_REFUNDED):
+            return redirect(order.get_absolute_url())
+        provider, provider_params = get_provider(payment.variant)
+        transaction_token = provider.get_transaction_token(**provider_params)
+        form = get_form_for_payment(payment)
+        form = form(data=request.POST or None, instance=payment)
```

Sure, if that would be helpful


---
**@NyanKiyoshi** on `saleor/payment/forms.py`:

```diff
+from . import ChargeStatus, TransactionType, get_provider
+from .models import Payment
+from .utils import gateway_authorize, gateway_capture, gateway_refund
+
+
+def get_form_for_payment(payment):
```

If it's supposed to stay that way, I'm fully against it. Here is my idea on the matter:

We could reuse the retrieved provider to retrieve the form instead of deciding which form to use from the payment variant name through a list of "hard-coded" cases.
https://github.com/mirumee/saleor/blob/a4f77a9d22216905738c6442867871f0b48ea1fb/saleor/order/views.py#L103-L106

Instead of getting the form from a payment method, I would suggest doing **`provider.get_form_class`** that would, for example, return a pointer to `saleor.payment.providers.braintree.forms.BraintreePaymentForm`. So the design pattern would be having the provider form, widgets, etc. in **`forms.py`**:
```
payment/
├── forms.py
├── __init__.py
├── providers
    ├── braintree
    │   ├── forms.py
    │   └── __init__.py
    ├── dummy
    │   ├── forms.py
    │   └── __init__.py
    └── __init__.py
```



---
**@Pacu2** on `saleor/payment/forms.py`:

```diff
+from . import ChargeStatus, TransactionType, get_provider
+from .models import Payment
+from .utils import gateway_authorize, gateway_capture, gateway_refund
+
+
+def get_form_for_payment(payment):
```

Yup, that's better in a long term


---
**@NyanKiyoshi** on `saleor/payment/utils.py`:

```diff
+def gateway_void(payment) -> Transaction:
+    if not can_be_voided(payment):
+        raise PaymentError('Only pre-authorized transactions can be voided.')
+    provider, provider_params = get_provider(payment.variant)
+    with transaction.atomic():
+        txn, error = provider.void(payment, **provider_params)
```

I was thinking about `get_transaction_token` too.


---
**@NyanKiyoshi** on `saleor/order/views.py`:

```diff
     ctx = {
         'form': form, 'payment': payment,
         'client_token': client_token, 'order': order}
-    return TemplateResponse(
-        request, [template, 'order/payment/default.html'], ctx)
+    return TemplateResponse(request, template, ctx)
```

What's the reason about dropping `order/payment/default.html`? It was really useful for gateways using modals, could we restore that?


---
**@NyanKiyoshi** on `saleor/payment/forms.py`:

```diff
+class PaymentForm(forms.Form):
+    """Abstract Payment form that should be used as a base for every
+    payment gateway implemented.
+    """
+
+    def __init__(self, payment, gateway, gateway_params, *args, **kwargs):
```

In a future PR, that would great to add some typing! :tada: 


---
**@NyanKiyoshi** on `saleor/payment/gateways/braintree/errors.py`:

```diff
+    '81710',  # Expiration date is invalid.
+    '81711',  # Expiration year is invalid. It must be between 1975 and 2201.
+    '81712',  # Expiration month is invalid.
+    '81713',  # Expiration year is invalid.
+]
+INCORRECT_ADDRESS_ERRORS = [
```

Note for the upcoming clean up: this is value is being overridden.


---
**@NyanKiyoshi** on `saleor/payment/utils.py`:

```diff
+    if not payment.can_refund():
+        raise PaymentError('This payment cannot be refunded.')
+
+    gateway, gateway_params = get_payment_gateway(payment.gateway)
+    with transaction.atomic():
+        txn, error = gateway.refund(payment, amount, **gateway_params)
```

I think that would be better to pass the parameters as keywords: `gateway.refund(payment=payment, amount=amount, **gateway_params)`. (idem for the other `gateway.*` calls)


---
**@NyanKiyoshi** on `saleor/order/views.py`:

```diff
     ctx = {
         'form': form, 'payment': payment,
         'client_token': client_token, 'order': order}
-    return TemplateResponse(
-        request, [template, 'order/payment/default.html'], ctx)
+    return TemplateResponse(request, template, ctx)
```

*Resolved.*


---
**@NyanKiyoshi** on `saleor/payment/forms.py`:

```diff
+class PaymentForm(forms.Form):
+    """Abstract Payment form that should be used as a base for every
+    payment gateway implemented.
+    """
+
+    def __init__(self, payment, gateway, gateway_params, *args, **kwargs):
```

*Resolved.*


---
**@NyanKiyoshi** on `saleor/payment/models.py`:

```diff
+    """
+    created = models.DateTimeField(auto_now_add=True, editable=False)
+    payment = models.ForeignKey(
+        Payment, related_name='transactions', on_delete=models.PROTECT)
+    token = models.CharField(max_length=128, blank=True, default='')
+    kind = models.CharField(max_length=10, choices=TransactionKind.CHOICES)
```

I think we should index this field or add a flag instead of `CharField`, as we use it to filter transactions when we are refunding.


---
**@NyanKiyoshi** on `saleor/payment/gateways/braintree/__init__.py`:

```diff
+        payment: Payment,
+        amount: Decimal,
+        **connection_params: Dict) -> Tuple[Transaction, str]:
+    gateway = get_braintree_gateway(**connection_params)
+    capture_txn = payment.transactions.filter(
+        kind=TransactionKind.CAPTURE, is_success=True).first()
```

Should we handle the case where `capture_txn` is `None`? Maybe return an error?


---
**@NyanKiyoshi** on `saleor/payment/models.py`:

```diff
+    billing_city_area = models.CharField(max_length=128, blank=True)
+    billing_postal_code = models.CharField(max_length=256, blank=True)
+    billing_country_code = models.CharField(max_length=2, blank=True)
+    billing_country_area = models.CharField(max_length=256, blank=True)
+    billing_email = models.EmailField(blank=True)
+    customer_ip_address = models.GenericIPAddressField(blank=True, null=True)
```

Wouldn't we need the billing phone number as well? It's useful for some gateways.


---
**@Pacu2** on `saleor/payment/models.py`:

```diff
+    billing_city_area = models.CharField(max_length=128, blank=True)
+    billing_postal_code = models.CharField(max_length=256, blank=True)
+    billing_country_code = models.CharField(max_length=2, blank=True)
+    billing_country_area = models.CharField(max_length=256, blank=True)
+    billing_email = models.EmailField(blank=True)
+    customer_ip_address = models.GenericIPAddressField(blank=True, null=True)
```

Was wondering if that's not too much in terms of GDPR, is phone required for the process?



---
**@NyanKiyoshi** on `saleor/payment/models.py`:

```diff
+    billing_city_area = models.CharField(max_length=128, blank=True)
+    billing_postal_code = models.CharField(max_length=256, blank=True)
+    billing_country_code = models.CharField(max_length=2, blank=True)
+    billing_country_area = models.CharField(max_length=256, blank=True)
+    billing_email = models.EmailField(blank=True)
+    customer_ip_address = models.GenericIPAddressField(blank=True, null=True)
```

In the case of the payment gateway I'm targeting, it's to pass the phone number to the client's browser (toggle available in `settings.py`), with the user required to confirm they want to send their phone number shown on the screen to the advertised gateway.

It's not needed for the process, but required that user provides a phone number to finalize the client side process that will be sent from the client browser to the gateway.

I'm not sure how much it affects the GDPR, since we already have the phone number in the order address (which is an optional field), I think it could be acceptable as we don't give it away and it's not a nominative information. I may be really wrong, I have really limited knowledge on the subject.

