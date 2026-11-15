---
source: https://github.com/medusajs/medusa/issues/13301
retrieved: 2026-11-15
license: public GitHub issue (GitHub Terms of Service); repository license NOASSERTION
---

# [Bug]: core stripe payment integration - double /capture api  (#13301, closed)

opened by @420coupe on 2025-08-26T06:37:16Z  labels: version: 2.0

### Package.json file

```JSON
{
  "name": "medusa-starter-default",
  "version": "0.0.1",
  "description": "A starter for Medusa projects.",
  "author": "Medusa (https://medusajs.com)",
  "license": "MIT",
  "keywords": [
    "sqlite",
    "postgres",
    "typescript",
    "ecommerce",
    "headless",
    "medusa"
  ],
  "scripts": {
    "build": "medusa build",
    "seed": "medusa exec ./src/scripts/seed.ts",
    "start": "medusa start -p 9777",
    "dev": "medusa develop -p 9777",
    "test:integration:http": "TEST_TYPE=integration:http NODE_OPTIONS=--experimental-vm-modules jest --silent=false --runInBand --forceExit",
    "test:integration:modules": "TEST_TYPE=integration:modules NODE_OPTIONS=--experimental-vm-modules jest --silent --runInBand --forceExit",
    "test:unit": "TEST_TYPE=unit NODE_OPTIONS=--experimental-vm-modules jest --silent --runInBand --forceExit",
    "full-cost-reconcile": "node -r dotenv/config -r ts-node/register src/scripts/full-cost-reconciliation.ts",
    "per-message-costs": "node -r dotenv/config -r ts-node/register src/scripts/per-message-cost-tracker.ts",
    "monitor-db-pool": "node -r dotenv/config -r ts-node/register src/scripts/monitor-db-pool.ts",
    "backfill-tiers": "medusa exec ./src/scripts/backfill-customer-tiers-merged.ts"
  },
  "dependencies": {
    "@medusajs/admin-sdk": "latest",
    "@medusajs/cli": "latest",
    "@medusajs/framework": "latest",
    "@medusajs/medusa": "latest",
    "@mikro-orm/core": "6.4.3",
    "@mikro-orm/knex": "6.4.3",
    "@mikro-orm/migrations": "6.4.3",
    "@mikro-orm/postgresql": "6.4.3",
    "@sendgrid/eventwebhook": "^8.0.0",
    "awilix": "^8.0.1",
    "multer": "^1.4.5-lts.1",
    "pg": "^8.13.0",
    "twilio": "^5.3.3"
  },
  "devDependencies": {
    "@medusajs/test-utils": "latest",
    "@mikro-orm/cli": "6.4.3",
    "@swc/core": "1.5.7",
    "@swc/jest": "^0.2.36",
    "@types/jest": "^29.5.13",
    "@types/multer": "^1.4.12",
    "@types/node": "^20.0.0",
    "@types/react": "^18.3.2",
    "@types/react-dom": "^18.2.25",
    "jest": "^29.7.0",
    "prop-types": "^15.8.1",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "ts-node": "^10.9.2",
    "typescript": "^5.6.2",
    "vite": "^5.2.11",
    "yalc": "^1.0.0-pre.53"
  },
  "engines": {
    "node": ">=20"
  },
  "packageManager": "yarn@3.2.3+sha512.f26f951f67de0c6a33ee381e5ff364709c87e70eb5e65c694e4facde3512f1fa80b8679e6ba31ce7d340fbb46f08dd683af9457e240f25a204be7427940d767e"
}
```

### Node.js version

v20.18.1

### Database and its version

PostgreSQL 15.6

### Operating system name and version

Ubuntu 25.04

### Browser name

Brave

### What happended?

The stripe endpoint /capture is called twice on a ``processPaymentWorkflow`` event whether manual or automatic capture from medusa-config.ts. I even tested with two different version frontend package versions and see the results below:

Default versions used by medusajs packages (core medusa stripe integration and nextjs-starter) 

```log
backend medusajs: 
@medusajs/medusa@2.9.0 invalid: "latest" from the root project
  └─┬ @medusajs/payment-stripe@2.9.0
    └── stripe@15.12.0
```
```log
frontend nextjs:
├── @stripe/react-stripe-js@1.16.5
├── @stripe/stripe-js@1.54.2
```
Here find the following: Multiple calls to stripe /capture api endpoint 

1. top manual capture
``"capture_method": "manual"``
2. bottom automatic 
``"capture_method": "automatic"``

<img width="1804" height="610" alt="Image" src="https://github.com/user-attachments/assets/a62c4e0a-7e38-41ee-ab5c-ae515629eb91" />

Different package version frontend
```log
backend medusajs: 
@medusajs/medusa@2.9.0 invalid: "latest" from the root project
  └─┬ @medusajs/payment-stripe@2.9.0
    └── stripe@15.12.0
```
```log
frontend nextjs:
├── @stripe/react-stripe-js@3.9.2
├── @stripe/stripe-js@7.9.0
```
Here find the following: mutiple calls to strpipe /capture api endpoint on manual, 1 /capture and 1 /cancel on auto

1. top manual capture
``"capture_method": "manual"``
2. bottom automatic 
``"capture_method": "automatic"``

<img width="1830" height="588" alt="Image" src="https://github.com/user-attachments/assets/138b41ec-44c5-473e-8277-13426f3ee166" />










Payment is successfully captured in both scenarios with both package versions. However at times there can occur a race condition between the capture events and the .confirmPayment on the nextjs frontend leading to a refund after an order is successfully processed and fulfilled in the case of digital products. 

### Expected behavior

1. payment intent created
2. .confirmPayment - if ``capture: true`` this is where payment is collected as ``"capture_method": "automatic"`` is passed due to the config below in medusa-config.ts
```ts
{
      resolve: "@medusajs/medusa/payment",
      options: {
        providers: [
          {
            resolve: "@medusajs/medusa/payment-stripe",
            id: "stripe",
            options: {
              apiKey: process.env.STRIPE_API_KEY,
              webhookSecret: process.env.STRIPE_WEBHOOK,
              automatic_payment_methods: true,
              capture: true,
            },
          },
        ],
      },
    },
```
3. order created after success response from .confirmPayment
4. There would be no need for the /capture api calls if ``capture: true``

### Actual behavior

1. payment intent created
2. .confirmPayment - payment is captured  - race conditions occur 1/1000
3. order created after success response from .confirmPayment  
4. ``processPaymentWorkflow`` - /capture api call
5. ``processPaymentWorkflow`` - /capture api call (from webhook response) 

### Link to reproduction repo

https://github.com/medusajs/medusa-starter-default/


---
**@420coupe** commented on 2025-09-03T20:26:43Z:

To clarify the race condition actually occurs from .confirmPayment and the paymentWebhook. 

When option ``capture:true``  is set the .confirmPayment() is sent with the ``confirmation_method: "automatic",`` so payment is collected in the .confirmPayment() step. After payment is confirmed ``cart/[id]/complete`` is called where ``processPaymentWorkflow`` is called. 

Then the paymentWebhook is hit and if the status is ``authorized or succeeded``  webhook also runs ``processPaymentWorkflow``. This causes the race condition. 


---
**@radeknapora** commented on 2025-09-10T08:47:44Z:

@willbouch @olivermrbl - sorry for tagging, but I’d like to bump this issue as it’s a serious problem in my case as well.
As @420coupe described, the race condition between .confirmPayment() and the paymentWebhook sometimes leads to orders not appearing in the admin dashboard, which makes it critical for production use.

Also, as seen from the reactions here, this seems to affect multiple users.

Could you please take a look at this? 🙏
Thanks in advance!


---
**@willbouch** commented on 2025-09-10T11:57:12Z:

Yes, this does look like a nasty little bug. Will take a look asap


---
**@420coupe** commented on 2025-09-22T21:28:57Z:

Any update on this? Seems to be occurring much more frequently (1/~~50~~20)


---
**@willbouch** commented on 2025-09-23T12:01:52Z:

I am sorry, I haven't had time to take a look at it yet. It is still in my todo list :/


---
**@420coupe** commented on 2025-09-24T05:42:29Z:

> I am sorry, I haven't had time to take a look at it yet. It is still in my todo list :/

I'm pretty sure this is a simple fix, just need a check on the process-payment call so if/when it gets called from the webhook it ignores it as it's already successfully processed. 

Double check but i'm 99% sure this is a simple solution for this issue. @willbouch 

edit - see PR above. 


---
**@adrien2p** commented on 2025-09-24T12:24:14Z:

hey @420coupe, thank you for the pr and issue, but I have a few questions before proceeding further.
Wich locking module have you configured? cause here the thing, the complete cart workflow acquire a lock upon execution, meaning that the first to acquire it will run through and the one that is queued will execute only after completion. therefore, the next run should return the already created order.


---
**@420coupe** commented on 2025-09-24T16:01:30Z:

> hey [@420coupe](https://github.com/420coupe), thank you for the pr and issue, but I have a few questions before proceeding further. Wich locking module have you configured? cause here the thing, the complete cart workflow acquire a lock upon execution, meaning that the first to acquire it will run through and the one that is queued will execute only after completion. therefore, the next run should return the already created order.

I have it in a production environment with server, worker and redis each dockerized in it's own container. 

The second to run fails and gets response below and initiates a refund - in some cases reverses order that may have already been fulfilled as in my case with digital products. 

```log
Cart cart_xxxx is already completed. 

ERR Encountered an error when trying to delete payment session - payses_xxxx - Error: An error occurred in cancelPayment: You cannot cancel this PaymentIntent because it has a status of succeeded. Only a PaymentIntent with one of the following statuses may be canceled:requires_payment_method, requires_capture, requires_confirmation, requires_action, processing...
```

Should we keep the convo here on in the PR?


---
**@adrien2p** commented on 2025-09-24T16:27:22Z:

I believe we can keep the convo here.m 👌
And the locking module you are using is it the redis one or the Inmemory one?

Because there is two things, the payment workflow up ont calling the complete cart workflow has a continueOnPermantFailure, so there shouldn’t be any compensation there, which seems different for you. Also, there is the lock in the complete cart, which means the workflow on the second run should return the order without doing anything 🤔

It means that there is something else at play. 


---
**@420coupe** commented on 2025-09-24T17:05:28Z:

> I believe we can keep the convo here.m 👌 And the locking module you are using is it the redis one or the Inmemory one?
> 
> Because there is two things, the payment workflow up ont calling the complete cart workflow has a continueOnPermantFailure, so there shouldn’t be any compensation there, which seems different for you. Also, there is the lock in the complete cart, which means the workflow on the second run should return the order without doing anything 🤔
> 
> It means that there is something else at play.

I am using the actual redis instance, here's entire medusa-config.ts

with these env settings for db
```
DB_POOL_MIN=15
DB_POOL_MAX=70
DB_ACQUIRE_TIMEOUT=45000
DB_CREATE_TIMEOUT=20000
DB_DESTROY_TIMEOUT=3000
DB_IDLE_TIMEOUT=25000
DB_REAP_INTERVAL=2000
DB_CREATE_RETRY_INTERVAL=300
```

```ts
import { loadEnv, defineConfig } from "@medusajs/framework/utils";

loadEnv(process.env.NODE_ENV || "production", process.cwd());

module.exports = defineConfig({
  projectConfig: {
    databaseUrl: process.env.DATABASE_URL,
    // Database connection pool configuration for performance
    databaseDriverOptions: {
      connection: {
        ssl: { rejectUnauthorized: false },
      },
      pool: {
        min: parseInt(process.env.DB_POOL_MIN || "5"),
        max: parseInt(process.env.DB_POOL_MAX || "20"),
        acquireTimeoutMillis: parseInt(
          process.env.DB_ACQUIRE_TIMEOUT || "30000"
        ),
        createTimeoutMillis: parseInt(process.env.DB_CREATE_TIMEOUT || "15000"),
        destroyTimeoutMillis: parseInt(
          process.env.DB_DESTROY_TIMEOUT || "2000"
        ),
        idleTimeoutMillis: parseInt(process.env.DB_IDLE_TIMEOUT || "15000"),
        reapIntervalMillis: parseInt(process.env.DB_REAP_INTERVAL || "1000"),
        createRetryIntervalMillis: parseInt(
          process.env.DB_CREATE_RETRY_INTERVAL || "200"
        ),
      },
    },
    // Worker mode configuration for production deployment
    workerMode:
      (process.env.MEDUSA_WORKER_MODE as "shared" | "worker" | "server") ||
      "shared",
    // Redis URL for sessions, cache, and workflows
    redisUrl: process.env.REDIS_URL,
    http: {
      storeCors: process.env.STORE_CORS!,
      adminCors: process.env.ADMIN_CORS!,
      authCors: process.env.AUTH_CORS!,
      jwtSecret: process.env.JWT_SECRET || "supersecret",
      cookieSecret: process.env.COOKIE_SECRET || "supersecret",
    },
  },
  admin: {
    backendUrl: process.env.MEDUSA_BACKEND_URL,
    // Disable admin in worker mode
    disable: process.env.DISABLE_MEDUSA_ADMIN === "true",
  },
  modules: [
    // Production Redis modules for caching, events, and workflows
    {
      resolve: "@medusajs/medusa/cache-redis",
      options: {
        redisUrl: process.env.REDIS_URL,
      },
    },
    {
      resolve: "@medusajs/medusa/event-bus-redis",
      options: {
        redisUrl: process.env.REDIS_URL,
      },
    },
    {
      resolve: "@medusajs/medusa/workflow-engine-redis",
      options: {
        redis: {
          url: process.env.REDIS_URL,
        },
      },
    },
    {
      resolve: "@medusajs/medusa/locking",
      options: {
        providers: [
          {
            resolve: "@medusajs/medusa/locking-redis",
            id: "locking-redis",
            is_default: true,
            options: {
              redisUrl: process.env.REDIS_URL,
            },
          },
        ],
      },
    },
    // Custom modules
    {
      resolve: "./src/modules/digital-product",
    },
    {
      resolve: "./src/modules/marketing",
    },
    {
      resolve: "@medusajs/fulfillment",
      options: {
        providers: [
          {
            resolve: "@medusajs/fulfillment-manual",
            id: "manual",
          },
          {
            resolve: "./src/modules/digital-product-fulfillment",
            id: "digital",
          },
        ],
      },
    },
    {
      resolve: "@medusajs/medusa/notification",
      options: {
        providers: [
          {
            resolve: "@medusajs/medusa/notification-sendgrid",
            id: "sendgrid",
            options: {
              channels: ["email"],
              api_key: process.env.SENDGRID_API_KEY,
              from: process.env.SENDGRID_FROM,
            },
          },
          {
            resolve: "./src/modules/twilio",
            id: "twilio",
            options: {
              channels: ["sms"],
              account_sid: process.env.TWILIO_ACCOUNT_SID,
              auth_token: process.env.TWILIO_AUTH_TOKEN,
              messaging_service_sid: process.env.TWILIO_MESSAGING_SERVICE_SID,
            },
          },
        ],
      },
    },
    {
      resolve: "@medusajs/medusa/file",
      options: {
        providers: [
          {
            resolve: "@medusajs/medusa/file-s3",
            id: "s3",
            options: {
              file_url: process.env.SUPABASE_S3_FILE_URL,
              access_key_id: process.env.SUPABASE_S3_ACCESS_KEY,
              secret_access_key: process.env.SUPABASE_S3_SECRET_KEY,
              region: process.env.SUPABASE_S3_REGION,
              bucket: process.env.SUPABASE_S3_BUCKET,
              endpoint: process.env.SUPABASE_S3_ENDPOINT,
              prefix: process.env.SUPABASE_S3_PREFIX,
              additional_client_config: {
                forcePathStyle: true,
              },
            },
          },
        ],
      },
    },
    {
      resolve: "@medusajs/medusa/payment",
      options: {
        providers: [
          {
            resolve: "@medusajs/medusa/payment-stripe",
            id: "stripe",
            options: {
              apiKey: process.env.STRIPE_API_KEY,
              webhookSecret: process.env.STRIPE_WEBHOOK,
              automatic_payment_methods: true,
              capture: true,
            },
          },
        ],
      },
    },
  ],
});

```




edit: also i tried both in-memory and redis instance and race condition occurs in both. 

edit2: i see the images didnt take here are some examples of different fails. 

<img width="2383" height="1279" alt="Image" src="https://github.com/user-attachments/assets/5a47bd6f-0bc3-4760-a956-d7f2429a2bd2" />

<img width="2383" height="1279" alt="Image" src="https://github.com/user-attachments/assets/a4322f1c-f4eb-41ce-91d6-8378a750a697" />


This one was weird, Payment successful, no order was created unlike others where order gets created and reversed/left unfulfilled 

<img width="2383" height="1279" alt="Image" src="https://github.com/user-attachments/assets/480eb1a6-d9ee-4d7f-9fd4-9e05435c990c" />

This last one order created, Payment successful, no refund, order created but not fulfilled -skipped a bunch of steps 

<img width="2383" height="1279" alt="Image" src="https://github.com/user-attachments/assets/59750811-3ea9-4159-9a05-5df1d87a323b" />

 


---
**@adrien2p** commented on 2025-09-24T18:03:47Z:

So the steps that are skipped is because the order already exists so the flow will return it instead of re running everything which is what we would expect to happen when there is concurrent complete cart running. All those are for the same transaction id?

Edit: for info, the skipped correspond to the steps for which the when condition was not satisfied


---
**@420coupe** commented on 2025-09-24T18:09:09Z:

> So the steps that are skipped is because the order already exists so the flow will return it instead of re running everything which is what we would expect to happen when there is concurrent complete cart running. All those are for the same transaction id?
> 
> Edit: for info, the skipped correspond to the steps for which the when condition was not satisfied

Not necessarily, i provided one example that everything was successful and no order was created and there is no other corresponding workflow to the specific cart from the paymentIntent. 


---
**@adrien2p** commented on 2025-09-24T18:12:14Z:

Would you have the possibility (just in case) to test on the latest version as well just to be sure you are not missing any fixes as well. You are currently on 2.9.0 right?


---
**@420coupe** commented on 2025-09-24T18:16:14Z:

> Would you have the possibility (just in case) to test on the latest version as well just to be sure you are not missing any fixes as well. You are currently on 2.9.0 right?

No this is actually on 2.10.3 

```log
/server # npx medusa -v
Couldn't find tsconfig.json. tsconfig-paths will be skipped
╔════════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║   Medusa collects anonymous usage analytics                            ║
║   to help improve Medusa for all users.                                ║
║                                                                        ║
║   If you'd like to opt-out, you can use `medusa telemetry --disable`   ║
║                                                                        ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝
Medusa CLI version: 2.10.3
Medusa version: 2.10.3
  Note: this is the Medusa version for the site at: /server
```


---
**@adrien2p** commented on 2025-09-24T18:17:42Z:

But in your description you mentioned this:

backend medusajs: 
@medusajs/medusa@2.9.0 invalid: "latest" from the root project
  └─┬ @medusajs/payment-stripe@2.9.0
    └── stripe@15.12.0


---
**@420coupe** commented on 2025-09-24T18:20:13Z:

> But in your description you mentioned this:
> 
> backend medusajs: @medusajs/medusa@2.9.0 invalid: "latest" from the root project └─┬ @medusajs/payment-stripe@2.9.0 └── stripe@15.12.0

yea, that was when i originally posted. These current results are on latest. That's why i commented it was occurring more frequently after update. 

edit: my project deploys with 'latest' so always pulls current latest when i rebuild/re-deploy backend docker stack


---
**@adrien2p** commented on 2025-09-24T18:23:50Z:

Got it, we will have a deeper look trying to understand, cause the fix you have done won’t trully fix the issue if the read occurs right before the cart is committed after completion. Also, on a side note don’t forget to check the release not before upgrading to latest and re deploy as sometimes there can be manual actions needed. I am thinking about the next release there 😇

Ps: don’t forget migrations etc but I suppose it is already in your pipeline 


---
**@420coupe** commented on 2025-09-24T18:49:26Z:

> Got it, we will have a deeper look trying to understand, cause the fix you have done won’t trully fix the issue if the read occurs right before the cart is committed after completion. Also, on a side note don’t forget to check the release not before upgrading to latest and re deploy as sometimes there can be manual actions needed. I am thinking about the next release there 😇
> 
> Ps: don’t forget migrations etc but I suppose it is already in your pipeline

Appreciate the feedback, yes I have migrations included in my pipeline already. As far as breaking changes i typically update my repo that is applied on-top of base core repo. 


---
**@420coupe** commented on 2025-10-30T17:29:30Z:

@carlos-r-l-rodrigues @adrien2p  @willbouch are you guys able to re-open this issue. It still persist in 2.11.1 here is an updated examples that occurred on the latest version. Stripe backend still shows 2 additional attempts to process payment after it has already succeeded then the refund initiation occurs. 

updated package.json
```json
{
  "name": "medusa-starter-default",
  "version": "0.0.1",
  "description": "A starter for Medusa projects.",
  "author": "Medusa (https://medusajs.com)",
  "license": "MIT",
  "keywords": [
    "sqlite",
    "postgres",
    "typescript",
    "ecommerce",
    "headless",
    "medusa"
  ],
  "scripts": {
    "build": "medusa build",
    "seed": "medusa exec ./src/scripts/seed.ts",
    "start": "medusa start",
    "dev": "medusa develop",
    "test:integration:http": "TEST_TYPE=integration:http NODE_OPTIONS=--experimental-vm-modules jest --silent=false --runInBand --forceExit",
    "test:integration:modules": "TEST_TYPE=integration:modules NODE_OPTIONS=--experimental-vm-modules jest --silent --runInBand --forceExit",
    "test:unit": "TEST_TYPE=unit NODE_OPTIONS=--experimental-vm-modules jest --silent --runInBand --forceExit",
    "full-cost-reconcile": "node -r dotenv/config -r ts-node/register src/scripts/full-cost-reconciliation.ts",
    "per-message-costs": "node -r dotenv/config -r ts-node/register src/scripts/per-message-cost-tracker.ts",
    "backfill-tiers": "medusa exec ./src/scripts/backfill-customer-tiers-merged.ts",
    "predeploy": "medusa db:migrate",
    "docker:build": "docker build -t derftuned-medusa .",
    "docker:up": "docker compose up --build -d",
    "docker:down": "docker compose down",
    "docker:logs": "docker compose logs -f"
  },
  "dependencies": {
    "@medusajs/admin-sdk": "latest",
    "@medusajs/cli": "latest",
    "@medusajs/framework": "latest",
    "@medusajs/medusa": "latest",
    "@sendgrid/eventwebhook": "^8.0.0",
    "multer": "^1.4.5-lts.1",
    "twilio": "^5.3.3"
  },
  "devDependencies": {
    "@medusajs/test-utils": "latest",
    "@swc/core": "1.5.7",
    "@swc/jest": "^0.2.36",
    "@types/jest": "^29.5.13",
    "@types/multer": "^1.4.12",
    "@types/node": "^20.0.0",
    "@types/react": "^18.3.2",
    "@types/react-dom": "^18.2.25",
    "jest": "^29.7.0",
    "prop-types": "^15.8.1",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "ts-node": "^10.9.2",
    "typescript": "^5.6.2",
    "vite": "^5.2.11",
    "yalc": "^1.0.0-pre.53"
  },
  "engines": {
    "node": ">=20"
  }
}
```

<img width="721" height="442" alt="Image" src="https://github.com/user-attachments/assets/1f6c5b13-eaec-4dab-a48c-f1e0db29aed7" />

<img width="1803" height="1279" alt="Image" src="https://github.com/user-attachments/assets/031c1b88-b0b1-4522-ab27-585552518471" />

```json
{
  "id": "wf_exec_01K8SHTR0CWFDHKY8KBCHG4NHZ",
  "workflow_id": "complete-cart",
  "transaction_id": "cart_01K8SHMRP2CJ4JA6K1JK8K5X85",
  "context": {
    "data": {
      "invoke": {
        "validate": {
          "__type": "Symbol(WorkflowWorkflowData)",
          "output": {
            "__type": "Symbol(WorkflowStepResponse)"
          }
        },
        "cart-query": {
          "__type": "Symbol(WorkflowWorkflowData)",
          "output": {
            "__type": "Symbol(WorkflowStepResponse)",
            "output": {
              "data": {
                "id": "cart_01K8SHMRP2CJ4JA6K1JK8K5X85",
                "email": "customer@hotmail.com",
                "items": [
                  {
                    "id": "cali_01K8SHMS4YQ240XW7FA1WXRDRM",
                    "title": "DerfTuned Motorsports Digital Art - 022",
                    "total": 25,
                    "cart_id": "cart_01K8SHMRP2CJ4JA6K1JK8K5X85",
                    "variant": {
                      "id": "variant_01K8P58KCHRX1P7EW736WFEPC5",
                      "product": {
                        "id": "prod_01K8P58K429BGTAWBGP7CQ72QK",
                        "is_giftcard": false,
                        "shipping_profile": {
                          "id": "sp_01J9Z46H06YD75WG5NRN6D676R"
                        }
                      },
                      "product_id": "prod_01K8P58K429BGTAWBGP7CQ72QK",
                      "allow_backorder": true,
                      "inventory_items": [
                        {
                          "inventory": {
                            "id": "iitem_01K8P58KEDNQ7VMVHK0A6JA89P",
                            "location_levels": [
                              {
                                "location_id": "sloc_01J9Z3ZW79FPF91YMZPMSV44AZ",
                                "stock_locations": [
                                  {
                                    "id": "sloc_01J9Z3ZW79FPF91YMZPMSV44AZ",
                                    "name": "Digital Product Warehouse",
                                    "sales_channels": [
                                      {
                                        "id": "sc_01J9YXNSVQXAT8002GJY8P1NE1",
                                        "name": "derftuned.com"
                                      }
                                    ]
                                  }
                                ],
                                "stocked_quantity": -274300000,
                                "reserved_quantity": 100000,
                                "raw_stocked_quantity": {
                                  "value": "-274300000",
                                  "precision": 20
                                },
                                "raw_reserved_quantity": {
                                  "value": "100000",
                                  "precision": 20
                                }
                              }
                            ],
                            "requires_shipping": true
                          },
                          "variant_id": "variant_01K8P58KCHRX1P7EW736WFEPC5",
                          "inventory_item_id": "iitem_01K8P58KEDNQ7VMVHK0A6JA89P",
                          "required_quantity": 100000
                        }
                      ],
                      "manage_inventory": true
                    },
                    "metadata": {},
                    "quantity": 10,
                    "subtitle": "DerfTuned Motorsports Digital Art - 022",
                    "subtotal": 25,
                    "raw_total": {
                      "value": "25",
                      "precision": 20
                    },
                    "tax_lines": [
                      {
                        "id": "calitxl_01K8SHRF6DZ22H83RG9TGR0DDS",
                        "code": "",
                        "rate": 0,
                        "total": 0,
                        "item_id": "cali_01K8SHMS4YQ240XW7FA1WXRDRM",
                        "metadata": null,
                        "subtotal": 0,
                        "raw_total": {
                          "value": "0",
                          "precision": 20
                        },
                        "created_at": "2025-10-30T03:14:39.965Z",
                        "deleted_at": null,
                        "updated_at": "2025-10-30T03:14:39.965Z",
                        "description": "Sales Tax",
                        "provider_id": "system",
                        "tax_rate_id": "txr_01JD8YWNP1YHCC99D8177JMFCM",
                        "raw_subtotal": {
                          "value": "0",
                          "precision": 20
                        }
                      }
                    ],
                    "tax_total": 0,
                    "thumbnail": "https://ppiturtnonwzgyldzcyq.supabase.co/storage/v1/object/public/derftuned/DTMS-DA-022-01-min-01K8P5TPR1Z162GFNS5QW6M7YV.jpg",
                    "created_at": "2025-10-30T03:12:39.071Z",
                    "deleted_at": null,
                    "product_id": "prod_01K8P58K429BGTAWBGP7CQ72QK",
                    "unit_price": 2.5,
                    "updated_at": "2025-10-30T03:13:16.918Z",
                    "variant_id": "variant_01K8P58KCHRX1P7EW736WFEPC5",
                    "adjustments": [],
                    "is_giftcard": false,
                    "variant_sku": null,
                    "product_type": "Digital",
                    "raw_subtotal": {
                      "value": "25",
                      "precision": 20
                    },
                    "product_title": "DerfTuned Motorsports Digital Art - 022",
                    "raw_tax_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "variant_title": "DerfTuned Motorsports Digital Art - 022",
                    "discount_total": 0,
                    "original_total": 25,
                    "product_handle": "dtms-da-022",
                    "raw_unit_price": {
                      "value": "2.5",
                      "precision": 20
                    },
                    "is_custom_price": false,
                    "is_discountable": true,
                    "product_type_id": "ptyp_01J9Z8YWEM999X73F8QW836WWT",
                    "variant_barcode": null,
                    "is_tax_inclusive": false,
                    "product_subtitle": "DTMS-DA-022",
                    "discount_subtotal": 0,
                    "original_subtotal": 25,
                    "requires_shipping": true,
                    "discount_tax_total": 0,
                    "original_tax_total": 0,
                    "product_collection": "Digital Art",
                    "raw_discount_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_original_total": {
                      "value": "25",
                      "precision": 20
                    },
                    "product_description": "**Bonus**\nBuy 1 get 10 FREE\nBuy 10 get 250 FREE\nBuy 20 get 750 FREE\nBuy 40 get 2000 FREE\n\nDigital Art Build Details***:\n- K20Z3 Motor\n- K20Z3 6 Speed Transmission w/ WaveTrac LSD\n- AWD Element transmission\n- Competition Clutch twin disk\n- Steel oil pan w/ oil drain bung\n- Vented Valve Cover w/ catch can setup\n- SBS Ported RBC manifold \n- 80 mm Throttle body\n- KTuned Fuel rail, lines and fuel regulator\n- KTuned Billet water necks\n- KTuned Billet shifter box and cables\n- Complete custom turbo kit\n- KLM Sidewinder manifold\n- Precision 6266 turbo\n- Precision Wastegate\n- Precision Blow-off valve\n- Aluminum intercooler piping\n- Same side K series intercooler\n- 3\" Stainless downpipe\n- 2\" Open dump tube\n- KTuned turbo blanket\n- Oil feed and return lines\n\n***Build is of the AWD K-Swap Turbo not entire car",
                    "compare_at_unit_price": null,
                    "raw_discount_subtotal": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_original_subtotal": {
                      "value": "25",
                      "precision": 20
                    },
                    "variant_option_values": null,
                    "raw_discount_tax_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_original_tax_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_compare_at_unit_price": null
                  }
                ],
                "total": 25,
                "region": {
                  "id": "reg_01J9Z3M2AXKMPG9Z76V1VTWPQ9",
                  "name": "North America",
                  "metadata": null,
                  "created_at": "2024-10-12T00:56:25.734Z",
                  "deleted_at": null,
                  "updated_at": "2024-11-22T03:55:00.216Z",
                  "currency_code": "usd",
                  "automatic_taxes": true
                },
                "customer": {
                  "id": "cus_01JHRG78ZR9AQ5TF9PN50QMN0A",
                  "email": "customer@hotmail.com",
                  "phone": null,
                  "metadata": null,
                  "last_name": null,
                  "created_at": "2025-01-16T21:27:31.576Z",
                  "created_by": null,
                  "deleted_at": null,
                  "first_name": null,
                  "updated_at": "2025-01-16T21:27:31.576Z",
                  "has_account": false,
                  "company_name": null
                },
                "metadata": null,
                "subtotal": 25,
                "raw_total": {
                  "value": "25",
                  "precision": 20
                },
                "region_id": "reg_01J9Z3M2AXKMPG9Z76V1VTWPQ9",
                "tax_total": 0,
                "created_at": "2025-10-30T03:12:38.594Z",
                "item_total": 25,
                "promotions": [],
                "updated_at": "2025-10-30T03:15:49.462Z",
                "customer_id": "cus_01JHRG78ZR9AQ5TF9PN50QMN0A",
                "completed_at": "2025-10-30T03:15:49.430Z",
                "credit_lines": [],
                "raw_subtotal": {
                  "value": "25",
                  "precision": 20
                },
                "currency_code": "usd",
                "item_subtotal": 25,
                "raw_tax_total": {
                  "value": "0",
                  "precision": 20
                },
                "discount_total": 0,
                "item_tax_total": 0,
                "original_total": 25,
                "raw_item_total": {
                  "value": "25",
                  "precision": 20
                },
                "shipping_total": 0,
                "billing_address": {
                  "id": "caaddr_01K8SHREVE7VBEJD6VVK71PSY7",
                  "city": "Toronto",
                  "phone": "1xxxxxxxxxx",
                  "company": "",
                  "metadata": {
                    "twitter": "",
                    "instagram": "xxx_xxx"
                  },
                  "province": "ON",
                  "address_1": "xxxxxxxxx",
                  "address_2": "",
                  "last_name": "Customer",
                  "created_at": "2025-10-30T03:14:39.599Z",
                  "deleted_at": null,
                  "first_name": "Customer",
                  "updated_at": "2025-10-30T03:14:39.599Z",
                  "customer_id": null,
                  "postal_code": "Xxx",
                  "country_code": "ca"
                },
                "sales_channel_id": "sc_01J9YXNSVQXAT8002GJY8P1NE1",
                "shipping_address": {
                  "id": "caaddr_01K8SHREVFNHNNRYSHD7FBNT59",
                  "city": "Toronto",
                  "phone": "1xxxxxxxxxx",
                  "company": "",
                  "metadata": {
                    "twitter": "",
                    "instagram": "xxx_xxx"
                  },
                  "province": "ON",
                  "address_1": "xxxxxxxxxxx",
                  "address_2": "",
                  "last_name": "Customer",
                  "created_at": "2025-10-30T03:14:39.599Z",
                  "deleted_at": null,
                  "first_name": "Customer",
                  "updated_at": "2025-10-30T03:14:39.599Z",
                  "customer_id": null,
                  "postal_code": "xxx",
                  "country_code": "ca"
                },
                "shipping_methods": [
                  {
                    "id": "casm_01K8SHRJS9Y006YCZZQCEA3NCK",
                    "data": {},
                    "name": "Digital Delivery",
                    "total": 0,
                    "amount": 0,
                    "cart_id": "cart_01K8SHMRP2CJ4JA6K1JK8K5X85",
                    "metadata": null,
                    "subtotal": 0,
                    "raw_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "tax_lines": [
                      {
                        "id": "casmtxl_01K8SHRKF4DC8WX48AQWNMT03M",
                        "code": "",
                        "rate": 0,
                        "total": 0,
                        "metadata": null,
                        "subtotal": 0,
                        "raw_total": {
                          "value": "0",
                          "precision": 20
                        },
                        "created_at": "2025-10-30T03:14:44.324Z",
                        "deleted_at": null,
                        "updated_at": "2025-10-30T03:14:44.324Z",
                        "description": "Sales Tax",
                        "provider_id": "system",
                        "tax_rate_id": "txr_01JD8YWNP1YHCC99D8177JMFCM",
                        "raw_subtotal": {
                          "value": "0",
                          "precision": 20
                        },
                        "shipping_method_id": "casm_01K8SHRJS9Y006YCZZQCEA3NCK"
                      }
                    ],
                    "tax_total": 0,
                    "created_at": "2025-10-30T03:14:43.625Z",
                    "deleted_at": null,
                    "raw_amount": {
                      "value": "0",
                      "precision": 20
                    },
                    "updated_at": "2025-10-30T03:14:43.625Z",
                    "adjustments": [],
                    "description": null,
                    "raw_subtotal": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_tax_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "discount_total": 0,
                    "original_total": 0,
                    "is_tax_inclusive": false,
                    "discount_subtotal": 0,
                    "original_subtotal": 0,
                    "discount_tax_total": 0,
                    "original_tax_total": 0,
                    "raw_discount_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_original_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "shipping_option_id": "so_01JA0XHS785FHGAMQ3H91EVSCF",
                    "raw_discount_subtotal": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_original_subtotal": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_discount_tax_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_original_tax_total": {
                      "value": "0",
                      "precision": 20
                    }
                  }
                ],
                "raw_item_subtotal": {
                  "value": "25",
                  "precision": 20
                },
                "shipping_subtotal": 0,
                "discount_tax_total": 0,
                "original_tax_total": 0,
                "payment_collection": {
                  "id": "pay_col_01K8SHN3AW4X2FVYZF64BMFE19",
                  "amount": 25,
                  "status": "completed",
                  "metadata": null,
                  "created_at": "2025-10-30T03:12:49.500Z",
                  "deleted_at": null,
                  "raw_amount": {
                    "value": "25",
                    "precision": 20
                  },
                  "updated_at": "2025-10-30T03:15:54.335Z",
                  "completed_at": "2025-10-30T03:15:54.316Z",
                  "currency_code": "usd",
                  "captured_amount": 25,
                  "refunded_amount": 0,
                  "payment_sessions": [
                    {
                      "id": "payses_01K8SHNYWA9NM89JSSZZQ5J66K",
                      "data": {
                        "id": "pi_xxxxxxxxxxxxxxxxxxxxxxxx",
                        "amount": 2500,
                        "object": "payment_intent",
                        "review": null,
                        "source": null,
                        "status": "succeeded",
                        "created": 1761793997,
                        "invoice": null,
                        "currency": "usd",
                        "customer": null,
                        "livemode": true,
                        "metadata": {
                          "session_id": "payses_01K8SHNYWA9NM89JSSZZQ5J66K"
                        },
                        "shipping": null,
                        "processing": null,
                        "application": null,
                        "canceled_at": null,
                        "description": null,
                        "next_action": null,
                        "on_behalf_of": null,
                        "client_secret": "pi_xxxxxxxx_secret_xxxxxxx",
                        "latest_charge": "ch_3SNmIbK6QjZA3FWk0KTrQD4r",
                        "receipt_email": null,
                        "transfer_data": null,
                        "amount_details": {
                          "tip": {}
                        },
                        "capture_method": "automatic",
                        "payment_method": "pm_1SNmKOK6QjZA3FWkztPx18Zj",
                        "transfer_group": null,
                        "amount_received": 2500,
                        "amount_capturable": 0,
                        "last_payment_error": null,
                        "setup_future_usage": null,
                        "cancellation_reason": null,
                        "confirmation_method": "automatic",
                        "payment_method_types": [
                          "card",
                          "link",
                          "cashapp",
                          "amazon_pay"
                        ],
                        "statement_descriptor": null,
                        "application_fee_amount": null,
                        "payment_method_options": {
                          "card": {
                            "network": null,
                            "installments": null,
                            "mandate_options": null,
                            "request_three_d_secure": "automatic"
                          },
                          "link": {
                            "persistent_token": null
                          },
                          "cashapp": {},
                          "amazon_pay": {
                            "express_checkout_element_session_id": null
                          }
                        },
                        "automatic_payment_methods": {
                          "enabled": true,
                          "allow_redirects": "always"
                        },
                        "statement_descriptor_suffix": null,
                        "excluded_payment_method_types": null,
                        "payment_method_configuration_details": {
                          "id": "pmc_1PejDyK6QjZA3FWkUVt0YiK0",
                          "parent": null
                        }
                      },
                      "amount": 25,
                      "status": "authorized",
                      "context": {},
                      "metadata": {},
                      "created_at": "2025-10-30T03:13:17.706Z",
                      "deleted_at": null,
                      "raw_amount": {
                        "value": "25",
                        "precision": 20
                      },
                      "updated_at": "2025-10-30T03:15:49.675Z",
                      "provider_id": "pp_stripe_stripe",
                      "authorized_at": "2025-10-30T03:15:49.663Z",
                      "currency_code": "usd",
                      "payment_collection_id": "pay_col_01K8SHN3AW4X2FVYZF64BMFE19"
                    }
                  ],
                  "authorized_amount": 25,
                  "raw_captured_amount": {
                    "value": "25",
                    "precision": 20
                  },
                  "raw_refunded_amount": {
                    "value": "0",
                    "precision": 20
                  },
                  "raw_authorized_amount": {
                    "value": "25",
                    "precision": 20
                  }
                },
                "raw_discount_total": {
                  "value": "0",
                  "precision": 20
                },
                "raw_item_tax_total": {
                  "value": "0",
                  "precision": 20
                },
                "raw_original_total": {
                  "value": "25",
                  "precision": 20
                },
                "raw_shipping_total": {
                  "value": "0",
                  "precision": 20
                },
                "shipping_tax_total": 0,
                "original_item_total": 25,
                "raw_shipping_subtotal": {
                  "value": "0",
                  "precision": 20
                },
                "original_item_subtotal": 25,
                "raw_discount_tax_total": {
                  "value": "0",
                  "precision": 20
                },
                "raw_original_tax_total": {
                  "value": "0",
                  "precision": 20
                },
                "raw_shipping_tax_total": {
                  "value": "0",
                  "precision": 20
                },
                "original_item_tax_total": 0,
                "original_shipping_total": 0,
                "raw_original_item_total": {
                  "value": "25",
                  "precision": 20
                },
                "original_shipping_subtotal": 0,
                "raw_original_item_subtotal": {
                  "value": "25",
                  "precision": 20
                },
                "original_shipping_tax_total": 0,
                "raw_original_item_tax_total": {
                  "value": "0",
                  "precision": 20
                },
                "raw_original_shipping_total": {
                  "value": "0",
                  "precision": 20
                },
                "raw_original_shipping_subtotal": {
                  "value": "0",
                  "precision": 20
                },
                "raw_original_shipping_tax_total": {
                  "value": "0",
                  "precision": 20
                }
              }
            },
            "compensateInput": {
              "data": {
                "id": "cart_01K8SHMRP2CJ4JA6K1JK8K5X85",
                "email": "customer@hotmail.com",
                "items": [
                  {
                    "id": "cali_01K8SHMS4YQ240XW7FA1WXRDRM",
                    "title": "DerfTuned Motorsports Digital Art - 022",
                    "total": 25,
                    "cart_id": "cart_01K8SHMRP2CJ4JA6K1JK8K5X85",
                    "variant": {
                      "id": "variant_01K8P58KCHRX1P7EW736WFEPC5",
                      "product": {
                        "id": "prod_01K8P58K429BGTAWBGP7CQ72QK",
                        "is_giftcard": false,
                        "shipping_profile": {
                          "id": "sp_01J9Z46H06YD75WG5NRN6D676R"
                        }
                      },
                      "product_id": "prod_01K8P58K429BGTAWBGP7CQ72QK",
                      "allow_backorder": true,
                      "inventory_items": [
                        {
                          "inventory": {
                            "id": "iitem_01K8P58KEDNQ7VMVHK0A6JA89P",
                            "location_levels": [
                              {
                                "location_id": "sloc_01J9Z3ZW79FPF91YMZPMSV44AZ",
                                "stock_locations": [
                                  {
                                    "id": "sloc_01J9Z3ZW79FPF91YMZPMSV44AZ",
                                    "name": "Digital Product Warehouse",
                                    "sales_channels": [
                                      {
                                        "id": "sc_01J9YXNSVQXAT8002GJY8P1NE1",
                                        "name": "derftuned.com"
                                      }
                                    ]
                                  }
                                ],
                                "stocked_quantity": -274300000,
                                "reserved_quantity": 100000,
                                "raw_stocked_quantity": {
                                  "value": "-274300000",
                                  "precision": 20
                                },
                                "raw_reserved_quantity": {
                                  "value": "100000",
                                  "precision": 20
                                }
                              }
                            ],
                            "requires_shipping": true
                          },
                          "variant_id": "variant_01K8P58KCHRX1P7EW736WFEPC5",
                          "inventory_item_id": "iitem_01K8P58KEDNQ7VMVHK0A6JA89P",
                          "required_quantity": 100000
                        }
                      ],
                      "manage_inventory": true
                    },
                    "metadata": {},
                    "quantity": 10,
                    "subtitle": "DerfTuned Motorsports Digital Art - 022",
                    "subtotal": 25,
                    "raw_total": {
                      "value": "25",
                      "precision": 20
                    },
                    "tax_lines": [
                      {
                        "id": "calitxl_01K8SHRF6DZ22H83RG9TGR0DDS",
                        "code": "",
                        "rate": 0,
                        "total": 0,
                        "item_id": "cali_01K8SHMS4YQ240XW7FA1WXRDRM",
                        "metadata": null,
                        "subtotal": 0,
                        "raw_total": {
                          "value": "0",
                          "precision": 20
                        },
                        "created_at": "2025-10-30T03:14:39.965Z",
                        "deleted_at": null,
                        "updated_at": "2025-10-30T03:14:39.965Z",
                        "description": "Sales Tax",
                        "provider_id": "system",
                        "tax_rate_id": "txr_01JD8YWNP1YHCC99D8177JMFCM",
                        "raw_subtotal": {
                          "value": "0",
                          "precision": 20
                        }
                      }
                    ],
                    "tax_total": 0,
                    "thumbnail": "https://ppiturtnonwzgyldzcyq.supabase.co/storage/v1/object/public/derftuned/DTMS-DA-022-01-min-01K8P5TPR1Z162GFNS5QW6M7YV.jpg",
                    "created_at": "2025-10-30T03:12:39.071Z",
                    "deleted_at": null,
                    "product_id": "prod_01K8P58K429BGTAWBGP7CQ72QK",
                    "unit_price": 2.5,
                    "updated_at": "2025-10-30T03:13:16.918Z",
                    "variant_id": "variant_01K8P58KCHRX1P7EW736WFEPC5",
                    "adjustments": [],
                    "is_giftcard": false,
                    "variant_sku": null,
                    "product_type": "Digital",
                    "raw_subtotal": {
                      "value": "25",
                      "precision": 20
                    },
                    "product_title": "DerfTuned Motorsports Digital Art - 022",
                    "raw_tax_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "variant_title": "DerfTuned Motorsports Digital Art - 022",
                    "discount_total": 0,
                    "original_total": 25,
                    "product_handle": "dtms-da-022",
                    "raw_unit_price": {
                      "value": "2.5",
                      "precision": 20
                    },
                    "is_custom_price": false,
                    "is_discountable": true,
                    "product_type_id": "ptyp_01J9Z8YWEM999X73F8QW836WWT",
                    "variant_barcode": null,
                    "is_tax_inclusive": false,
                    "product_subtitle": "DTMS-DA-022",
                    "discount_subtotal": 0,
                    "original_subtotal": 25,
                    "requires_shipping": true,
                    "discount_tax_total": 0,
                    "original_tax_total": 0,
                    "product_collection": "Digital Art",
                    "raw_discount_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_original_total": {
                      "value": "25",
                      "precision": 20
                    },
                    "product_description": "**Bonus**\nBuy 1 get 10 FREE\nBuy 10 get 250 FREE\nBuy 20 get 750 FREE\nBuy 40 get 2000 FREE\n\nDigital Art Build Details***:\n- K20Z3 Motor\n- K20Z3 6 Speed Transmission w/ WaveTrac LSD\n- AWD Element transmission\n- Competition Clutch twin disk\n- Steel oil pan w/ oil drain bung\n- Vented Valve Cover w/ catch can setup\n- SBS Ported RBC manifold \n- 80 mm Throttle body\n- KTuned Fuel rail, lines and fuel regulator\n- KTuned Billet water necks\n- KTuned Billet shifter box and cables\n- Complete custom turbo kit\n- KLM Sidewinder manifold\n- Precision 6266 turbo\n- Precision Wastegate\n- Precision Blow-off valve\n- Aluminum intercooler piping\n- Same side K series intercooler\n- 3\" Stainless downpipe\n- 2\" Open dump tube\n- KTuned turbo blanket\n- Oil feed and return lines\n\n***Build is of the AWD K-Swap Turbo not entire car",
                    "compare_at_unit_price": null,
                    "raw_discount_subtotal": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_original_subtotal": {
                      "value": "25",
                      "precision": 20
                    },
                    "variant_option_values": null,
                    "raw_discount_tax_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_original_tax_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_compare_at_unit_price": null
                  }
                ],
                "total": 25,
                "region": {
                  "id": "reg_01J9Z3M2AXKMPG9Z76V1VTWPQ9",
                  "name": "North America",
                  "metadata": null,
                  "created_at": "2024-10-12T00:56:25.734Z",
                  "deleted_at": null,
                  "updated_at": "2024-11-22T03:55:00.216Z",
                  "currency_code": "usd",
                  "automatic_taxes": true
                },
                "customer": {
                  "id": "cus_01JHRG78ZR9AQ5TF9PN50QMN0A",
                  "email": "customer@hotmail.com",
                  "phone": null,
                  "metadata": null,
                  "last_name": null,
                  "created_at": "2025-01-16T21:27:31.576Z",
                  "created_by": null,
                  "deleted_at": null,
                  "first_name": null,
                  "updated_at": "2025-01-16T21:27:31.576Z",
                  "has_account": false,
                  "company_name": null
                },
                "metadata": null,
                "subtotal": 25,
                "raw_total": {
                  "value": "25",
                  "precision": 20
                },
                "region_id": "reg_01J9Z3M2AXKMPG9Z76V1VTWPQ9",
                "tax_total": 0,
                "created_at": "2025-10-30T03:12:38.594Z",
                "item_total": 25,
                "promotions": [],
                "updated_at": "2025-10-30T03:15:49.462Z",
                "customer_id": "cus_01JHRG78ZR9AQ5TF9PN50QMN0A",
                "completed_at": "2025-10-30T03:15:49.430Z",
                "credit_lines": [],
                "raw_subtotal": {
                  "value": "25",
                  "precision": 20
                },
                "currency_code": "usd",
                "item_subtotal": 25,
                "raw_tax_total": {
                  "value": "0",
                  "precision": 20
                },
                "discount_total": 0,
                "item_tax_total": 0,
                "original_total": 25,
                "raw_item_total": {
                  "value": "25",
                  "precision": 20
                },
                "shipping_total": 0,
                "billing_address": {
                  "id": "caaddr_01K8SHREVE7VBEJD6VVK71PSY7",
                  "city": "Toronto",
                  "phone": "1xxxxxxxxxx",
                  "company": "",
                  "metadata": {
                    "twitter": "",
                    "instagram": "xxx_xxx"
                  },
                  "province": "ON",
                  "address_1": "xxxxxxx",
                  "address_2": "",
                  "last_name": "Customer",
                  "created_at": "2025-10-30T03:14:39.599Z",
                  "deleted_at": null,
                  "first_name": "Customer",
                  "updated_at": "2025-10-30T03:14:39.599Z",
                  "customer_id": null,
                  "postal_code": "xxxx",
                  "country_code": "ca"
                },
                "sales_channel_id": "sc_01J9YXNSVQXAT8002GJY8P1NE1",
                "shipping_address": {
                  "id": "caaddr_01K8SHREVFNHNNRYSHD7FBNT59",
                  "city": "Toronto",
                  "phone": "1xxxxxxxxxx",
                  "company": "",
                  "metadata": {
                    "twitter": "",
                    "instagram": "xxx_xxx"
                  },
                  "province": "ON",
                  "address_1": "xxxxxx",
                  "address_2": "",
                  "last_name": "Customer",
                  "created_at": "2025-10-30T03:14:39.599Z",
                  "deleted_at": null,
                  "first_name": "Customer",
                  "updated_at": "2025-10-30T03:14:39.599Z",
                  "customer_id": null,
                  "postal_code": "xxxx",
                  "country_code": "ca"
                },
                "shipping_methods": [
                  {
                    "id": "casm_01K8SHRJS9Y006YCZZQCEA3NCK",
                    "data": {},
                    "name": "Digital Delivery",
                    "total": 0,
                    "amount": 0,
                    "cart_id": "cart_01K8SHMRP2CJ4JA6K1JK8K5X85",
                    "metadata": null,
                    "subtotal": 0,
                    "raw_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "tax_lines": [
                      {
                        "id": "casmtxl_01K8SHRKF4DC8WX48AQWNMT03M",
                        "code": "",
                        "rate": 0,
                        "total": 0,
                        "metadata": null,
                        "subtotal": 0,
                        "raw_total": {
                          "value": "0",
                          "precision": 20
                        },
                        "created_at": "2025-10-30T03:14:44.324Z",
                        "deleted_at": null,
                        "updated_at": "2025-10-30T03:14:44.324Z",
                        "description": "Sales Tax",
                        "provider_id": "system",
                        "tax_rate_id": "txr_01JD8YWNP1YHCC99D8177JMFCM",
                        "raw_subtotal": {
                          "value": "0",
                          "precision": 20
                        },
                        "shipping_method_id": "casm_01K8SHRJS9Y006YCZZQCEA3NCK"
                      }
                    ],
                    "tax_total": 0,
                    "created_at": "2025-10-30T03:14:43.625Z",
                    "deleted_at": null,
                    "raw_amount": {
                      "value": "0",
                      "precision": 20
                    },
                    "updated_at": "2025-10-30T03:14:43.625Z",
                    "adjustments": [],
                    "description": null,
                    "raw_subtotal": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_tax_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "discount_total": 0,
                    "original_total": 0,
                    "is_tax_inclusive": false,
                    "discount_subtotal": 0,
                    "original_subtotal": 0,
                    "discount_tax_total": 0,
                    "original_tax_total": 0,
                    "raw_discount_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_original_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "shipping_option_id": "so_01JA0XHS785FHGAMQ3H91EVSCF",
                    "raw_discount_subtotal": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_original_subtotal": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_discount_tax_total": {
                      "value": "0",
                      "precision": 20
                    },
                    "raw_original_tax_total": {
                      "value": "0",
                      "precision": 20
                    }
                  }
                ],
                "raw_item_subtotal": {
                  "value": "25",
                  "precision": 20
                },
                "shipping_subtotal": 0,
                "discount_tax_total": 0,
                "original_tax_total": 0,
                "payment_collection": {
                  "id": "pay_col_01K8SHN3AW4X2FVYZF64BMFE19",
                  "amount": 25,
                  "status": "completed",
                  "metadata": null,
                  "created_at": "2025-10-30T03:12:49.500Z",
                  "deleted_at": null,
                  "raw_amount": {
                    "value": "25",
                    "precision": 20
                  },
                  "updated_at": "2025-10-30T03:15:54.335Z",
                  "completed_at": "2025-10-30T03:15:54.316Z",
                  "currency_code": "usd",
                  "captured_amount": 25,
                  "refunded_amount": 0,
                  "payment_sessions": [
                    {
                      "id": "payses_01K8SHNYWA9NM89JSSZZQ5J66K",
                      "data": {
                        "id": "pi_xxxxxxxxxxxxxxxxxx",
                        "amount": 2500,
                        "object": "payment_intent",
                        "review": null,
                        "source": null,
                        "status": "succeeded",
                        "created": 1761793997,
                        "invoice": null,
                        "currency": "usd",
                        "customer": null,
                        "livemode": true,
                        "metadata": {
                          "session_id": "payses_01K8SHNYWA9NM89JSSZZQ5J66K"
                        },
                        "shipping": null,
                        "processing": null,
                        "application": null,
                        "canceled_at": null,
                        "description": null,
                        "next_action": null,
                        "on_behalf_of": null,
                        "client_secret": "pi_xxxxxxxxxxxxx_secret_xxxxxxx",
                        "latest_charge": "ch_3SNmIbK6QjZA3FWk0KTrQD4r",
                        "receipt_email": null,
                        "transfer_data": null,
                        "amount_details": {
                          "tip": {}
                        },
                        "capture_method": "automatic",
                        "payment_method": "pm_1SNmKOK6QjZA3FWkztPx18Zj",
                        "transfer_group": null,
                        "amount_received": 2500,
                        "amount_capturable": 0,
                        "last_payment_error": null,
                        "setup_future_usage": null,
                        "cancellation_reason": null,
                        "confirmation_method": "automatic",
                        "payment_method_types": [
                          "card",
                          "link",
                          "cashapp",
                          "amazon_pay"
                        ],
                        "statement_descriptor": null,
                        "application_fee_amount": null,
                        "payment_method_options": {
                          "card": {
                            "network": null,
                            "installments": null,
                            "mandate_options": null,
                            "request_three_d_secure": "automatic"
                          },
                          "link": {
                            "persistent_token": null
                          },
                          "cashapp": {},
                          "amazon_pay": {
                            "express_checkout_element_session_id": null
                          }
                        },
                        "automatic_payment_methods": {
                          "enabled": true,
                          "allow_redirects": "always"
                        },
                        "statement_descriptor_suffix": null,
                        "excluded_payment_method_types": null,
                        "payment_method_configuration_details": {
                          "id": "pmc_1PejDyK6QjZA3FWkUVt0YiK0",
                          "parent": null
                        }
                      },
                      "amount": 25,
                      "status": "authorized",
                      "context": {},
                      "metadata": {},
                      "created_at": "2025-10-30T03:13:17.706Z",
                      "deleted_at": null,
                      "raw_amount": {
                        "value": "25",
                        "precision": 20
                      },
                      "updated_at": "2025-10-30T03:15:49.675Z",
                      "provider_id": "pp_stripe_stripe",
                      "authorized_at": "2025-10-30T03:15:49.663Z",
                      "currency_code": "usd",
                      "payment_collection_id": "pay_col_01K8SHN3AW4X2FVYZF64BMFE19"
                    }
                  ],
                  "authorized_amount": 25,
                  "raw_captured_amount": {
                    "value": "25",
                    "precision": 20
                  },
                  "raw_refunded_amount": {
                    "value": "0",
                    "precision": 20
                  },
                  "raw_authorized_amount": {
                    "value": "25",
                    "precision": 20
                  }
                },
                "raw_discount_total": {
                  "value": "0",
                  "precision": 20
                },
                "raw_item_tax_total": {
                  "value": "0",
                  "precision": 20
                },
                "raw_original_total": {
                  "value": "25",
                  "precision": 20
                },
                "raw_shipping_total": {
                  "value": "0",
                  "precision": 20
                },
                "shipping_tax_total": 0,
                "original_item_total": 25,
                "raw_shipping_subtotal": {
                  "value": "0",
                  "precision": 20
                },
                "original_item_subtotal": 25,
                "raw_discount_tax_total": {
                  "value": "0",
                  "precision": 20
                },
                "raw_original_tax_total": {
                  "value": "0",
                  "precision": 20
                },
                "raw_shipping_tax_total": {
                  "value": "0",
                  "precision": 20
                },
                "original_item_tax_total": 0,
                "original_shipping_total": 0,
                "raw_original_item_total": {
                  "value": "25",
                  "precision": 20
                },
                "original_shipping_subtotal": 0,
                "raw_original_item_subtotal": {
                  "value": "25",
                  "precision": 20
                },
                "original_shipping_tax_total": 0,
                "raw_original_item_tax_total": {
                  "value": "0",
                  "precision": 20
                },
                "raw_original_shipping_total": {
                  "value": "0",
                  "precision": 20
                },
                "raw_original_shipping_subtotal": {
                  "value": "0",
                  "precision": 20
                },
                "raw_original_shipping_tax_total": {
                  "value": "0",
                  "precision": 20
                }
              }
            }
          }
        },
        "acquire-lock-step": {
          "__type": "Symbol(WorkflowWorkflowData)",
          "output": {
            "__type": "Symbol(WorkflowStepResponse)",
            "compensateInput": {
              "keys": [
                "cart_01K8SHMRP2CJ4JA6K1JK8K5X85"
              ]
            }
          }
        },
        "release-lock-step": {
          "__type": "Symbol(WorkflowWorkflowData)",
          "output": {
            "__type": "Symbol(WorkflowStepResponse)",
            "output": true,
            "compensateInput": true
          }
        },
        "use-query-graph-step": {
          "__type": "Symbol(WorkflowWorkflowData)",
          "output": {
            "__type": "Symbol(WorkflowStepResponse)",
            "output": {
              "data": {
                "cart_id": "cart_01K8SHMRP2CJ4JA6K1JK8K5X85",
                "order_id": "order_01K8SHTJXCPKXB1DP4NXKJ7VZA"
              }
            },
            "compensateInput": {
              "data": {
                "cart_id": "cart_01K8SHMRP2CJ4JA6K1JK8K5X85",
                "order_id": "order_01K8SHTJXCPKXB1DP4NXKJ7VZA"
              }
            }
          }
        },
        "validate-cart-payments": {
          "__type": "Symbol(WorkflowWorkflowData)",
          "output": {
            "__type": "Symbol(WorkflowStepResponse)",
            "output": [
              {
                "id": "payses_01K8SHNYWA9NM89JSSZZQ5J66K",
                "data": {
                  "id": "pi_xxxxxxxxxxxxxxxxxx",
                  "amount": 2500,
                  "object": "payment_intent",
                  "review": null,
                  "source": null,
                  "status": "succeeded",
                  "created": 1761793997,
                  "invoice": null,
                  "currency": "usd",
                  "customer": null,
                  "livemode": true,
                  "metadata": {
                    "session_id": "payses_01K8SHNYWA9NM89JSSZZQ5J66K"
                  },
                  "shipping": null,
                  "processing": null,
                  "application": null,
                  "canceled_at": null,
                  "description": null,
                  "next_action": null,
                  "on_behalf_of": null,
                  "client_secret": "pi_xxxxxxxxxxxxxxxxxxx_secret_xxxxxxxxxxxxxxxxxxx",
                  "latest_charge": "ch_3SNmIbK6QjZA3FWk0KTrQD4r",
                  "receipt_email": null,
                  "transfer_data": null,
                  "amount_details": {
                    "tip": {}
                  },
                  "capture_method": "automatic",
                  "payment_method": "pm_1SNmKOK6QjZA3FWkztPx18Zj",
                  "transfer_group": null,
                  "amount_received": 2500,
                  "amount_capturable": 0,
                  "last_payment_error": null,
                  "setup_future_usage": null,
                  "cancellation_reason": null,
                  "confirmation_method": "automatic",
                  "payment_method_types": [
                    "card",
                    "link",
                    "cashapp",
                    "amazon_pay"
                  ],
                  "statement_descriptor": null,
                  "application_fee_amount": null,
                  "payment_method_options": {
                    "card": {
                      "network": null,
                      "installments": null,
                      "mandate_options": null,
                      "request_three_d_secure": "automatic"
                    },
                    "link": {
                      "persistent_token": null
                    },
                    "cashapp": {},
                    "amazon_pay": {
                      "express_checkout_element_session_id": null
                    }
                  },
                  "automatic_payment_methods": {
                    "enabled": true,
                    "allow_redirects": "always"
                  },
                  "statement_descriptor_suffix": null,
                  "excluded_payment_method_types": null,
                  "payment_method_configuration_details": {
                    "id": "pmc_1PejDyK6QjZA3FWkUVt0YiK0",
                    "parent": null
                  }
                },
                "amount": 25,
                "status": "authorized",
                "context": {},
                "metadata": {},
                "created_at": "2025-10-30T03:13:17.706Z",
                "deleted_at": null,
                "raw_amount": {
                  "value": "25",
                  "precision": 20
                },
                "updated_at": "2025-10-30T03:15:49.675Z",
                "provider_id": "pp_stripe_stripe",
                "authorized_at": "2025-10-30T03:15:49.663Z",
                "currency_code": "usd",
                "payment_collection_id": "pay_col_01K8SHN3AW4X2FVYZF64BMFE19"
              }
            ],
            "compensateInput": [
              {
                "id": "payses_01K8SHNYWA9NM89JSSZZQ5J66K",
                "data": {
                  "id": "pi_xxxxxxxxxxxxxxxxxxxxxxx",
                  "amount": 2500,
                  "object": "payment_intent",
                  "review": null,
                  "source": null,
                  "status": "succeeded",
                  "created": 1761793997,
                  "invoice": null,
                  "currency": "usd",
                  "customer": null,
                  "livemode": true,
                  "metadata": {
                    "session_id": "payses_01K8SHNYWA9NM89JSSZZQ5J66K"
                  },
                  "shipping": null,
                  "processing": null,
                  "application": null,
                  "canceled_at": null,
                  "description": null,
                  "next_action": null,
                  "on_behalf_of": null,
                  "client_secret": "pi_xxxxxxxxxxxxxxxxxx_secret_xxxxxxxxxxxxxxxxxxx",
                  "latest_charge": "ch_3SNmIbK6QjZA3FWk0KTrQD4r",
                  "receipt_email": null,
                  "transfer_data": null,
                  "amount_details": {
                    "tip": {}
                  },
                  "capture_method": "automatic",
                  "payment_method": "pm_1SNmKOK6QjZA3FWkztPx18Zj",
                  "transfer_group": null,
                  "amount_received": 2500,
                  "amount_capturable": 0,
                  "last_payment_error": null,
                  "setup_future_usage": null,
                  "cancellation_reason": null,
                  "confirmation_method": "automatic",
                  "payment_method_types": [
                    "card",
                    "link",
                    "cashapp",
                    "amazon_pay"
                  ],
                  "statement_descriptor": null,
                  "application_fee_amount": null,
                  "payment_method_options": {
                    "card": {
                      "network": null,
                      "installments": null,
                      "mandate_options": null,
                      "request_three_d_secure": "automatic"
                    },
                    "link": {
                      "persistent_token": null
                    },
                    "cashapp": {},
                    "amazon_pay": {
                      "express_checkout_element_session_id": null
                    }
                  },
                  "automatic_payment_methods": {
                    "enabled": true,
                    "allow_redirects": "always"
                  },
                  "statement_descriptor_suffix": null,
                  "excluded_payment_method_types": null,
                  "payment_method_configuration_details": {
                    "id": "pmc_1PejDyK6QjZA3FWkUVt0YiK0",
                    "parent": null
                  }
                },
                "amount": 25,
                "status": "authorized",
                "context": {},
                "metadata": {},
                "created_at": "2025-10-30T03:13:17.706Z",
                "deleted_at": null,
                "raw_amount": {
                  "value": "25",
                  "precision": 20
                },
                "updated_at": "2025-10-30T03:15:49.675Z",
                "provider_id": "pp_stripe_stripe",
                "authorized_at": "2025-10-30T03:15:49.663Z",
                "currency_code": "usd",
                "payment_collection_id": "pay_col_01K8SHN3AW4X2FVYZF64BMFE19"
              }
            ]
          }
        },
        "compensate-payment-if-needed": {
          "__type": "Symbol(WorkflowWorkflowData)",
          "output": {
            "__type": "Symbol(WorkflowStepResponse)",
            "output": "payses_01K8SHNYWA9NM89JSSZZQ5J66K",
            "compensateInput": "payses_01K8SHNYWA9NM89JSSZZQ5J66K"
          }
        }
      },
      "payload": {
        "id": "cart_01K8SHMRP2CJ4JA6K1JK8K5X85"
      },
      "compensate": {}
    },
    "errors": []
  },
  "execution": {
    "_v": 0,
    "runId": "01K8SHTQZFN7XSB77EBSMKT7SX",
    "state": "done",
    "steps": {
      "_root": {
        "id": "_root",
        "next": [
          "_root.acquire-lock-step"
        ]
      },
      "_root.acquire-lock-step": {
        "_v": 0,
        "id": "_root.acquire-lock-step",
        "next": [
          "_root.acquire-lock-step.use-query-graph-step",
          "_root.acquire-lock-step.cart-query"
        ],
        "uuid": "01K8P9B356YXQX65YEN6NJQ950",
        "depth": 1,
        "invoke": {
          "state": "done",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154535,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B356YXQX65YEN6NJQ950",
          "action": "acquire-lock-step",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154535,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments"
        ],
        "uuid": "01K8P9B3565GHA3SH0E6BQRQGJ",
        "depth": 2,
        "invoke": {
          "state": "done",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154541,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B3565GHA3SH0E6BQRQGJ",
          "async": false,
          "action": "cart-query",
          "noCompensation": true,
          "compensateAsync": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154541,
        "saveResponse": true
      },
      "_root.acquire-lock-step.use-query-graph-step": {
        "_v": 0,
        "id": "_root.acquire-lock-step.use-query-graph-step",
        "next": [],
        "uuid": "01K8P9B356YSWGCTKGF56D0EAF",
        "depth": 2,
        "invoke": {
          "state": "done",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154541,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B356YSWGCTKGF56D0EAF",
          "action": "use-query-graph-step",
          "noCompensation": true
        },
        "stepFailed": false,
        "lastAttempt": 1761794154541,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed"
        ],
        "uuid": "01K8P9B356SKPSJVGS4JQM42NY",
        "depth": 3,
        "invoke": {
          "state": "done",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154651,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B356SKPSJVGS4JQM42NY",
          "action": "validate-cart-payments",
          "noCompensation": true
        },
        "stepFailed": false,
        "lastAttempt": 1761794154651,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate"
        ],
        "uuid": "01K8P9B356PMWZJHQ5KHE94STT",
        "depth": 4,
        "invoke": {
          "state": "done",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154659,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B356PMWZJHQ5KHE94STT",
          "action": "compensate-payment-if-needed",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154659,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query"
        ],
        "uuid": "01K8P9B356V0KKSEA97A530JYE",
        "depth": 5,
        "invoke": {
          "state": "done",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154662,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B356V0KKSEA97A530JYE",
          "action": "validate",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154662,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping"
        ],
        "uuid": "01K8P9B356EBGM8V32HZ3HXCZB",
        "depth": 6,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154666,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B356EBGM8V32HZ3HXCZB",
          "async": false,
          "action": "shipping-options-query",
          "noCompensation": true,
          "compensateAsync": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154666,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders"
        ],
        "uuid": "01K8P9B357EX5KASDMCB2CW2ZG",
        "depth": 7,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154668,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B357EX5KASDMCB2CW2ZG",
          "action": "validate-shipping",
          "noCompensation": true
        },
        "stepFailed": false,
        "lastAttempt": 1761794154668,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.create-remote-links",
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.update-carts",
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.reserve-inventory-step",
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.register-usage",
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step"
        ],
        "uuid": "01K8P9B3578SRBCDD4GC20TMR8",
        "depth": 8,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154670,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B3578SRBCDD4GC20TMR8",
          "action": "create-orders",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154670,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.update-carts": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.update-carts",
        "next": [],
        "uuid": "01K8P9B357TYNXBF4YP9PZ9XVW",
        "depth": 9,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154671,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B357TYNXBF4YP9PZ9XVW",
          "action": "update-carts",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154671,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.register-usage": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.register-usage",
        "next": [],
        "uuid": "01K8P9B357STHHVWG922J27GGM",
        "depth": 9,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154671,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B357STHHVWG922J27GGM",
          "action": "register-usage",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154671,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization"
        ],
        "uuid": "01K8P9B357M9P2EHJVX1T7VF5N",
        "depth": 9,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154671,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B357M9P2EHJVX1T7VF5N",
          "action": "emit-event-step",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154671,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.create-remote-links": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.create-remote-links",
        "next": [],
        "uuid": "01K8P9B357SR8PD4A6PY4EF3ZY",
        "depth": 9,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154671,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B357SR8PD4A6PY4EF3ZY",
          "action": "create-remote-links",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154671,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.reserve-inventory-step": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.reserve-inventory-step",
        "next": [],
        "uuid": "01K8P9B357MBXEBFGRHR50F9CX",
        "depth": 9,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154671,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B357MBXEBFGRHR50F9CX",
          "action": "reserve-inventory-step",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154671,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step"
        ],
        "uuid": "01K8P9B357X7F6317QSBHWM16K",
        "depth": 10,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154676,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B357X7F6317QSBHWM16K",
          "action": "beforePaymentAuthorization",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154676,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step.add-order-transaction"
        ],
        "uuid": "01K8P9B357BH5HXQ18TS9Z3RF4",
        "depth": 11,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154677,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B357BH5HXQ18TS9Z3RF4",
          "action": "authorize-payment-session-step",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154677,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step.add-order-transaction": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step.add-order-transaction",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step.add-order-transaction.orderCreated"
        ],
        "uuid": "01K8P9B357RJ93RJQPHED4K8HM",
        "depth": 12,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154679,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B357RJ93RJQPHED4K8HM",
          "action": "add-order-transaction",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154679,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step.add-order-transaction.orderCreated": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step.add-order-transaction.orderCreated",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step.add-order-transaction.orderCreated.create-order"
        ],
        "uuid": "01K8P9B357JD0P4X748MVCMJGB",
        "depth": 13,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154681,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B357JD0P4X748MVCMJGB",
          "action": "orderCreated",
          "noCompensation": false
        },
        "stepFailed": false,
        "lastAttempt": 1761794154681,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step.add-order-transaction.orderCreated.create-order": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step.add-order-transaction.orderCreated.create-order",
        "next": [
          "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step.add-order-transaction.orderCreated.create-order.release-lock-step"
        ],
        "uuid": "01K8P9B357AFJ137JJVNM912AM",
        "depth": 14,
        "invoke": {
          "state": "skipped",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154682,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B357AFJ137JJVNM912AM",
          "action": "create-order",
          "noCompensation": true
        },
        "stepFailed": false,
        "lastAttempt": 1761794154682,
        "saveResponse": true
      },
      "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step.add-order-transaction.orderCreated.create-order.release-lock-step": {
        "_v": 0,
        "id": "_root.acquire-lock-step.cart-query.validate-cart-payments.compensate-payment-if-needed.validate.shipping-options-query.validate-shipping.create-orders.emit-event-step.beforePaymentAuthorization.authorize-payment-session-step.add-order-transaction.orderCreated.create-order.release-lock-step",
        "next": [],
        "uuid": "01K8P9B357TS624JEXV1WQVTRF",
        "depth": 15,
        "invoke": {
          "state": "done",
          "status": "ok"
        },
        "attempts": 1,
        "failures": 0,
        "startedAt": 1761794154684,
        "compensate": {
          "state": "dormant",
          "status": "idle"
        },
        "definition": {
          "uuid": "01K8P9B357TS624JEXV1WQVTRF",
          "action": "release-lock-step",
          "noCompensation": true
        },
        "stepFailed": false,
        "lastAttempt": 1761794154684,
        "saveResponse": true
      }
    },
    "modelId": "complete-cart",
    "options": {
      "name": "complete-cart",
      "store": true,
      "idempotent": false,
      "retentionTime": 259200
    },
    "metadata": {
      "sourcePath": "/server/node_modules/@medusajs/core-flows/dist/cart/workflows/complete-cart.js",
      "eventGroupId": "01K8SHTQZ4WK5ES7VPX16K8FS9",
      "preventReleaseEvents": false
    },
    "startedAt": 1761794154532,
    "definition": {
      "next": [
        {
          "uuid": "01K8P9B356YSWGCTKGF56D0EAF",
          "action": "use-query-graph-step",
          "noCompensation": true
        },
        {
          "next": {
            "next": {
              "next": {
                "next": {
                  "next": {
                    "next": {
                      "next": [
                        {
                          "uuid": "01K8P9B357SR8PD4A6PY4EF3ZY",
                          "action": "create-remote-links",
                          "noCompensation": false
                        },
                        {
                          "uuid": "01K8P9B357TYNXBF4YP9PZ9XVW",
                          "action": "update-carts",
                          "noCompensation": false
                        },
                        {
                          "uuid": "01K8P9B357MBXEBFGRHR50F9CX",
                          "action": "reserve-inventory-step",
                          "noCompensation": false
                        },
                        {
                          "uuid": "01K8P9B357STHHVWG922J27GGM",
                          "action": "register-usage",
                          "noCompensation": false
                        },
                        {
                          "next": {
                            "next": {
                              "next": {
                                "next": {
                                  "next": {
                                    "next": {
                                      "uuid": "01K8P9B357TS624JEXV1WQVTRF",
                                      "action": "release-lock-step",
                                      "noCompensation": true
                                    },
                                    "uuid": "01K8P9B357AFJ137JJVNM912AM",
                                    "action": "create-order",
                                    "noCompensation": true
                                  },
                                  "uuid": "01K8P9B357JD0P4X748MVCMJGB",
                                  "action": "orderCreated",
                                  "noCompensation": false
                                },
                                "uuid": "01K8P9B357RJ93RJQPHED4K8HM",
                                "action": "add-order-transaction",
                                "noCompensation": false
                              },
                              "uuid": "01K8P9B357BH5HXQ18TS9Z3RF4",
                              "action": "authorize-payment-session-step",
                              "noCompensation": false
                            },
                            "uuid": "01K8P9B357X7F6317QSBHWM16K",
                            "action": "beforePaymentAuthorization",
                            "noCompensation": false
                          },
                          "uuid": "01K8P9B357M9P2EHJVX1T7VF5N",
                          "action": "emit-event-step",
                          "noCompensation": false
                        }
                      ],
                      "uuid": "01K8P9B3578SRBCDD4GC20TMR8",
                      "action": "create-orders",
                      "noCompensation": false
                    },
                    "uuid": "01K8P9B357EX5KASDMCB2CW2ZG",
                    "action": "validate-shipping",
                    "noCompensation": true
                  },
                  "uuid": "01K8P9B356EBGM8V32HZ3HXCZB",
                  "async": false,
                  "action": "shipping-options-query",
                  "noCompensation": true,
                  "compensateAsync": false
                },
                "uuid": "01K8P9B356V0KKSEA97A530JYE",
                "action": "validate",
                "noCompensation": false
              },
              "uuid": "01K8P9B356PMWZJHQ5KHE94STT",
              "action": "compensate-payment-if-needed",
              "noCompensation": false
            },
            "uuid": "01K8P9B356SKPSJVGS4JQM42NY",
            "action": "validate-cart-payments",
            "noCompensation": true
          },
          "uuid": "01K8P9B3565GHA3SH0E6BQRQGJ",
          "async": false,
          "action": "cart-query",
          "noCompensation": true,
          "compensateAsync": false
        }
      ],
      "uuid": "01K8P9B356YXQX65YEN6NJQ950",
      "action": "acquire-lock-step",
      "noCompensation": false
    },
    "timedOutAt": null,
    "hasAsyncSteps": false,
    "transactionId": "cart_01K8SHMRP2CJ4JA6K1JK8K5X85",
    "hasFailedSteps": false,
    "hasSkippedSteps": true,
    "hasWaitingSteps": false,
    "hasRevertedSteps": false,
    "hasSkippedOnFailureSteps": false
  },
  "state": "done",
  "created_at": "2025-10-30T03:15:54.509Z",
  "updated_at": "2025-10-30T03:15:54.703Z",
  "deleted_at": null
}
```


---
**@radeknapora** commented on 2025-10-30T17:36:47Z:

I believe there are still multiple problems with the Stripe payment integration. This issue demonstrates the scale of the problem well: https://github.com/medusajs/medusa/issues/13837


---
**@420coupe** commented on 2025-11-05T14:20:25Z:

@adrien2p @willbouch @MedusaNick tagging you guys again to re-open this issue. Still occurring in latest 2.11.3


---
**@adrien2p** commented on 2025-11-05T16:24:49Z:

> [@adrien2p](https://github.com/adrien2p) [@willbouch](https://github.com/willbouch) [@MedusaNick](https://github.com/MedusaNick) tagging you guys again to re-open this issue. Still occurring in latest 2.11.3

thanks for trying, we will investigate, what is weird is that the new workflows will not use the cart as the transaction id, plus we are already locking the operation in redis, so two workflows that target the same cart should not run at the same time until the lock is released 🤔 


---
**@adrien2p** commented on 2025-11-05T16:34:33Z:

would you be able to share your workflow executions for the last test you have made please?


---
**@adrien2p** commented on 2025-11-05T17:15:58Z:

ok, we believe we might have found the culprit, but it is a bit different than the original assumption. We have opened a pr [here](https://github.com/medusajs/medusa/pull/13977) and the snapshot is being generated as we speak. Would you be able to try it @420coupe, please?


---
**@420coupe** commented on 2025-11-05T17:19:10Z:

> ok, we believe we might have found the culprit, but it is a bit different than the original assumption. We have opened a pr [here](https://github.com/medusajs/medusa/pull/13977) and the snapshot is being generated as we speak. Would you be able to try it [@420coupe](https://github.com/420coupe), please?

I will be able to post previous workflow and test out the new PR in a couple of hours. Will provide feedback shortly. 


---
**@carlos-r-l-rodrigues** commented on 2025-11-05T18:08:03Z:

Hi @420coupe, this is the snapshot: `2.11.4-snapshot-20251105174837`
No need to post the previous workflow run.

Thanks


---
**@adrien2p** commented on 2025-11-07T08:40:51Z:

> > ok, we believe we might have found the culprit, but it is a bit different than the original assumption. We have opened a pr [here](https://github.com/medusajs/medusa/pull/13977) and the snapshot is being generated as we speak. Would you be able to try it [@420coupe](https://github.com/420coupe), please?
> 
> I will be able to post previous workflow and test out the new PR in a couple of hours. Will provide feedback shortly.

Hey @420coupe, have you had any change to test?


---
**@420coupe** commented on 2025-11-07T17:37:12Z:

> > > ok, we believe we might have found the culprit, but it is a bit different than the original assumption. We have opened a pr [here](https://github.com/medusajs/medusa/pull/13977) and the snapshot is being generated as we speak. Would you be able to try it [@420coupe](https://github.com/420coupe), please?
> > 
> > 
> > I will be able to post previous workflow and test out the new PR in a couple of hours. Will provide feedback shortly.
> 
> Hey [@420coupe](https://github.com/420coupe), have you had any change to test?

Hey guys sorry for delay, trying to test the snapshot and keep getting this issue when trying to install - fails on rollup step. 

```json
{
  "name": "medusa-starter-default",
  "version": "0.0.1",
  "description": "A starter for Medusa projects.",
  "author": "Medusa (https://medusajs.com)",
  "license": "MIT",
  "keywords": [
    "sqlite",
    "postgres",
    "typescript",
    "ecommerce",
    "headless",
    "medusa"
  ],
  "scripts": {
    "build": "medusa build",
    "seed": "medusa exec ./src/scripts/seed.ts",
    "start": "medusa start",
    "dev": "medusa develop",
    "test:integration:http": "TEST_TYPE=integration:http NODE_OPTIONS=--experimental-vm-modules jest --silent=false --runInBand --forceExit",
    "test:integration:modules": "TEST_TYPE=integration:modules NODE_OPTIONS=--experimental-vm-modules jest --silent --runInBand --forceExit",
    "test:unit": "TEST_TYPE=unit NODE_OPTIONS=--experimental-vm-modules jest --silent --runInBand --forceExit",
    "full-cost-reconcile": "node -r dotenv/config -r ts-node/register src/scripts/full-cost-reconciliation.ts",
    "per-message-costs": "node -r dotenv/config -r ts-node/register src/scripts/per-message-cost-tracker.ts",
    "backfill-tiers": "medusa exec ./src/scripts/backfill-customer-tiers-merged.ts",
    "predeploy": "medusa db:migrate",
    "docker:build": "docker build -t derftuned-medusa .",
    "docker:up": "docker compose up --build -d",
    "docker:down": "docker compose down",
    "docker:logs": "docker compose logs -f"
  },
  "dependencies": {
    "@medusajs/admin-sdk": "2.11.4-snapshot-20251105174837",
    "@medusajs/cli": "2.11.4-snapshot-20251105174837",
    "@medusajs/framework": "2.11.4-snapshot-20251105174837",
    "@medusajs/medusa": "2.11.4-snapshot-20251105174837",
    "@sendgrid/eventwebhook": "^8.0.0",
    "multer": "^1.4.5-lts.1",
    "twilio": "^5.3.3"
  },
  "devDependencies": {
    "@medusajs/test-utils": "2.11.4-snapshot-20251105174837",
    "@swc/core": "1.5.7",
    "@swc/jest": "^0.2.36",
    "@types/jest": "^29.5.13",
    "@types/multer": "^1.4.12",
    "@types/node": "^20.0.0",
    "@types/react": "^18.3.2",
    "@types/react-dom": "^18.2.25",
    "jest": "^29.7.0",
    "prop-types": "^15.8.1",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "ts-node": "^10.9.2",
    "typescript": "^5.6.2",
    "vite": "^5.2.11",
    "yalc": "^1.0.0-pre.53"
  },
  "engines": {
    "node": ">=20"
  }
}
```

```logs
$ rm -rf node_modules yarn.lock
coupe420@420coupe-Workstation:~/Documents/projects/derftuned-medusa$ yarn
yarn install v1.22.22
info No lockfile found.
[1/5] Validating package.json...
[2/5] Resolving packages...
warning @medusajs/cli > pg-god > cli-ux@5.6.7: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/config@1.18.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/command@1.8.36: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > cli-ux > @oclif/command@1.8.36: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/command > @oclif/config@1.18.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/config@1.18.2: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/command@1.8.36: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > cli-ux > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/config > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/command > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/errors@1.3.5: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/config > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > cli-ux > @oclif/screen@1.0.4: Deprecated in favor of @oclif/core
warning @medusajs/cli > pg-god > @oclif/config > @oclif/parser@3.8.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/command > @oclif/parser@3.8.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/config > @oclif/parser@3.8.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/config > @oclif/parser > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/command > @oclif/help@1.0.15: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/help@1.0.15: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/command > @oclif/help > @oclif/config@1.18.16: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/command > @oclif/help > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/command > @oclif/help > @oclif/config > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/cli > pg-god > @oclif/command > @oclif/help > @oclif/config > @oclif/parser@3.8.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
warning @medusajs/medusa > @medusajs/draft-order > match-sorter@6.4.0: This was arguably a breaking change. Not in API, but more results can be returned. Upgrade to the next major when you are ready for that
warning @medusajs/medusa > @medusajs/draft-order > lodash.isequal@4.5.0: This package is deprecated. Use require('node:util').isDeepStrictEqual instead.
warning @medusajs/medusa > @medusajs/admin-bundler > @medusajs/dashboard > match-sorter@6.4.0: This was arguably a breaking change. Not in API, but more results can be returned. Upgrade to the next major when you are ready for that
warning @medusajs/medusa > @medusajs/admin-bundler > @medusajs/dashboard > lodash.isequal@4.5.0: This package is deprecated. Use require('node:util').isDeepStrictEqual instead.
warning multer@1.4.5-lts.2: Multer 1.x is impacted by a number of vulnerabilities, which have been patched in 2.x. You should upgrade to the latest 2.x version.
warning jest > jest-cli > jest-config > glob@7.2.3: Glob versions prior to v9 are no longer supported
warning jest > @jest/core > jest-runtime > glob@7.2.3: Glob versions prior to v9 are no longer supported
warning jest > @jest/core > @jest/reporters > glob@7.2.3: Glob versions prior to v9 are no longer supported
warning jest > jest-cli > jest-config > glob > inflight@1.0.6: This module is not supported, and leaks memory. Do not use it. Check out lru-cache if you want a good and tested way to coalesce async requests by a key value, which is much more comprehensive and powerful.
warning jest > @jest/core > @jest/transform > babel-plugin-istanbul > test-exclude > glob@7.2.3: Glob versions prior to v9 are no longer supported
warning yalc > glob@7.2.3: Glob versions prior to v9 are no longer supported
warning yalc > npm-packlist > glob@7.2.3: Glob versions prior to v9 are no longer supported
[3/5] Fetching packages...
warning react-hook-form@7.49.1: The engine "pnpm" appears to be invalid.
[4/5] Linking dependencies...
warning "@medusajs/medusa > @medusajs/caching@2.11.4-snapshot-20251105174837" has unmet peer dependency "awilix@^8.0.1".
warning "@medusajs/medusa > @medusajs/analytics-posthog@2.11.4-snapshot-20251105174837" has unmet peer dependency "posthog-node@^5.11.0".
[5/5] Building fresh packages...
[1/6] ⠂ protobufjs
[2/6] ⠂ @medusajs/telemetry
[3/6] ⠂ rollup
[4/6] ⠂ esbuild
error /home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup: Command failed.
Exit code: 127
Command: patch-package
Arguments: 



```


---
**@adrien2p** commented on 2025-11-10T08:40:58Z:

> > > > ok, we believe we might have found the culprit, but it is a bit different than the original assumption. We have opened a pr [here](https://github.com/medusajs/medusa/pull/13977) and the snapshot is being generated as we speak. Would you be able to try it [@420coupe](https://github.com/420coupe), please?
> > > 
> > > 
> > > I will be able to post previous workflow and test out the new PR in a couple of hours. Will provide feedback shortly.
> > 
> > 
> > Hey [@420coupe](https://github.com/420coupe), have you had any change to test?
> 
> Hey guys sorry for delay, trying to test the snapshot and keep getting this issue when trying to install - fails on rollup step.
> 
> {
>   "name": "medusa-starter-default",
>   "version": "0.0.1",
>   "description": "A starter for Medusa projects.",
>   "author": "Medusa (https://medusajs.com)",
>   "license": "MIT",
>   "keywords": [
>     "sqlite",
>     "postgres",
>     "typescript",
>     "ecommerce",
>     "headless",
>     "medusa"
>   ],
>   "scripts": {
>     "build": "medusa build",
>     "seed": "medusa exec ./src/scripts/seed.ts",
>     "start": "medusa start",
>     "dev": "medusa develop",
>     "test:integration:http": "TEST_TYPE=integration:http NODE_OPTIONS=--experimental-vm-modules jest --silent=false --runInBand --forceExit",
>     "test:integration:modules": "TEST_TYPE=integration:modules NODE_OPTIONS=--experimental-vm-modules jest --silent --runInBand --forceExit",
>     "test:unit": "TEST_TYPE=unit NODE_OPTIONS=--experimental-vm-modules jest --silent --runInBand --forceExit",
>     "full-cost-reconcile": "node -r dotenv/config -r ts-node/register src/scripts/full-cost-reconciliation.ts",
>     "per-message-costs": "node -r dotenv/config -r ts-node/register src/scripts/per-message-cost-tracker.ts",
>     "backfill-tiers": "medusa exec ./src/scripts/backfill-customer-tiers-merged.ts",
>     "predeploy": "medusa db:migrate",
>     "docker:build": "docker build -t derftuned-medusa .",
>     "docker:up": "docker compose up --build -d",
>     "docker:down": "docker compose down",
>     "docker:logs": "docker compose logs -f"
>   },
>   "dependencies": {
>     "@medusajs/admin-sdk": "2.11.4-snapshot-20251105174837",
>     "@medusajs/cli": "2.11.4-snapshot-20251105174837",
>     "@medusajs/framework": "2.11.4-snapshot-20251105174837",
>     "@medusajs/medusa": "2.11.4-snapshot-20251105174837",
>     "@sendgrid/eventwebhook": "^8.0.0",
>     "multer": "^1.4.5-lts.1",
>     "twilio": "^5.3.3"
>   },
>   "devDependencies": {
>     "@medusajs/test-utils": "2.11.4-snapshot-20251105174837",
>     "@swc/core": "1.5.7",
>     "@swc/jest": "^0.2.36",
>     "@types/jest": "^29.5.13",
>     "@types/multer": "^1.4.12",
>     "@types/node": "^20.0.0",
>     "@types/react": "^18.3.2",
>     "@types/react-dom": "^18.2.25",
>     "jest": "^29.7.0",
>     "prop-types": "^15.8.1",
>     "react": "^18.2.0",
>     "react-dom": "^18.2.0",
>     "ts-node": "^10.9.2",
>     "typescript": "^5.6.2",
>     "vite": "^5.2.11",
>     "yalc": "^1.0.0-pre.53"
>   },
>   "engines": {
>     "node": ">=20"
>   }
> }
> ```
> $ rm -rf node_modules yarn.lock
> coupe420@420coupe-Workstation:~/Documents/projects/derftuned-medusa$ yarn
> yarn install v1.22.22
> info No lockfile found.
> [1/5] Validating package.json...
> [2/5] Resolving packages...
> warning @medusajs/cli > pg-god > cli-ux@5.6.7: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/config@1.18.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/command@1.8.36: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > cli-ux > @oclif/command@1.8.36: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/command > @oclif/config@1.18.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/config@1.18.2: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/command@1.8.36: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > cli-ux > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/config > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/command > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/errors@1.3.5: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/config > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > cli-ux > @oclif/screen@1.0.4: Deprecated in favor of @oclif/core
> warning @medusajs/cli > pg-god > @oclif/config > @oclif/parser@3.8.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/command > @oclif/parser@3.8.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/config > @oclif/parser@3.8.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/config > @oclif/parser > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/command > @oclif/help@1.0.15: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/help@1.0.15: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/command > @oclif/help > @oclif/config@1.18.16: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/command > @oclif/help > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/command > @oclif/help > @oclif/config > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/cli > pg-god > @oclif/command > @oclif/help > @oclif/config > @oclif/parser@3.8.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> warning @medusajs/medusa > @medusajs/draft-order > match-sorter@6.4.0: This was arguably a breaking change. Not in API, but more results can be returned. Upgrade to the next major when you are ready for that
> warning @medusajs/medusa > @medusajs/draft-order > lodash.isequal@4.5.0: This package is deprecated. Use require('node:util').isDeepStrictEqual instead.
> warning @medusajs/medusa > @medusajs/admin-bundler > @medusajs/dashboard > match-sorter@6.4.0: This was arguably a breaking change. Not in API, but more results can be returned. Upgrade to the next major when you are ready for that
> warning @medusajs/medusa > @medusajs/admin-bundler > @medusajs/dashboard > lodash.isequal@4.5.0: This package is deprecated. Use require('node:util').isDeepStrictEqual instead.
> warning multer@1.4.5-lts.2: Multer 1.x is impacted by a number of vulnerabilities, which have been patched in 2.x. You should upgrade to the latest 2.x version.
> warning jest > jest-cli > jest-config > glob@7.2.3: Glob versions prior to v9 are no longer supported
> warning jest > @jest/core > jest-runtime > glob@7.2.3: Glob versions prior to v9 are no longer supported
> warning jest > @jest/core > @jest/reporters > glob@7.2.3: Glob versions prior to v9 are no longer supported
> warning jest > jest-cli > jest-config > glob > inflight@1.0.6: This module is not supported, and leaks memory. Do not use it. Check out lru-cache if you want a good and tested way to coalesce async requests by a key value, which is much more comprehensive and powerful.
> warning jest > @jest/core > @jest/transform > babel-plugin-istanbul > test-exclude > glob@7.2.3: Glob versions prior to v9 are no longer supported
> warning yalc > glob@7.2.3: Glob versions prior to v9 are no longer supported
> warning yalc > npm-packlist > glob@7.2.3: Glob versions prior to v9 are no longer supported
> [3/5] Fetching packages...
> warning react-hook-form@7.49.1: The engine "pnpm" appears to be invalid.
> [4/5] Linking dependencies...
> warning "@medusajs/medusa > @medusajs/caching@2.11.4-snapshot-20251105174837" has unmet peer dependency "awilix@^8.0.1".
> warning "@medusajs/medusa > @medusajs/analytics-posthog@2.11.4-snapshot-20251105174837" has unmet peer dependency "posthog-node@^5.11.0".
> [5/5] Building fresh packages...
> [1/6] ⠂ protobufjs
> [2/6] ⠂ @medusajs/telemetry
> [3/6] ⠂ rollup
> [4/6] ⠂ esbuild
> error /home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup: Command failed.
> Exit code: 127
> Command: patch-package
> Arguments: 
> ```

can you update your dev deps with the [following](https://github.com/medusajs/medusa-starter-default/pull/2564/files) I believe it should resolve your issues


---
**@420coupe** commented on 2025-11-11T16:14:46Z:

> > > > > ok, we believe we might have found the culprit, but it is a bit different than the original assumption. We have opened a pr [here](https://github.com/medusajs/medusa/pull/13977) and the snapshot is being generated as we speak. Would you be able to try it [@420coupe](https://github.com/420coupe), please?
> > > > 
> > > > 
> > > > I will be able to post previous workflow and test out the new PR in a couple of hours. Will provide feedback shortly.
> > > 
> > > 
> > > Hey [@420coupe](https://github.com/420coupe), have you had any change to test?
> > 
> > 
> > Hey guys sorry for delay, trying to test the snapshot and keep getting this issue when trying to install - fails on rollup step.
> > {
> > "name": "medusa-starter-default",
> > "version": "0.0.1",
> > "description": "A starter for Medusa projects.",
> > "author": "Medusa (https://medusajs.com)",
> > "license": "MIT",
> > "keywords": [
> > "sqlite",
> > "postgres",
> > "typescript",
> > "ecommerce",
> > "headless",
> > "medusa"
> > ],
> > "scripts": {
> > "build": "medusa build",
> > "seed": "medusa exec ./src/scripts/seed.ts",
> > "start": "medusa start",
> > "dev": "medusa develop",
> > "test:integration:http": "TEST_TYPE=integration:http NODE_OPTIONS=--experimental-vm-modules jest --silent=false --runInBand --forceExit",
> > "test:integration:modules": "TEST_TYPE=integration:modules NODE_OPTIONS=--experimental-vm-modules jest --silent --runInBand --forceExit",
> > "test:unit": "TEST_TYPE=unit NODE_OPTIONS=--experimental-vm-modules jest --silent --runInBand --forceExit",
> > "full-cost-reconcile": "node -r dotenv/config -r ts-node/register src/scripts/full-cost-reconciliation.ts",
> > "per-message-costs": "node -r dotenv/config -r ts-node/register src/scripts/per-message-cost-tracker.ts",
> > "backfill-tiers": "medusa exec ./src/scripts/backfill-customer-tiers-merged.ts",
> > "predeploy": "medusa db:migrate",
> > "docker:build": "docker build -t derftuned-medusa .",
> > "docker:up": "docker compose up --build -d",
> > "docker:down": "docker compose down",
> > "docker:logs": "docker compose logs -f"
> > },
> > "dependencies": {
> > "@medusajs/admin-sdk": "2.11.4-snapshot-20251105174837",
> > "@medusajs/cli": "2.11.4-snapshot-20251105174837",
> > "@medusajs/framework": "2.11.4-snapshot-20251105174837",
> > "@medusajs/medusa": "2.11.4-snapshot-20251105174837",
> > "@sendgrid/eventwebhook": "^8.0.0",
> > "multer": "^1.4.5-lts.1",
> > "twilio": "^5.3.3"
> > },
> > "devDependencies": {
> > "@medusajs/test-utils": "2.11.4-snapshot-20251105174837",
> > "@swc/core": "1.5.7",
> > "@swc/jest": "^0.2.36",
> > "@types/jest": "^29.5.13",
> > "@types/multer": "^1.4.12",
> > "@types/node": "^20.0.0",
> > "@types/react": "^18.3.2",
> > "@types/react-dom": "^18.2.25",
> > "jest": "^29.7.0",
> > "prop-types": "^15.8.1",
> > "react": "^18.2.0",
> > "react-dom": "^18.2.0",
> > "ts-node": "^10.9.2",
> > "typescript": "^5.6.2",
> > "vite": "^5.2.11",
> > "yalc": "^1.0.0-pre.53"
> > },
> > "engines": {
> > "node": ">=20"
> > }
> > }
> > ```
> > $ rm -rf node_modules yarn.lock
> > coupe420@420coupe-Workstation:~/Documents/projects/derftuned-medusa$ yarn
> > yarn install v1.22.22
> > info No lockfile found.
> > [1/5] Validating package.json...
> > [2/5] Resolving packages...
> > warning @medusajs/cli > pg-god > cli-ux@5.6.7: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/config@1.18.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/command@1.8.36: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > cli-ux > @oclif/command@1.8.36: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/command > @oclif/config@1.18.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/config@1.18.2: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/command@1.8.36: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > cli-ux > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/config > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/command > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/errors@1.3.5: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/config > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > cli-ux > @oclif/screen@1.0.4: Deprecated in favor of @oclif/core
> > warning @medusajs/cli > pg-god > @oclif/config > @oclif/parser@3.8.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/command > @oclif/parser@3.8.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/config > @oclif/parser@3.8.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/config > @oclif/parser > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/command > @oclif/help@1.0.15: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/plugin-help > @oclif/help@1.0.15: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/command > @oclif/help > @oclif/config@1.18.16: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/command > @oclif/help > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/command > @oclif/help > @oclif/config > @oclif/errors@1.3.6: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/cli > pg-god > @oclif/command > @oclif/help > @oclif/config > @oclif/parser@3.8.17: Package no longer supported. Contact Support at https://www.npmjs.com/support for more info.
> > warning @medusajs/medusa > @medusajs/draft-order > match-sorter@6.4.0: This was arguably a breaking change. Not in API, but more results can be returned. Upgrade to the next major when you are ready for that
> > warning @medusajs/medusa > @medusajs/draft-order > lodash.isequal@4.5.0: This package is deprecated. Use require('node:util').isDeepStrictEqual instead.
> > warning @medusajs/medusa > @medusajs/admin-bundler > @medusajs/dashboard > match-sorter@6.4.0: This was arguably a breaking change. Not in API, but more results can be returned. Upgrade to the next major when you are ready for that
> > warning @medusajs/medusa > @medusajs/admin-bundler > @medusajs/dashboard > lodash.isequal@4.5.0: This package is deprecated. Use require('node:util').isDeepStrictEqual instead.
> > warning multer@1.4.5-lts.2: Multer 1.x is impacted by a number of vulnerabilities, which have been patched in 2.x. You should upgrade to the latest 2.x version.
> > warning jest > jest-cli > jest-config > glob@7.2.3: Glob versions prior to v9 are no longer supported
> > warning jest > @jest/core > jest-runtime > glob@7.2.3: Glob versions prior to v9 are no longer supported
> > warning jest > @jest/core > @jest/reporters > glob@7.2.3: Glob versions prior to v9 are no longer supported
> > warning jest > jest-cli > jest-config > glob > inflight@1.0.6: This module is not supported, and leaks memory. Do not use it. Check out lru-cache if you want a good and tested way to coalesce async requests by a key value, which is much more comprehensive and powerful.
> > warning jest > @jest/core > @jest/transform > babel-plugin-istanbul > test-exclude > glob@7.2.3: Glob versions prior to v9 are no longer supported
> > warning yalc > glob@7.2.3: Glob versions prior to v9 are no longer supported
> > warning yalc > npm-packlist > glob@7.2.3: Glob versions prior to v9 are no longer supported
> > [3/5] Fetching packages...
> > warning react-hook-form@7.49.1: The engine "pnpm" appears to be invalid.
> > [4/5] Linking dependencies...
> > warning "@medusajs/medusa > @medusajs/caching@2.11.4-snapshot-20251105174837" has unmet peer dependency "awilix@^8.0.1".
> > warning "@medusajs/medusa > @medusajs/analytics-posthog@2.11.4-snapshot-20251105174837" has unmet peer dependency "posthog-node@^5.11.0".
> > [5/5] Building fresh packages...
> > [1/6] ⠂ protobufjs
> > [2/6] ⠂ @medusajs/telemetry
> > [3/6] ⠂ rollup
> > [4/6] ⠂ esbuild
> > error /home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup: Command failed.
> > Exit code: 127
> > Command: patch-package
> > Arguments: 
> > ```
> 
> can you update your dev deps with the [following](https://github.com/medusajs/medusa-starter-default/pull/2564/files) I believe it should resolve your issues

I was able to install, but build fails. see below

```log
yarn build
yarn run v1.22.22
$ medusa build
info:    Starting build...
info:    Compiling backend source...
info:    Removing existing ".medusa/server" folder
info:    Compiling frontend source...
info:    Backend build completed successfully (3.00s)
x Build failed in 3.99s
error:   Unable to compile frontend source
error:   node_modules/@medusajs/dashboard/dist/chunk-MHC2COUJ.mjs (13:2): "ptPT" is not exported by "node_modules/date-fns/locale.mjs", imported by "node_modules/@medusajs/dashboard/dist/chunk-MHC2COUJ.mjs".
file: /home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-MHC2COUJ.mjs:13:2

11:   pl,
12:   ptBR,
13:   ptPT,
      ^
14:   th,
15:   tr,

node_modules/@medusajs/dashboard/dist/chunk-MHC2COUJ.mjs (13:2): "ptPT" is not exported by "node_modules/date-fns/locale.mjs", imported by "node_modules/@medusajs/dashboard/dist/chunk-MHC2COUJ.mjs".
file: /home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-MHC2COUJ.mjs:13:2

11:   pl,
12:   ptBR,
13:   ptPT,
      ^
14:   th,
15:   tr,

    at getRollupError (file:///home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup/dist/es/shared/parseAst.js:401:41)
    at error (file:///home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup/dist/es/shared/parseAst.js:397:42)
    at Module.error (file:///home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup/dist/es/shared/node-entry.js:16946:16)
    at Module.traceVariable (file:///home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup/dist/es/shared/node-entry.js:17400:29)
    at ModuleScope.findVariable (file:///home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup/dist/es/shared/node-entry.js:15067:39)
    at Identifier.bind (file:///home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup/dist/es/shared/node-entry.js:5415:40)
    at Property.bind (file:///home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup/dist/es/shared/node-entry.js:2806:23)
    at ObjectExpression.bind (file:///home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup/dist/es/shared/node-entry.js:2802:28)
    at ArrayExpression.bind (file:///home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup/dist/es/shared/node-entry.js:2802:28)
    at VariableDeclarator.bind (file:///home/coupe420/Documents/projects/derftuned-medusa/node_modules/rollup/dist/es/shared/node-entry.js:2806:23) {
  binding: 'ptPT',
  code: 'MISSING_EXPORT',
  exporter: '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/date-fns/locale.mjs',
  id: '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-MHC2COUJ.mjs',
  url: 'https://rollupjs.org/troubleshooting/#error-name-is-not-exported-by-module',
  pos: 100,
  loc: {
    column: 2,
    file: '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-MHC2COUJ.mjs',
    line: 13
  },
  frame: '11:   pl,\n12:   ptBR,\n13:   ptPT,\n      ^\n14:   th,\n15:   tr,',
  watchFiles: [
    '/home/coupe420/Documents/projects/derftuned-medusa/.medusa/client/index.html',
    '/home/coupe420/Documents/projects/derftuned-medusa/.medusa/client/entry.jsx',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/react/jsx-dev-runtime.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/react/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/react-dom/client.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/app.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/.medusa/client/index.css',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/draft-order/.medusa/server/src/admin/index.mjs',
    'package.json',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/react/jsx-runtime.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-NQIC7ZFS.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-ONB3JEHR.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-YCDDT44O.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-4GQOUCX6.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-2VTICXJR.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-D3YQN7HV.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-PMA2D6IL.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-MNXC6Q4F.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-RM6NY572.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-C5P5PL3E.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-DG7J63J2.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-LPEUYMRK.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-ZCARHA6C.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-OC7BQLYI.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-OZPB6JBL.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-S4DMV3ZT.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-MHC2COUJ.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-OBQI23QM.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-KXRW6JRE.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-KOSCMAIC.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-X6DSNTTX.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-I6E6CALJ.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-B4GODIOW.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-N4N4KGET.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-QTCZFYFH.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-ENV6YVOM.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-PIR2H25N.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-C5LYZZZ5.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-RLY2SL5E.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-2ZKVRTBW.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-XYHXWLTJ.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-F6PXCY3N.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-IXZVR3HG.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-R2G2B47Y.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-GRT22PE5.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-32IQRUVY.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-WTK7SR6S.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-6XWHQ6ON.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-MQALAB34.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-OGAZYXOV.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-KX4P5L3R.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-V2LANK5S.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-QZ6PT4QV.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-QL4XKIVL.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-4BGVSXZZ.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-FXYH54JP.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-774WSTCC.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-DEQUVHHE.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/dashboard/dist/chunk-QZ7TP4HQ.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/react/cjs/react-jsx-dev-runtime.development.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/react-dom/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/react/cjs/react.development.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/admin-shared/dist/index.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/js-sdk/dist/esm/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@tanstack/react-query/build/modern/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/ui/dist/esm/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/icons/dist/esm/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/motion/dist/es/motion/lib/react.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/react-router-dom/dist/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/date-fns/locale.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/react-i18next/dist/es/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/radix-ui/dist/index.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/react-hook-form/dist/index.esm.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/react/cjs/react-jsx-runtime.development.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/i18next/dist/esm/i18next.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/i18next-browser-languagedetector/dist/esm/i18nextBrowserLanguageDetector.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/react-dom/cjs/react-dom.development.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@ariakit/react/esm/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/lodash.debounce/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@uiw/react-json-view/esm/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/match-sorter/dist/match-sorter.esm.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/date-fns/index.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/admin-sdk/dist/index.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/lodash.isequal/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@hookform/resolvers/zod/dist/zod.mjs',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/js-sdk/dist/esm/admin/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/js-sdk/dist/esm/auth/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/js-sdk/dist/esm/client.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@medusajs/js-sdk/dist/esm/store/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@tanstack/query-core/build/modern/index.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@tanstack/react-query/build/modern/types.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@tanstack/react-query/build/modern/useQueries.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@tanstack/react-query/build/modern/useQuery.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@tanstack/react-query/build/modern/useSuspenseQuery.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@tanstack/react-query/build/modern/useSuspenseInfiniteQuery.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@tanstack/react-query/build/modern/useSuspenseQueries.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@tanstack/react-query/build/modern/usePrefetchQuery.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@tanstack/react-query/build/modern/usePrefetchInfiniteQuery.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@tanstack/react-query/build/modern/queryOptions.js',
    '/home/coupe420/Documents/projects/derftuned-medusa/node_modules/@tanstack/react-query/build/modern/infiniteQueryOptions.js',
    ... 3793 more items
  ],
  [Symbol(augmented)]: true
}
error Command failed with exit code 1.
info Visit https://yarnpkg.com/en/docs/cli/run for documentation about this command.
```


---
**@adrien2p** commented on 2025-11-11T16:30:26Z:

Have you updated all your packages with the snapshot?


---
**@420coupe** commented on 2025-11-11T16:36:57Z:

> Have you updated all your packages with the snapshot?

here's current package.json 

```json
{
  "name": "medusa-starter-default",
  "version": "0.0.1",
  "description": "A starter for Medusa projects.",
  "author": "Medusa (https://medusajs.com)",
  "license": "MIT",
  "keywords": [
    "sqlite",
    "postgres",
    "typescript",
    "ecommerce",
    "headless",
    "medusa"
  ],
  "scripts": {
    "build": "medusa build",
    "seed": "medusa exec ./src/scripts/seed.ts",
    "start": "medusa start",
    "dev": "medusa develop",
    "test:integration:http": "TEST_TYPE=integration:http NODE_OPTIONS=--experimental-vm-modules jest --silent=false --runInBand --forceExit",
    "test:integration:modules": "TEST_TYPE=integration:modules NODE_OPTIONS=--experimental-vm-modules jest --silent --runInBand --forceExit",
    "test:unit": "TEST_TYPE=unit NODE_OPTIONS=--experimental-vm-modules jest --silent --runInBand --forceExit",
    "full-cost-reconcile": "node -r dotenv/config -r ts-node/register src/scripts/full-cost-reconciliation.ts",
    "per-message-costs": "node -r dotenv/config -r ts-node/register src/scripts/per-message-cost-tracker.ts",
    "backfill-tiers": "medusa exec ./src/scripts/backfill-customer-tiers-merged.ts",
    "predeploy": "medusa db:migrate",
    "docker:build": "docker build -t derftuned-medusa .",
    "docker:up": "docker compose up --build -d",
    "docker:down": "docker compose down",
    "docker:logs": "docker compose logs -f"
  },
  "dependencies": {
    "@medusajs/admin-sdk": "2.11.4-snapshot-20251105174837",
    "@medusajs/cli": "2.11.4-snapshot-20251105174837",
    "@medusajs/framework": "2.11.4-snapshot-20251105174837",
    "@medusajs/medusa": "2.11.4-snapshot-20251105174837",
    "@sendgrid/eventwebhook": "^8.0.0",
    "multer": "^1.4.5-lts.1",
    "twilio": "^5.3.3"
  },
  "devDependencies": {
    "@medusajs/test-utils": "2.11.4-snapshot-20251105174837",
    "@swc/core": "^1.7.28",
    "@swc/jest": "^0.2.36",
    "@types/jest": "^29.5.13",
    "@types/multer": "^1.4.12",
    "@types/node": "^20.12.11",
    "@types/react": "^18.3.2",
    "@types/react-dom": "^18.2.25",
    "jest": "^29.7.0",
    "prop-types": "^15.8.1",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "ts-node": "^10.9.2",
    "typescript": "^5.6.2",
    "vite": "^5.4.14",
    "yalc": "^1.0.0-pre.53"
  },
  "engines": {
    "node": ">=20"
  }
}
```


---
**@adrien2p** commented on 2025-11-11T16:41:33Z:

Weird, sounds like a translation thing issue. Not related but maybe something around that have been merged and broke 🤔 @willbouch does That ring a bell by any chance?


---
**@radeknapora** commented on 2025-11-11T16:46:39Z:

Hi @adrien2p I think this translation bug fix arrived after the snapshot was created #13986


---
**@carlos-r-l-rodrigues** commented on 2025-11-11T18:53:10Z:

You can use a preview version: `2.11.4-preview-20251111180137`


---
**@420coupe** commented on 2025-11-11T19:03:28Z:

> 2.11.4-preview-20251111180137

I was able to build, i'll run simulations now to see if i can re-produce ~~error~~ double/capture api issue. 


---
**@420coupe** commented on 2025-11-13T06:27:05Z:

> You can use a preview version: `2.11.4-preview-20251111180137`

ok to provide some feedback. In the simulations I have not been able to replicate the refund occurring however I do still see 2 capture attempts sent to stripe after the successful payment capture. This happens on every single transaction, see image below for 1 example. 

<img width="1848" height="337" alt="Image" src="https://github.com/user-attachments/assets/7d40c970-9126-4693-a461-931e5d575337" />


---
**@radeknapora** commented on 2025-11-13T09:16:58Z:

Okay guys. After digging deep into this and analyzing this and related issues #13837, #12790, I think I've found the root cause that connects all of them.

All three issues stem from the same architectural problem: Medusa creates orders AFTER the customer returns from payment, not when the webhook confirms payment. This makes webhooks unreliable and creates race conditions.

### How Medusa currently works
1. Customer confirms checkout
2. PaymentIntent created in Stripe
3. Customer redirected to payment provider
4. Payment succeeds in Stripe
5. Customer MUST return to store and trigger `/store/carts/:id/complete`
6. Only then: Order is created in Medusa

### Why this causes problems:
- If the customer closes the browser after payment → Payment captured, but no order created
- If the customer experiences network issues on redirect → Payment captured, but no order created
- Webhook arrives before frontend redirect → Race condition, double capture attempts
- Slower payment methods (SEPA, BLIK, bank transfers) → Authorization check fails before payment confirms

### How this connects to the other Issues
**Issue #12790**

> Stripe payment succeeded, funds were captured, but no order appeared in Medusa. Manually calling /store/carts/cart_xxx/complete created the order.

This is the smoking gun - the webhook isn't finalizing the order, only the frontend redirect is. When the customer doesn't return, the order is never created even though payment succeeded.

**Issue #13301 (double capture)**

> The stripe endpoint /capture is called twice... race conditions occur 1/20... leading to a refund after an order is successfully processed

This happens because BOTH the webhook AND the frontend complete route trigger the processPaymentWorkflow. The webhook fires first, then when the customer returns, /complete triggers it again → double capture.

**Issue #13837 (SEPA fails)**

The SEPA issue is a timing problem - Medusa checks authorization before the payment provider webhook confirms the payment (because SEPA takes longer). The current flow can't handle async payment methods reliably.

### How other platforms handle this

1. Customer confirms checkout → Create Order with status "pending"
2. Initialize PaymentIntent with order reference
3. Redirect to payment gateway
4. Payment provider sends webhook → Update order status to "paid"
5. Order exists regardless of whether customer returns

### Why This Works Better

- Webhook is the source of truth (not frontend navigation)
- Orders are never lost (even if customer doesn't return)
- No race conditions (webhook is the only trigger)
- Works with all payment methods (instant or delayed confirmation)
- Idempotent (same webhook can be processed multiple times safely)

### The Issue with current documentation
Looking at the [official Next.js Starter guide](https://docs.medusajs.com/resources/nextjs-starter/guides/customize-stripe), the implementation relies entirely on the frontend redirect:
```typescript
// app/api/capture-payment/[cartId]/route.ts
export async function GET(req: NextRequest, { params }: { params: Params }) {
  const { cartId } = await params
  
  // ❌ This only works if customer returns
  const order = await placeOrder(cartId)
  
  return NextResponse.redirect(
    `${origin}/${countryCode}/order/${order.id}/confirmed`
  )
}
```

### My Questions

- Was there a specific reason for creating orders after payment instead of before?
- Maybe I’m missing something about how this is supposed to work, but it seems these parts are very tightly coupled. Could you please clarify this if I’m wrong?

I'm running this in production and it's causing real issues - payments succeeding but orders sometimes disappearing, angry customers, manual reconciliation needed. I'm happy to help work on a fix.


---
**@adrien2p** commented on 2025-11-13T09:54:26Z:

> > You can use a preview version: `2.11.4-preview-20251111180137`
> 
> ok to provide some feedback. In the simulations I have not been able to replicate the refund occurring however I do still see 2 capture attempts sent to stripe after the successful payment capture. This happens on every single transaction, see image below for 1 example.
> 
> <img alt="Image" width="1848" height="337" src="https://private-user-images.githubusercontent.com/35115310/513714953-7d40c970-9126-4693-a461-931e5d575337.png?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NjMwMjc3OTcsIm5iZiI6MTc2MzAyNzQ5NywicGF0aCI6Ii8zNTExNTMxMC81MTM3MTQ5NTMtN2Q0MGM5NzAtOTEyNi00NjkzLWE0NjEtOTMxZTVkNTc1MzM3LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTExMTMlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUxMTEzVDA5NTEzN1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTBkZGRhYzA3MWM4MDU3ZDIwNDllNjBmNDUyMjA3OTRkNzE3MjRkN2M5ODI1N2MwZGQzY2NlYjQ4MWMzYThmOTUmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.acZcsoH8iWWLjB9EBNRPakVez2qPXiViVshYfKhjnyU">

Do you know what are the 400 response? maybe we can have some info there.
What I dont get here, is that we have put a lock, which means since redis is single threaded even if both arrives exactly at the same time, the two lock trying to be acquired will run one after each other. So, theoratically, only one process payment will run while the other one wait for the lock to be release. The second one when will be executed, will call the capture from the payment module service would end up not calling the stripe api because the session will be fully captured 🤔 cc @carlos-r-l-rodrigues 


---
**@420coupe** commented on 2025-11-13T17:41:24Z:

> > > You can use a preview version: `2.11.4-preview-20251111180137`
> > 
> > 
> > ok to provide some feedback. In the simulations I have not been able to replicate the refund occurring however I do still see 2 capture attempts sent to stripe after the successful payment capture. This happens on every single transaction, see image below for 1 example.
> > <img alt="Image" width="1848" height="337" src="https://private-user-images.githubusercontent.com/35115310/513714953-7d40c970-9126-4693-a461-931e5d575337.png?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NjMwMjc3OTcsIm5iZiI6MTc2MzAyNzQ5NywicGF0aCI6Ii8zNTExNTMxMC81MTM3MTQ5NTMtN2Q0MGM5NzAtOTEyNi00NjkzLWE0NjEtOTMxZTVkNTc1MzM3LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTExMTMlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUxMTEzVDA5NTEzN1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTBkZGRhYzA3MWM4MDU3ZDIwNDllNjBmNDUyMjA3OTRkNzE3MjRkN2M5ODI1N2MwZGQzY2NlYjQ4MWMzYThmOTUmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.acZcsoH8iWWLjB9EBNRPakVez2qPXiViVshYfKhjnyU">
> 
> Do you know what are the 400 response? maybe we can have some info there. What I dont get here, is that we have put a lock, which means since redis is single threaded even if both arrives exactly at the same time, the two lock trying to be acquired will run one after each other. So, theoratically, only one process payment will run while the other one wait for the lock to be release. The second one when will be executed, will call the capture from the payment module service would end up not calling the stripe api because the session will be fully captured 🤔 cc [@carlos-r-l-rodrigues](https://github.com/carlos-r-l-rodrigues)

Typically prior i was able to simulate by running ~100 simultaneous throttled checkouts with 2 step payments (cashapp/amazonpay), rarely was i ever able to get just cc to occur although it has, as well as express checkout which is unique to my instance. I'd usually have 1-5 have a race condition and revert/refund from what i suspect was the subsequent calls after to attempt to capture from the webhook endpoint. ( as described above by @radeknapora )

Here are the two different capture attempts, the 400 response is cannot be captured because it has already been captured. 


<img width="1872" height="624" alt="Image" src="https://github.com/user-attachments/assets/5e34f54d-e408-41ac-bc1c-db602c4b99bf" />

```json
{
  "error": {
    "code": "payment_intent_unexpected_state",
    "doc_url": "https://stripe.com/docs/error-codes/payment-intent-unexpected-state",
    "message": "This PaymentIntent could not be captured because it has already been captured.",
    "payment_intent": {
      "id": "pi_3SSttEK6QjZA3FWk0dslzmbC",
      "object": "payment_intent",
      "amount": 3000,
      "amount_capturable": 0,
      "amount_details": {
        "tip": {}
      },
      "amount_received": 3000,
      "application": null,
      "application_fee_amount": null,
      "automatic_payment_methods": {
        "allow_redirects": "always",
        "enabled": true
      },
      "canceled_at": null,
      "cancellation_reason": null,
      "capture_method": "automatic",
      "client_secret": "pi_3S**********************_******_*********************wWFt",
      "confirmation_method": "automatic",
      "created": 1763014816,
      "currency": "usd",
      "customer": null,
      "description": null,
      "excluded_payment_method_types": null,
      "invoice": null,
      "last_payment_error": null,
      "latest_charge": "py_3SSttEK6QjZA3FWk0VnKaa5y",
      "livemode": false,
      "metadata": {
        "session_id": "payses_01K9XXYCR6Q4JMZ908PN3JXFX3"
      },
      "next_action": null,
      "on_behalf_of": null,
      "payment_method": "pm_1SStuyK6QjZA3FWkjD77kZ5i",
      "payment_method_configuration_details": {
        "id": "pmc_1PoE5nK6QjZA3FWk3b502P3b",
        "parent": null
      },
      "payment_method_options": {
        "amazon_pay": {
          "express_checkout_element_session_id": null
        },
        "card": {
          "installments": null,
          "mandate_options": null,
          "network": null,
          "request_three_d_secure": "automatic"
        },
        "cashapp": {},
        "klarna": {
          "preferred_locale": null
        },
        "link": {
          "persistent_token": null
        }
      },
      "payment_method_types": [
        "card",
        "klarna",
        "link",
        "cashapp",
        "amazon_pay"
      ],
      "processing": null,
      "receipt_email": null,
      "review": null,
      "setup_future_usage": null,
      "shipping": null,
      "source": null,
      "statement_descriptor": null,
      "statement_descriptor_suffix": null,
      "status": "succeeded",
      "transfer_data": null,
      "transfer_group": null
    },
    "request_log_url": "https://dashboard.stripe.com/test/logs/req_kbSKkokOIuQ1EE?t=1763014953",
    "type": "invalid_request_error"
  }
}
```

<img width="1872" height="624" alt="Image" src="https://github.com/user-attachments/assets/ca9da741-4ace-4c2e-8cd7-835129948be8" />

```json
{
  "error": {
    "code": "payment_intent_unexpected_state",
    "doc_url": "https://stripe.com/docs/error-codes/payment-intent-unexpected-state",
    "message": "This PaymentIntent could not be captured because it has already been captured.",
    "payment_intent": {
      "id": "pi_3SSttEK6QjZA3FWk0dslzmbC",
      "object": "payment_intent",
      "amount": 3000,
      "amount_capturable": 0,
      "amount_details": {
        "tip": {}
      },
      "amount_received": 3000,
      "application": null,
      "application_fee_amount": null,
      "automatic_payment_methods": {
        "allow_redirects": "always",
        "enabled": true
      },
      "canceled_at": null,
      "cancellation_reason": null,
      "capture_method": "automatic",
      "client_secret": "pi_3S**********************_******_*********************wWFt",
      "confirmation_method": "automatic",
      "created": 1763014816,
      "currency": "usd",
      "customer": null,
      "description": null,
      "excluded_payment_method_types": null,
      "invoice": null,
      "last_payment_error": null,
      "latest_charge": "py_3SSttEK6QjZA3FWk0VnKaa5y",
      "livemode": false,
      "metadata": {
        "session_id": "payses_01K9XXYCR6Q4JMZ908PN3JXFX3"
      },
      "next_action": null,
      "on_behalf_of": null,
      "payment_method": "pm_1SStuyK6QjZA3FWkjD77kZ5i",
      "payment_method_configuration_details": {
        "id": "pmc_1PoE5nK6QjZA3FWk3b502P3b",
        "parent": null
      },
      "payment_method_options": {
        "amazon_pay": {
          "express_checkout_element_session_id": null
        },
        "card": {
          "installments": null,
          "mandate_options": null,
          "network": null,
          "request_three_d_secure": "automatic"
        },
        "cashapp": {},
        "klarna": {
          "preferred_locale": null
        },
        "link": {
          "persistent_token": null
        }
      },
      "payment_method_types": [
        "card",
        "klarna",
        "link",
        "cashapp",
        "amazon_pay"
      ],
      "processing": null,
      "receipt_email": null,
      "review": null,
      "setup_future_usage": null,
      "shipping": null,
      "source": null,
      "statement_descriptor": null,
      "statement_descriptor_suffix": null,
      "status": "succeeded",
      "transfer_data": null,
      "transfer_group": null
    },
    "request_log_url": "https://dashboard.stripe.com/test/logs/req_0h57gdQtzlFZxw?t=1763014958",
    "type": "invalid_request_error"
  }
}
```



---
