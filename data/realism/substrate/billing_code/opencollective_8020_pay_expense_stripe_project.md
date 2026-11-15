---
source: https://github.com/opencollective/opencollective/issues/8020
retrieved: 2026-11-15
license: public GitHub issue (GitHub Terms of Service); repository license MIT
---

# [Project] Pay Expense (Stripe) Functionality  (#8020, closed)

opened by @Betree on 2025-06-10T13:31:58Z  labels: project

## Overview

Create payment pages which expense submitters can use to request that an off-platform payment be made via Stripe (credit card/bank transfer, etc.).

## Ownership

**Owner:** @hdiniz
<!-- Add the following roles as they develop, again discuss ownership before @mentioning -->
<!-- **Product:** -->
<!-- **Design:** -->
**Engineering:** @hdiniz, @betree
<!-- **Documentation:**  -->

## Desired Outcomes

- Expenses that are issued by administrators of (financially active) organizations have payment URL’s through which payment can be made (via Stripe).
- Expense payment URL’s are accessible to both logged-off and logged-on users.
- Expense submitters who are admins of (financially active) organizations can mark an expense as “requires payment.”
- Platform settlement expenses are automatically marked as “requires payment.”
- Admins of accounts (collectives or organizations) that are required to pay an expense cannot mark the expense as paid.
- When an expense that was marked as “requires payment” is ACTUALLY paid it is automatically marked as paid on the platform.



---
**@Betree** commented on 2025-06-16T12:32:40Z:

**This week**
- [x] Engineering call to review technical proposal
- [x] Handle expense in Stripe webhook (metadata)
- [x] MVP UI for paying expenses
- [ ] Investigate refunds/reject/disputes


---
**@Betree** commented on 2025-06-23T12:27:51Z:

**This week**
- [ ] Unauthenticated payments (public URL)
- [ ] Limit to settlements


---
**@gustavlrsn** commented on 2025-06-30T12:16:46Z:

**This week**
- [ ] Continue working on unauthenticated payments
- [ ] Sync: figure out UX


---
**@Betree** commented on 2025-07-07T12:30:13Z:

**This week**
- [x] Merge PR to make Stripe payment method the default for settlements (if there's no previous one)
- [x] Deploy
- [ ] Run the new settlements to test it out


---
**@kewitz** commented on 2025-07-14T12:16:52Z:

**This week**
- [x] Review and merge E2E tests
- [x] Add reminder for next month: check automatic payout method logic

