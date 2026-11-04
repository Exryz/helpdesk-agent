---
id: KB-005
title: Account Locked Out
category: Accounts & Access
tags: [lockout, okta, password, account]
---

# Account Locked Out

## Policy Summary
Accounts lock automatically after **5 failed sign-in attempts within 10 minutes**. Lockouts clear automatically after **15 minutes**, or you can self-unlock immediately via **https://northwind.okta.com** (**Need help signing in? > Unlock account?**) using Microsoft Authenticator push or SMS.

## Stopping Repeated Lockouts
Usually caused by a phone/tablet retrying an old password in Outlook/Teams/Mail after a password reset, or a stale entry in Windows Credential Manager:
- Update your password on all mobile apps (or toggle Airplane Mode while isolating which device is locking you out).
- Clear saved entries under **Control Panel > Credential Manager > Windows Credentials** (`northwind` / `MicrosoftOffice`).
- Note: >3 lockouts in 24 hours alerts the Security team. If you cannot self-unlock or lost your MFA phone, call ext. **4357** (**P2 High** priority).
