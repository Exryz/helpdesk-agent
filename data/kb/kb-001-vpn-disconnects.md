---
id: KB-001
title: VPN Keeps Disconnecting (Cisco AnyConnect)
category: Network
tags: [vpn, anyconnect, remote-work, disconnect]
---

# VPN Keeps Disconnecting (Cisco AnyConnect)

## Symptoms
- Cisco AnyConnect connects to `vpn.northwind.example` but drops after a few minutes.
- You see the message "The VPN connection was disconnected" or AnyConnect shows "Reconnecting...".
- Teams calls and file transfers freeze periodically while working remotely.

## Cause
Northwind Labs VPN sessions have two built-in limits: an **idle timeout of 30 minutes** (no traffic) and a **maximum session length of 12 hours**, after which you must sign in again. Disconnects outside these limits are usually caused by Wi-Fi power saving, an outdated AnyConnect client (older than version 5.1), unstable home Wi-Fi, or a laptop going to sleep.

## Resolution steps
1. Confirm your AnyConnect version: open AnyConnect, click the gear icon, then **About**. If it is older than 5.1, install the latest version from **Company Portal > Apps > Cisco Secure Client**.
2. Disable Wi-Fi adapter power saving: open **Device Manager > Network adapters**, right-click your Wi-Fi adapter, choose **Properties > Power Management**, and clear **Allow the computer to turn off this device to save power**.
3. Set your power plan so the laptop does not sleep while plugged in: **Settings > System > Power & battery > Screen and sleep**, set "When plugged in, put my device to sleep after" to **Never**.
4. If possible, connect via an Ethernet cable or move closer to your router. Prefer the 5 GHz band.
5. Restart your home router and laptop, then reconnect.
6. If disconnects happen exactly every 12 hours, this is expected; simply reconnect.

## When to contact IT
Open a ticket at https://help.northwind.example (category **Network > VPN**) if the VPN still drops more than once per hour after completing the steps above. Include:
- The time of the disconnects
- Your AnyConnect version
- The diagnostic bundle: AnyConnect gear icon **> Diagnostics > DART**, then attach the generated ZIP file

If you cannot work at all because of VPN issues, call the IT hotline at local **4357**.
