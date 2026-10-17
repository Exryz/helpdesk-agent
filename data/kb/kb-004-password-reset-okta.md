---
id: KB-004
title: Resetting Your Password with Okta Self-Service
category: Accounts & Access
tags: [password, okta, self-service, sso]
---

# Resetting Your Password with Okta Self-Service

## Overview
Your Northwind Labs password is managed by **Okta** and is used for Windows sign-in, Microsoft 365, VPN and all single sign-on (SSO) apps. You can reset it yourself at any time without contacting IT.

## Password rules
- Minimum length of **14 characters**.
- Must include at least three of: uppercase, lowercase, numbers, symbols.
- Cannot reuse any of your **last 10 passwords**.
- Cannot contain your name or username.
- Passwords expire every **90 days**. Okta emails you a reminder **14 days** before expiry.

## Resolution steps: forgot or expired password
1. Go to **https://northwind.okta.com** from any browser (phone or another computer works too).
2. Click **Need help signing in?** and then **Forgot password?**.
3. Enter your username (firstname.lastname) and choose **Reset via Okta Verify / Microsoft Authenticator push** or **Reset via SMS**.
4. Approve the verification, then enter and confirm your new password.
5. On your laptop, if you are on the office network or connected to VPN, lock the screen (**Win + L**) and sign in with the new password. If you are remote and off VPN, sign in with your **old** password, connect to VPN, then lock and unlock with the new password so Windows caches it.

## Changing a password that has not expired
Sign in to https://northwind.okta.com, click your name in the top right, choose **Settings**, and under **Change Password** enter your current and new password.

## After changing your password
- Update the password on your phone's Outlook and Teams apps if prompted.
- It can take up to **15 minutes** for the new password to sync to all systems.

## When to contact IT
If self-service reset fails because you have no MFA method enrolled or you no longer have your phone, call the IT hotline at local **4357**. The technician will verify your identity via a video call with your photo ID before resetting your password. IT will never ask you for your password.
