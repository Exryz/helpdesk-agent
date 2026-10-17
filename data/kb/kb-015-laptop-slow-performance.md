---
id: KB-015
title: Laptop Running Slow
category: Hardware
tags: [performance, slow, laptop, windows-11]
---

# Laptop Running Slow

## Symptoms
- Apps take a long time to open, the fan runs constantly, or the laptop freezes briefly.
- Typing lags in Teams or Outlook.
- Task Manager shows CPU, memory or disk usage near 100%.

## Cause
Northwind's standard laptop is the **Dell Latitude 5440** with **16 GB RAM** and a 512 GB SSD, running Windows 11. Slowness is usually caused by not restarting for many days, too many browser tabs, low disk space, pending updates, or a background sync or security scan.

## Resolution steps
1. **Restart the laptop.** Shutting the lid is not a restart. Restart at least **once a week**; laptops that have not restarted for **7 days** receive a reminder notification.
2. **Check Task Manager**: press **Ctrl + Shift + Esc**, click the **CPU** or **Memory** column to sort, and close apps you do not need. Do not end processes named *Microsoft Defender*, *CrowdStrike* or *Intune Management Extension* - they are required security software.
3. **Free disk space**: keep at least **15% free**. Go to **Settings > System > Storage**, turn on **Storage Sense**, and run **Cleanup recommendations**. Use OneDrive **Free up space** for large folders (see KB-013).
4. **Install pending updates**: **Settings > Windows Update > Check for updates**, then restart (see KB-021).
5. **Use the right power mode**: **Settings > System > Power & battery > Power mode**, select **Best performance** when plugged in.
6. **Limit browser tabs** and disable unneeded browser extensions in Edge via **edge://extensions**.
7. **Update drivers and BIOS**: open **Dell Command | Update** from the Start menu and click **Check**, then **Apply**.
8. Make sure the laptop vents are not blocked; avoid using it on a bed or sofa.

## Hardware lifecycle
Laptops are replaced every **4 years**. If your laptop is older than 4 years, or has less than 16 GB RAM and you work with large datasets, your manager can request an early upgrade via the portal under **Hardware > Laptop Upgrade**.

## When to contact IT
If the laptop is still slow after a restart and the steps above, open a ticket at https://help.northwind.example under **Hardware > Performance**. Include a screenshot of Task Manager showing the **Performance** tab and the laptop's service tag (on the sticker underneath).
