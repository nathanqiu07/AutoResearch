---
source: https://github.com/medusajs/medusa/issues/6254
retrieved: 2026-11-15
license: public GitHub issue (GitHub Terms of Service); repository license NOASSERTION
---

# Stripe webhook failures  (#6254, closed)

opened by @BorisKamp on 2024-01-29T10:59:44Z  labels: type: bug, Stale

Running `medusa` `1.20.0` and `medusa-payment-stripe` `6.0.7` Im having all my webhooks fail.
In Stripe dashboard, all the webhooks return a `400` with the following message:

```
Webhook Error: Webhook payload must be provided as a string or a Buffer (https://nodejs.org/api/buffer.html) instance representing the _raw_ request body.Payload was provided as a parsed JavaScript object instead. 
Signature verification is impossible without access to the original signed material. 
Learn more about webhook signing and explore webhook integration examples for various frameworks at https://github.com/stripe/stripe-node#webhook-signing
```

I read this:
https://medusajs.com/changelog/#v1.20.0

But have no clue what I need to do, I cannot find that anywhere in the text.

Am I missing something here?

I find it pretty disturbing that this happens, now payments do not work basically...


---
**@olivermrbl** commented on 2024-01-29T11:49:16Z:

It seems your webhook parses the request payload incorrectly, so the raw `body-parser` middleware is likely not registered properly on the route.

I was unable to reproduce your issue in a fresh project. Are you able to provide a reproduction of the issue? Would make it easier to debug.

Also, can I get you to ensure all your Medusa packages are updated? 



---
**@BorisKamp** commented on 2024-01-29T12:30:59Z:

Thank you for your reply @olivermrbl
I have no custom code for the stripe functionality.

I have setop local webhooks with Stripe using this:
https://stripe.com/docs/webhooks#test-webhook

And can reproduce it locally now.

What do I need to do, do you want access to my MedusaJS repo? Can you test it without the frontend?



---
**@olivermrbl** commented on 2024-01-29T12:33:33Z:

If you are OK with giving me access, that would definitely be the most straightforward approach.

I'll spin up our own storefront and test it out.


---
**@BorisKamp** commented on 2024-01-29T12:34:44Z:

> If you are OK with giving me access, that would definitely be the most straightforward approach.
> 
> I'll spin up our own storefront and test it out.

Sure, it's a gitlab repo, what e-mail can I use to invite you?


---
**@olivermrbl** commented on 2024-01-29T12:35:19Z:

`oli@medusajs.com` :)


---
**@BorisKamp** commented on 2024-01-29T12:37:33Z:

> `oli@medusajs.com` :)

Done, can you access it?


---
**@BorisKamp** commented on 2024-01-29T14:05:13Z:

Downgrading does not help because of the `SearchUtils.isSearchService` bug.
I appreciate the help but this is quite urgent )-:


---
**@BorisKamp** commented on 2024-01-30T10:24:08Z:

@olivermrbl I have customer paying for orders now and the carts are not converted to orders because of the webhook issue.

Can I manually complete the carts as a workaround for now?


---
**@BorisKamp** commented on 2024-01-30T13:10:16Z:

@adrien2p tagging you since Oli seems to have other stuff on his mind (understandable, no offence).


---
**@olivermrbl** commented on 2024-01-31T08:14:07Z:

> > `oli@medusajs.com` :)
> 
> Done, can you access it?

I can't sign in to get access no. Can you try resending the invite?


---
**@BorisKamp** commented on 2024-01-31T09:09:38Z:

> I can't sign in to get access no. Can you try resending the invite?

See your mail, I've manually set the pw for you,


---
**@dasherzx** commented on 2024-02-05T07:26:43Z:

same issue. whats the workaround (if there's one)


---
**@BorisKamp** commented on 2024-02-05T08:22:32Z:

> same issue. whats the workaround (if there's one)

Well Im glad I'm not the only one anymore @olivermrbl 

@dasherzx What Im doing for now is manually calling the `{{medusa-host}}/store/carts/:cartId/complete` endpoint on the cart when I see the payment is successful (can see that in Stripe). It should then follow the usual flow again. Annoying but it is a temporary workaround...


---
**@BorisKamp** commented on 2024-02-07T07:47:06Z:

Here's a detailled step by step of what im doing (and be aware, I changed nothing, everything used to work for about half a year and it suddenly stopped working):
1. I make sure I use the correct webhook secret, let me show you some screenshots, the stripe localhost webhook setup:
![unnamed](https://github.com/medusajs/medusa/assets/8350740/5912ce6c-297f-46e8-b943-c2f19902fa4e)

2. I use that webhook secret in Medusa .env file:
![unnamed (1)](https://github.com/medusajs/medusa/assets/8350740/450a43f2-c3af-43ed-b98c-e301501bfb6b)

3. Medusa config file:
![unnamed (2)](https://github.com/medusajs/medusa/assets/8350740/59a00e57-3f74-402b-b779-ae462ed86338)

4. And I still have a 400, I see the webhook incoming in the terminal:
![unnamed (3)](https://github.com/medusajs/medusa/assets/8350740/f53d697b-590c-44ce-955f-525aab8eb04b)

5. In stripe the local listener is setup correctly (well duh, otherwise the webhook would'nt be shown in the medus terminal)
![unnamed (4)](https://github.com/medusajs/medusa/assets/8350740/23be4298-11b1-41c2-ab5c-d2707073e64e)

6. The webhook shown in stripe, with the 400 and the same response body as I told in the issue (first comment).
![unnamed (5)](https://github.com/medusajs/medusa/assets/8350740/bb8cf85c-117d-46b3-8cf1-0f285c7e8d02)

Is there a way I can debug the incoming webhook in MedusaJS so we can investigate further?

Mentioning @adrien2p as he's helped me before and I get no solutions yet and this is breaking, sorry!
Adrien, Oli has access to my medusa gitlab project, if you need access, let me know.




---
**@adrien2p** commented on 2024-02-08T08:33:14Z:

@BorisKamp, in order to debug this one, you should put BP or log in the stripe plugin web hook end point, theoratically this one expect a raw body and not a parsed one.


---
**@dadebulba** commented on 2024-02-12T09:25:08Z:

Same issue here, we changed nothing, and suddenly Stripe webhooks started failing last week, we have paying customers so this is critical also for us.
@BorisKamp did you manage to find a solution?


---
**@olivermrbl** commented on 2024-02-12T09:31:28Z:

@dadebulba, can you provide a reproduction?


---
**@dadebulba** commented on 2024-02-12T10:21:06Z:

I managed to solve the issue, although I don't understand why my code was causing it.
In the `src/api/index.ts` file I put this custom route:

```
const customRouter = Router()
  customRouter.post("/admin/validatetoken", [cors(adminCors), express.json(), express.urlencoded({ extended: true })], async (req, res) => {
    const encryptedData = Buffer.from(req.body.token as string, 'hex')
    const publicKey = process.env.MEDUSA_PUBLIC_KEY.replace(/\\n/g, '\n')
    try {
      const decryptedData = publicDecrypt(
        publicKey,
        encryptedData
      );
      if (decryptedData) {
        const userService = req.scope.resolve("userService") as UserService
        const user = await userService.retrieveByApiToken(decryptedData.toString('utf-8'))
        req.scope.register({
          loggedInUser: {
            resolve: () => user,
          },
          clientOS: {
            resolve: () => extractOs(req)
          }
        })
        const mixpanelTracking = req.scope.resolve("mixpanelTrackingService") as MixpanelTrackingService
        await mixpanelTracking.identify()
        await mixpanelTracking.adminPageVisit()
      }
      res.send(decryptedData.toString('utf-8'));
    }
    catch (err) {
      console.log(err)
      res.status(400).send(err)
    }
  })
```

By removing the `console.log(err)`, the webhook started accepting incoming events and reply 200 to stripe. I don't know why.

I'm using  "@medusajs/medusa": "^1.19.0" and "medusa-payment-stripe": "^6.0.2"


---
**@KabyleBOT** commented on 2024-03-28T11:40:36Z:

I am having the same issue here !

Is there a solution ?


---
**@scrlkx** commented on 2024-04-07T23:17:13Z:

I was facing the same issue and I just noticed that I was using the Webhook ID instead of the Signing Secret. Maybe it's not the case for you guys, but going trough the documentation again can be a good idea as Stripe's UI can be a little bit confusing.

> After the Webhook is created, you’ll see "Signing secret" in the Webhook details. Click on "Reveal" to reveal the secret key. Copy that key and in your Medusa backend add the Webhook secret environment variable: 

https://docs.medusajs.com/plugins/payment/stripe#retrieve-stripes-keys


---
**@rickylabs** commented on 2024-04-16T11:58:17Z:

Same issue with latest Stripe API and Medusa packages. 
Error trigger when using test secret key and test webhook secret..
Multiple people are reporting the same issue you should investigate what's happening it is potentially blocking orders for some !

Why does medusa-stripe-pluigin still rely on stripe ^11.10.0 node package ? Current major is 15 !

https://github.com/medusajs/medusa/blob/develop/packages/medusa-payment-stripe/package.json#L56


---
**@KabyleBOT** commented on 2024-04-16T12:57:03Z:

I am struggling with this issue and tried all possible solutions without results. I suspect api Versions miss match between stripe hook and nodejs configuration in the plug-in. 


---
**@rickylabs** commented on 2024-04-16T13:24:43Z:

https://github.com/medusajs/medusa/blob/develop/packages/medusa-payment-stripe/src/core/stripe-base.ts#L33C1-L39C4

According to the version used by medusa plugin it support apiVersion: "2022-11-15". Does that mean that current Stripe version ([2024-04-10](https://docs.stripe.com/upgrades#2024-04-10)) isn't supported ?


---
**@KabyleBOT** commented on 2024-04-16T13:27:16Z:

It's what I am suspecting. But I am not sure. I am investigating this right after some other urgent issues in my backlog. In my webapp the order is created even if the webhook is failing 


---
**@rickylabs** commented on 2024-04-16T13:42:22Z:

After some research I came upon this: https://stackoverflow.com/a/78168323

I also found that Medusa Team has improved the handling of webhook for V2 API that implement the same changes: 

https://github.com/medusajs/medusa/blob/34c893a37ddaf0c0486bab8b206e8f3c1045ac48/packages/medusa/src/api-v2/hooks/middlewares.ts#L6

More likely this part seems the reason why we're getting error that seems fixed in v2 :

https://github.com/medusajs/medusa/blob/34c893a37ddaf0c0486bab8b206e8f3c1045ac48/packages/payment-stripe/src/core/stripe-base.ts#L357C3-L365C4

Now the question for @olivermrbl : Does Medusa team could backport these modifications to current stripe plugin more precisely the route handler: https://github.com/medusajs/medusa/blob/develop/packages/medusa-payment-stripe/src/api/stripe/hooks/route.ts ?


---
**@KabyleBOT** commented on 2024-04-16T16:46:24Z:

Exactly I saw this and I was wondering how can we use it to replace the actual plug-in 


---
**@rickylabs** commented on 2024-04-16T16:55:33Z:

> Exactly I saw this and I was wondering how can we use it to replace the actual plug-in

As a workaround you could create your own endpoint and wrap it in it's own Middleware like so: https://docs.medusajs.com/development/api-routes/create#parse-webhook-body-parameters

And setup your webhook to listen to this new endpoint. As long as rawbody is preserved you shouldn't have any issue with webhook validation.

My point is that medusa team should upgrade the current API route for stripe webhook like they did for the V2 API 

Update: 

Here is how to resolve the Webhook issue (worked for me) if you're still using Express API Route System

1. Create a new route pattern to handle your /stripe/* API routes: 
```typescript
  const stripeCors = {
    origin: "*", //list of FQDN from Stripe if you want to restrict domains: https://docs.stripe.com/ips#stripe-domains
    credentials: false,
    methods: "GET,HEAD,PUT,PATCH,POST,DELETE,OPTIONS",
  };
  const stripeRoutePattern = /^\/stripe\/.*/;
  stripePublicRouter(router, stripeCors);
```
2. In your Stripe router ensure that rawBody is preserved
```typescript
import { Router, json, urlencoded } from "express" //important: do not use "body-parser" if your express pckg is above 4.16.x
import { wrapHandler } from "@medusajs/utils";
import { MedusaRequest, MedusaResponse } from "@medusajs/medusa";

export function stripePublicRouter(stripeRouter, stripeCorsOptions): Router {
  stripeRouter.use(
    cors(stripeCorsOptions), 
    json({
      verify: (req: MedusaRequest, res: MedusaResponse, buf: Buffer) => {
      req.rawBody = buf
    }}),
    urlencoded({ extended: true }),
  )

  stripeRouter.post(
    "/stripe/events",
    wrapHandler(YOUR_STRIPE_API_ROUTE_HANDLER)
  )

  return stripeRouter
}
```
3. Create a new endpoint to receive your webhooks
```typescript
import { MedusaRequest, MedusaResponse } from "@medusajs/medusa"
import StripeProviderService from "medusa-payment-stripe/dist/services/stripe-provider"
import { constructWebhook } from "medusa-payment-stripe/dist/api/utils/utils"

type SerializedBuffer = {
  data: ArrayBuffer
  type: "Buffer"
}

export const POST = async (req: MedusaRequest, res: MedusaResponse) => {
  try {
    const pluginOptions = req.scope.resolve<StripeProviderService>(
      "stripeProviderService"
    ).options

    let rawData = req.rawBody
    if ((rawData as unknown as SerializedBuffer).type === "Buffer") {
      rawData = Buffer.from((rawData as unknown as SerializedBuffer).data)
    }

    const event = constructWebhook({
      signature: req.headers["stripe-signature"],
      body: rawData,
      container: req.scope,
    })

    const eventBus = req.scope.resolve("eventBusService")

    // we delay the processing of the event to avoid a conflict caused by a race condition
    await eventBus.emit("medusa.stripe_payment_intent_update", event, {
      delay: pluginOptions.webhook_delay || 5000,
      attempts: pluginOptions.webhook_retries || 3,
    })
  } catch (err) {
    res.status(400).send(`Webhook Error: ${err.message}`)
    return
  }

  res.sendStatus(200)
}

```

That way Webhook payload from Stripe will be preserved and hopefully it should avoid issue to many of you !


---
**@rickylabs** commented on 2024-04-17T15:03:11Z:

Please do not close this issue as the Stripe Plugin is still not implementing the solution introduced in V2


---
**@jeeinog** commented on 2024-08-17T22:11:15Z:

In the end, did you manage to solve the problem?
It took me a while to solve it, but in practice, literally the only thing I did was move my router from /WebHook before the app.use(express.json) middleware


---
**@gianpieropa** commented on 2024-09-09T10:20:31Z:

i still have this error, how can i solve?


---
**@paradox1612** commented on 2024-09-09T22:43:14Z:

i still have this issue, how can i  solve? 



---
**@gianpieropa** commented on 2024-09-10T07:19:48Z:

Hi i solved the issue placing a file middlewares.ts in /src/api/ with this content:
```
import { MiddlewaresConfig } from "@medusajs/medusa";
import { raw } from "body-parser";

export const config: MiddlewaresConfig = {
  routes: [
    {
      matcher: "/stripe/hooks",
      bodyParser: false,
      middlewares: [raw({ type: "application/json" })],
    },
    {
      matcher: "/paypal/hooks",
      bodyParser: false,
      middlewares: [raw({ type: "application/json" })],
    },
  ],
};

```


---
**@Koushith** commented on 2024-10-25T18:22:58Z:

> I managed to solve the issue, although I don't understand why my code was causing it. In the `src/api/index.ts` file I put this custom route:
> 
> ```
> const customRouter = Router()
>   customRouter.post("/admin/validatetoken", [cors(adminCors), express.json(), express.urlencoded({ extended: true })], async (req, res) => {
>     const encryptedData = Buffer.from(req.body.token as string, 'hex')
>     const publicKey = process.env.MEDUSA_PUBLIC_KEY.replace(/\\n/g, '\n')
>     try {
>       const decryptedData = publicDecrypt(
>         publicKey,
>         encryptedData
>       );
>       if (decryptedData) {
>         const userService = req.scope.resolve("userService") as UserService
>         const user = await userService.retrieveByApiToken(decryptedData.toString('utf-8'))
>         req.scope.register({
>           loggedInUser: {
>             resolve: () => user,
>           },
>           clientOS: {
>             resolve: () => extractOs(req)
>           }
>         })
>         const mixpanelTracking = req.scope.resolve("mixpanelTrackingService") as MixpanelTrackingService
>         await mixpanelTracking.identify()
>         await mixpanelTracking.adminPageVisit()
>       }
>       res.send(decryptedData.toString('utf-8'));
>     }
>     catch (err) {
>       console.log(err)
>       res.status(400).send(err)
>     }
>   })
> ```
> 
> By removing the `console.log(err)`, the webhook started accepting incoming events and reply 200 to stripe. I don't know why.
> 
> I'm using "@medusajs/medusa": "^1.19.0" and "medusa-payment-stripe": "^6.0.2"

- Thank you. it's pretty wierd, but removing logs from catch block worked.


---
**@github-actions[bot]** commented on 2024-11-26T02:02:52Z:

This issue is stale because it has been open 30 days with no activity. Remove stale label or comment or this will be closed in 3 days.


---
**@github-actions[bot]** commented on 2024-11-29T02:03:49Z:

This issue was closed because it has been stalled for 3 days with no activity.

