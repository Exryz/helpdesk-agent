---
id: KB-003
title: Connecting to Office Wi-Fi and Guest Wi-Fi
category: Network
tags: [wifi, wireless, guest, office]
---

# Connecting to Office Wi-Fi and Guest Wi-Fi

## Overview
Northwind Labs offices broadcast two wireless networks:

| Network (SSID) | Who can use it | How you sign in |
|---|---|---|
| **NW-Corp** | Company-managed laptops only | Automatic, using the Intune device certificate |
| **NW-Guest** | Visitors, contractors, personal phones | Captive portal with a sponsor-approved code |

The hidden legacy network "Northwind-WLAN" was retired and must not be used.

## Connecting a company laptop to NW-Corp
1. Click the network icon in the taskbar and select **NW-Corp**, then **Connect**.
2. The laptop authenticates automatically with its device certificate; no password is needed.
3. If you are prompted for credentials or see "Can't connect to this network", right-click NW-Corp, choose **Forget**, run a Company Portal sync (**Company Portal > Settings > Sync**), restart, and try again.

## Guest Wi-Fi (NW-Guest)
1. The visitor connects to **NW-Guest** and a captive portal page opens in the browser.
2. The visitor enters their name, email and the name of their Northwind host (sponsor).
3. The sponsor receives an approval email and must click **Approve**.
4. Guest access is valid for **24 hours** and is limited to internet access with a 10 Mbps bandwidth cap. Internal systems are not reachable from NW-Guest.
5. For multi-day events, reception can issue an event code valid for up to **7 days**.

Employees must not connect personal devices to NW-Corp; use NW-Guest for personal phones and tablets.

## Troubleshooting slow or weak Wi-Fi
- Move closer to an access point; conference rooms each have a ceiling access point.
- Toggle Wi-Fi off and on, or run **Settings > System > Troubleshoot > Other troubleshooters > Network and Internet**.
- Use a wired dock connection at your desk when available.

## When to contact IT
Report building-wide outages or a specific room with persistently slow Wi-Fi by opening a ticket at https://help.northwind.example under **Network > Wi-Fi**, including the room name, floor and time of day. For an office-wide outage, call local **4357**.
