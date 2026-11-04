---
id: KB-021
title: Windows Update and Mandatory Patching Policy
category: Software
tags: [windows-update, patching, restart, reboot, compliance]
---

# Windows Update and Mandatory Patching Policy

## Patch Tuesday Schedule & 7-Day Deadline
Northwind pushes monthly cumulative updates via Intune on **Patch Tuesday (second Tuesday of the month)**:
- **Grace period:** **7 days** to reboot at your convenience (**Settings > Windows Update > Schedule the restart**; set **Active hours** to `08:00–18:00`).
- **Forced reboot:** After day 7, Intune triggers a non-snoozable **15-minute countdown**. Updates require **>= 20% battery** and AC power.
- **Remote tip:** Leave your laptop plugged in on Wi-Fi Wednesday night after Patch Tuesday.

## Fixing Stuck Updates (`0x80070002` / `0x80240020` / Stuck at 0% or 100%)
```powershell
# Run in an elevated prompt or via services.msc:
net stop wuauserv
Remove-Item -Recurse -Force C:\Windows\SoftwareDistribution\Download\*
net start wuauserv
```
Then re-run **Settings > Windows Update > Check for updates**.

## Escalation
- Fails twice with an error code: open a ticket under **Software > Operating System** with your `winver` build number.
- Boot loop or stuck on *"Working on updates - 100% complete"* for **> 2 hours**: call ext. **4357** immediately.
