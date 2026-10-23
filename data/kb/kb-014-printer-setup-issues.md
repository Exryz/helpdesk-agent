---
id: KB-014
title: Printer Setup and Common Printer Issues
category: Hardware
tags: [printer, printing, papercut, secure-print]
---

# Printer Setup and Common Printer Issues

## Overview
Northwind Labs uses **follow-me secure printing** with PaperCut. You print to a single queue called **NW-SecurePrint**, then release the job at **any** office printer by tapping your badge. Jobs that are not released are deleted after **24 hours**. Color printing is enabled by default; please print in black and white whenever possible.

## Setting up the printer
1. Make sure you are on **NW-Corp** Wi-Fi, a docking station, or connected to VPN.
2. Go to **Settings > Bluetooth & devices > Printers & scanners**.
3. Click **Add device**. Wait for **NW-SecurePrint on nw-print01** to appear and click **Add device**.
4. If it does not appear, click **Add manually**, choose **Select a shared printer by name**, and enter `\\nw-print01\NW-SecurePrint`.
5. Alternatively, install **Northwind Printers** from **Company Portal**, which adds the queue automatically.

## Releasing a print job
1. Walk to any printer and tap your **employee badge** on the card reader.
2. First-time use: you will be asked to enter your Okta username and password to link your badge.
3. Select your jobs on the touchscreen and tap **Print**, or **Print All**.

## Common issues
| Problem | What to do |
|---|---|
| Job does not appear at printer | Check you printed to NW-SecurePrint, not a local/old printer. Wait 1 minute and tap your badge again. |
| Paper jam | Follow the on-screen animation to open the indicated door and gently remove paper. Never use tools. |
| Out of toner or paper | Paper is in the cabinet next to each printer. Toner is replaced by Facilities - report it via the portal. |
| Badge not recognized | Re-link the badge by tapping **Register card** on the printer screen. |
| Printing from home | Printing to office printers from home is not supported; jobs will wait 24 hours for release. Personal home printers may be added via USB. |

## When to contact IT
Open a ticket at https://help.northwind.example under **Hardware > Printer** for repeated jams, error codes on the display, or hardware faults. Include the **printer name sticker** (for example `NW-PRN-3F-01` = 3rd floor) and the error code. Printer issues are normally **P4 (Low)** priority unless a whole floor cannot print.
