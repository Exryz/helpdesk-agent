---
id: KB-002
title: VPN Cannot Connect or Shows a Certificate Error
category: Network
tags: [vpn, anyconnect, certificate, intune]
---

# VPN Cannot Connect or Shows a Certificate Error

## Symptoms
- AnyConnect shows "Certificate Validation Failure" or "No valid certificates available for authentication".
- AnyConnect shows "Login failed" even though your Okta password is correct.
- The connection never completes and stays on "Contacting vpn.northwind.example".

## Cause
The Northwind Labs VPN requires two things: your Okta credentials with MFA, **and** a device certificate issued by the **Northwind Device CA**. The device certificate is installed automatically by Intune and is valid for **1 year**; it renews automatically 30 days before expiry, but only if the laptop checks in with Intune. Laptops that have been offline for a long time, have an incorrect system clock, or are personal (unmanaged) devices will fail certificate validation. Personal devices are not permitted to use the VPN.

## Resolution steps
1. Check that the server address in AnyConnect is exactly `vpn.northwind.example`.
2. Verify the date, time and time zone: **Settings > Time & language > Date & time**, turn on **Set time automatically**, then click **Sync now**. A wrong clock makes valid certificates appear invalid.
3. Force an Intune sync to renew the certificate: open **Company Portal**, click **Settings**, then **Sync**. Alternatively go to **Settings > Accounts > Access work or school**, select your Northwind account, click **Info**, then **Sync**.
4. Wait 15 minutes, restart the laptop, and try again.
5. To confirm the certificate is present, press **Win + R**, type `certmgr.msc`, open **Personal > Certificates** and look for a certificate issued by **Northwind Device CA** with a future expiry date.
6. If you get "Login failed", make sure your password has not expired (see KB-004) and that you approve the MFA prompt in Microsoft Authenticator within 60 seconds.

## When to contact IT
If the certificate is missing or expired after an Intune sync and restart, open a ticket at https://help.northwind.example under **Network > VPN** and include a screenshot of the error. Because certificate re-issue requires a technician, mark it as urgent if you are unable to work, or call local **4357**.
