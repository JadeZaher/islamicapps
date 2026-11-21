---
title: Free Plan
description: Railway's Free plan, and the 30-day trial every new account starts on.
---
The Free plan is Railway's $0 plan: $1 of resource usage each month, no credit card, services that sleep when idle. New accounts start with a 30-day [trial](#trial) that has higher limits and a one-time $5 grant, then continue on the Free plan. This page covers both.

## Free plan

Every workspace can run on the Free plan. It costs $0 a month, includes $1 of resource usage each month, and needs no credit card. The $1 resets every billing cycle and does not roll over.

**What's included**

- 1 project with up to 3 services, each up to 1 vCPU and 0.5 GB RAM
- Postgres, Redis, MySQL, MongoDB, and more as single-node [databases](/databases). High-availability clusters start on Hobby
- 1 volume (0.5 GB) and 1 [bucket](/storage-buckets) (10 GB)
- A `*.up.railway.app` domain per service, private networking, and community support

**How Free services run**

Services on the Free plan run [serverless](/deployments/serverless). A service sleeps after 5 to 10 minutes without outbound traffic and wakes on the next request. A sleeping service incurs no compute charges. Databases sleep the same way, wake on the next connection, and keep their data. Sleep is triggered by outbound inactivity, not by missing inbound traffic, so a service that keeps sending traffic stays awake: a bot holding a WebSocket, a worker polling a queue, or a service with an open database connection. Railway picks the region for services without a volume.

**How the $1 is spent**

The $1 covers CPU, RAM, egress, and volume storage at the [standard rates](/pricing/plans#resource-usage-pricing), billed by the minute while a service is awake. On its own, $1 buys about a month of any one of these. Real usage draws from all of them at once.

| Resource | What $1 covers for a month |
| --- | --- |
| RAM | 100 MB, around the clock |
| CPU | 0.05 vCPU, around the clock |
| Egress | 20 GB |

When the $1 runs out, your services stop until the next billing cycle or until you upgrade. Volumes and bucket files are kept.

### Free vs Trial

New accounts also get a 30-day [Trial](#trial) with higher limits. The Trial is a one-time boost, not a plan.

| | Free | Trial |
| --- | --- | --- |
| Credit | $1 every month | $5 once, for 30 days |
| Credit card | Not required | Not required |
| Services sleep when idle | Yes | No |
| Custom domains, cron jobs, region choice | No | Yes |
| What happens after | Continues every month | Switch to Free or upgrade |

To run services always-on, pick a region, or use custom domains and cron jobs, upgrade to [Hobby](/pricing/plans#plans): $5 a month with $5 of usage included, for up to 50 services per project.

### Free plan FAQs

#### Is the Free plan really free?

Yes. There is no subscription fee and no credit card. You get $1 of resource usage each month for your services and one-click databases, and when it is used up your services stop until the next cycle. See [Free plan](#free-plan).

#### Is the $1 one-time or monthly?

Monthly. It resets every billing cycle and does not roll over. The one-time $5 is the [Trial](#trial) grant for new accounts.

#### Do Free plan services sleep?

Yes. Free plan services run [serverless](/deployments/serverless): they sleep after 5 to 10 minutes without outbound traffic and wake on the next request. A service that keeps sending traffic, such as a bot with an open WebSocket or a worker polling a queue, stays awake. Hobby runs services always-on for $5 a month.

#### Can I run a database for free?

Yes. Postgres, Redis, MySQL, and MongoDB deploy in one click on the Free plan as single-node databases with a 0.5 GB volume. They sleep when idle and wake on the next connection.

#### Does bandwidth count against the $1?

Yes. Network egress is billed at $0.05 per GB and draws from the same $1 as CPU, RAM, and volume storage.

## Trial

New accounts start with a 30-day trial on top of the [Free plan](#free-plan), with higher limits and a one-time grant of $5.

After 30 days pass or the $5 is spent, the trial ends and your services stop. Switch to the Free plan from the [Plans page](https://railway.com/workspace/plans) or upgrade to Hobby, then redeploy. The Free plan's $1 does not roll over month to month.

### Try without an account

You can try Railway before signing up. Run `ssh railway.new` to get a free Linux VM with coding agents preinstalled and a preview URL, with no account or credit card. Railway identifies you by your SSH key.

| Limit        | Value                        |
| ------------ | ---------------------------- |
| VM size      | 2 vCPU, 2 GB RAM             |
| Build time   | 60 minutes                   |
| Claim window | 24 hours                     |
| Boxes        | 3 per IP address per day     |

Compute for an unclaimed box is free. To keep it, open the claim link from the welcome message and sign up; the box moves into your account with the same VM, files, and URL. Unclaimed boxes are deleted with their files. See [railway.com/free-vm](https://railway.com/free-vm) for more.

When demand is high, Railway caps how many free VMs run at once in each region. If you hit the cap, you'll see "Anonymous trials are temporarily disabled. Try again shortly, or sign up to keep building." That attempt doesn't count against your daily limit.

### Full VS limited trial

Your trial experience depends on whether Railway can verify your account.

| Trial Type        | Deploy Code | Deploy Databases | Deploy Buckets | Network Access |
| ----------------- | ----------- | ---------------- | -------------- | -------------- |
| **Full Trial**    | ✅          | ✅               | ✅             | Full           |
| **Limited Trial** | ✅          | ✅               | ✅             | Restricted     |

When you sign up for a free Trial, you can connect your GitHub account to initiate verification. Your verification status depends on a number of factors, including the age and activity of your GitHub account.

If your account is not verified (either because you have not initiated the verification process or your account does not meet Railway's criteria for verification), your trial will have some network restrictions. Specifically, services on the Limited Trial have restricted outbound network access and only a limited set of ports are available.

Verification is a necessary measure to prevent abuse of the free Trial, limiting users from creating multiple accounts and reducing the risk of trial users deploying or hosting content that violates Railway's [Terms of Service](https://railway.com/legal/fair-use).

This is a fully automated process, and Railway does not respond to requests for verification. If your account is not verified, you can upgrade to the Hobby plan to unlock the full Railway experience.

### Trial FAQs

#### How do I get started with the free trial?

If you do not already have a Railway account, you can sign up for a free Trial by clicking "Login" at [railway.com](https://railway.com/).

#### How does the trial work?

When you sign up for the free Trial, you will receive a one-time grant of $5 in credits that you can use to try out Railway. The credits will be applied towards any usage on the platform and expire in 30 days.

If you upgrade to a plan while you still have a credit balance from the Trial, the remaining balance will carry over to your new plan. To prevent fraud and ensure your payment method is valid and in good standing, the carried-over Trial credits may not be applied to your first billing cycle, and will instead be applied as a discount to subsequent charges once a successful payment has been processed.

#### What resources can I access during the trial?

During the trial, you can access the same features as on the Hobby plan, however you will be limited to 1 GB of RAM and shared (rather than dedicated) vCPU cores. Additionally, your projects will be limited to 5 services per project.

As a trial user, you can spin up databases and deploy code. However, if you are on the [Limited Trial](#full-vs-limited-trial), your services will have some network restrictions.

#### What's the difference between the limited trial and the full trial?

If you connect your GitHub account, and we are able to verify it against a set of parameters, you will be on the Full Trial with full network access.

If you do not connect a GitHub account, or we are not able to verify your account, you will be on the Limited Trial. You can still deploy code, databases, and buckets, but your services will have restricted outbound network access and only a limited set of ports will be available.

While you're on the Limited Trial, you can initiate verification at any time by visiting [railway.com/verify](https://railway.com/verify) in order to access the Full Trial experience.

#### How far will the $5 one-time trial grant last?

The longevity of your one-time trial grant depends on how many resources you consume within the 30 day period you sign-up for the platform. The more resources you deploy, the greater the consumption.

#### Data retention

Railway deletes stateful volumes created by Trial accounts 30 days after the expiration of your credits. To retain your data, upgrade your account after the Trial period.