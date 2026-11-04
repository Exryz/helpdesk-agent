---
id: KB-002
title: VPN Cannot Connect or Shows a Certificate Error
category: Network
tags: [vpn, anyconnect, certificate, intune]
---

# VPN Cannot Connect or Shows a Certificate Error

## Quick Fix
Northwind Labs VPN (`vpn.northwind.example`) requires **Okta MFA + a machine certificate** issued by `Northwind Device CA` (valid 1 year, auto-renewed by Intune 30 days before expiry). Unmanaged personal devices are rejected.

If AnyConnect throws `Certificate Validation Failure`, `No valid certificates available for authentication`, or `Login failed`:

1. Sync your system clock (**Settings > Time & language > Date & time > Sync now**).
2. Force an Intune check-in: **Company Portal > Settings > Sync** (or **Settings > Accounts > Access work or school > Info > Sync**).
3. Wait ~15 minutes, reboot, and verify `certmgr.msc` (**Personal > Certificates**) has an unexpired `Northwind Device CA` cert.
4. Still failing? Open a ticket under **Network > VPN** at https://help.northwind.example (or call ext. **4357** if blocked from working).
