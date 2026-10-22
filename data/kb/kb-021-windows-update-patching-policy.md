---
id: KB-021
title: Windows Update and Mandatory Patching Policy
category: Software
tags: [windows-update, patching, restart, reboot, compliance]
---

# Windows Update and Mandatory Patching Policy

## Symptoms
- A Windows toast notification states "Your device needs to restart to install updates" or "Mandatory update deadline reached".
- Your laptop restarts unexpectedly overnight or during the active workday after a pending patch window expires.
- Windows Update reports error code `0x80070002` or `0x80240020` while downloading monthly cumulative quality updates.
- Intune displays a compliance warning banner indicating your operating system build is out of compliance.

## Cause
Northwind Labs distributes Microsoft cumulative quality and security updates on **Patch Tuesday (the second Tuesday of each calendar month)** via Microsoft Intune. To balance productivity with zero-day vulnerability protection, standard policy grants a **7-day grace period** from release date for users to schedule their restart. If a reboot has not occurred by day 7, Intune enforces an automatic restart with a persistent **15-minute countdown timer** that cannot be snoozed. In addition, quality updates require at least **20% battery charge** and connection to AC power before installation will commence.

## Resolution steps
1. **Check for pending updates manually**: Click **Start > Settings > Windows Update** (or press **Win + I** and select **Windows Update**). Click **Check for updates** to download all approved patches.
2. **Configure Active Hours**: Navigate to **Settings > Windows Update > Advanced options > Active hours**. Set your typical working schedule (default is **08:00 to 18:00**) so automatic background reboots do not disrupt meetings or presentations.
3. **Schedule an intentional restart**: When updates have completed downloading, click **Restart now**, or select **Schedule the restart** to specify an evening hour when your laptop will remain plugged into wall power.
4. **Resolve stalled download cache**: If an update gets stuck downloading at 0% or 100%:
   - Press **Win + R**, type `services.msc`, and press Enter.
   - Locate and right-click **Windows Update**, then click **Stop**.
   - Open File Explorer and navigate to `C:\Windows\SoftwareDistribution\Download`. Delete all files and folders inside this directory.
   - Return to the Services window, right-click **Windows Update**, and click **Start**.
   - Return to Settings and click **Check for updates** again.
5. **Leave device connected overnight**: Remote employees should leave their laptop connected to AC power and home Wi-Fi overnight at least once a week (specifically Wednesday night following Patch Tuesday) to allow background maintenance tasks and Intune policy evaluation to complete.

## When to contact IT
Open a ticket at https://help.northwind.example under **Software > Operating System** if an update repeatedly fails with an error code after two restart attempts. Include your current Windows build number (**Win + R**, type `winver`).

If your laptop enters a continuous boot loop or displays "Working on updates - 100% complete" for more than **2 hours**, contact the IT hotline immediately at local **4357**.
