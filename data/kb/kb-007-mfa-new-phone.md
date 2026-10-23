---
id: KB-007
title: Moving MFA to a New Phone
category: Security
tags: [mfa, authenticator, new-phone, temporary-access-pass]
---

# Moving MFA to a New Phone

## Overview
Microsoft Authenticator is tied to your physical phone. When you replace, reset or lose your phone, you need to move your Northwind MFA registration. How you do it depends on whether you still have the **old phone**.

## Option A: You still have your old phone (recommended)
1. Install Microsoft Authenticator on the new phone.
2. On a computer, go to **https://aka.ms/mysecurityinfo** and sign in (approve the prompt on the **old** phone).
3. Click **+ Add sign-in method > Authenticator app** and scan the QR code with the **new** phone.
4. Test the new phone, set it as the **default sign-in method**, then click **Delete** next to the old phone's entry.
5. Only then wipe or trade in the old phone.

## Option B: Restore from cloud backup
If you had **Cloud backup** turned on (iCloud for iPhone, Microsoft personal account for Android), open Authenticator on the new phone and tap **Begin recovery**. Work accounts restored from backup still require re-verification: tap the Northwind account and follow the prompt to sign in again.

## Option C: You no longer have the old phone
1. Call the IT hotline at local **4357** (or open a ticket from a colleague's computer at https://help.northwind.example under **Accounts & Access > MFA**).
2. IT verifies your identity by **video call with your photo ID**, or through your manager confirming in person.
3. IT issues a **Temporary Access Pass (TAP)**: a one-time code valid for **8 hours**.
4. Go to https://aka.ms/mysecurityinfo, sign in using the TAP, and register the new phone as in KB-006.
5. IT removes the old phone from your account.

If the old phone was lost or stolen, also follow KB-023.

## Important notes
- Plan ahead: complete Option A **before** you hand in or factory-reset your old phone.
- A user who cannot sign in at all because of MFA is handled as **P2 (High)** priority.
- Phone number changes for SMS backup can be updated in the same Security info page.
