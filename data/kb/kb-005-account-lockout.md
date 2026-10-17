---
id: KB-005
title: Account Locked Out
category: Accounts & Access
tags: [lockout, okta, password, account]
---

# Account Locked Out

## Symptoms
- Okta displays "Your account is locked. Please contact your administrator" or "Account locked".
- Windows shows "The referenced account is currently locked out and may not be logged on to".
- Outlook and Teams keep asking for your password.

## Cause
For security, your account is locked automatically after **5 failed sign-in attempts within 10 minutes**. The lockout lasts **15 minutes** and then clears automatically. The most common causes are:
- Typing an old password after a recent password change.
- A phone or tablet with an old password saved in the Mail, Outlook or Teams app that keeps retrying in the background.
- A mapped drive or saved credential in **Credential Manager** using an old password.

## Resolution steps
1. **Wait 15 minutes** and then sign in carefully with your current password. Check Caps Lock.
2. Or unlock immediately yourself: go to **https://northwind.okta.com**, click **Need help signing in?**, then **Unlock account?**, enter your username and approve the Microsoft Authenticator push or SMS code.
3. If you recently changed your password, update it on every mobile device (Outlook, Teams, Mail apps). If you cannot find which device is causing it, temporarily turn off Wi-Fi and mobile data on your phone.
4. Clear old saved credentials: open **Control Panel > Credential Manager > Windows Credentials** and remove entries referencing `northwind` or `MicrosoftOffice`.
5. If your password has expired, reset it with Okta self-service (see KB-004).

## Repeated lockouts
If you are locked out more than **3 times in one day**, the Security team is automatically notified because this may indicate someone attempting to guess your password. You may be contacted to confirm the activity.

## When to contact IT
Call local **4357** if you are still locked out after the self-service unlock, or if you do not have access to your MFA device. A locked-out user who cannot work is treated as **P2 (High)** priority. Tickets can also be opened at https://help.northwind.example from a colleague's computer.
