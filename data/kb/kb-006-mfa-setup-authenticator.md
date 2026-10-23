---
id: KB-006
title: Setting Up MFA with Microsoft Authenticator
category: Security
tags: [mfa, authenticator, 2fa, security]
---

# Setting Up MFA with Microsoft Authenticator

## Overview
Multi-factor authentication (MFA) is **mandatory** for all Northwind Labs accounts. The approved method is the **Microsoft Authenticator** app with number matching. SMS is allowed only as a backup method. New employees must enroll within **14 days** of their start date; after that, sign-in is blocked until MFA is registered.

## Requirements
- A smartphone running iOS 16+ or Android 10+.
- Microsoft Authenticator installed from the Apple App Store or Google Play (publisher: Microsoft Corporation).
- A computer where you can sign in to your Northwind account.

## Resolution steps: first-time setup
1. On your computer, go to **https://aka.ms/mysecurityinfo** and sign in with your Northwind account.
2. Click **+ Add sign-in method**, select **Authenticator app**, then click **Add**.
3. On your phone, open Microsoft Authenticator, tap **+**, then **Work or school account > Scan QR code**.
4. Scan the QR code displayed on your computer and click **Next**.
5. A test notification is sent. Enter the **two-digit number** shown on your computer into the app and tap **Yes**.
6. Back on the Security info page, click **Set default sign-in method** and choose **Microsoft Authenticator - notification**.
7. Optionally add your phone number as a backup SMS method.

## Tips
- Turn on **Cloud backup** in Authenticator (**Settings > Backup**) so you can restore accounts on a new phone (see KB-007).
- Enable notifications for the Authenticator app, otherwise prompts will not appear.
- Approve prompts within **60 seconds**, or they expire.
- **Never approve a prompt you did not initiate.** If you receive unexpected MFA prompts, tap **No, it's not me** and report it to the Security team via local 4357 immediately - this may mean your password is compromised.

## When to contact IT
Open a ticket at https://help.northwind.example under **Accounts & Access > MFA** if you do not have a compatible smartphone; IT can issue a FIDO2 hardware security key instead.
