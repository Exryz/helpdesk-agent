---
id: KB-030
title: Low Disk Space and Storage Quota Cleanup
category: Hardware
tags: [disk-space, storage, c-drive, storage-sense, cleanup, full-disk]
---

# Low Disk Space and Storage Quota Cleanup

## Quota & Compliance Target
Standard Northwind laptops ship with a **512 GB NVMe SSD** (`C:`). Corporate compliance requires at least **15% free space (~75 GB)** so Windows cumulative updates, swap paging, and BitLocker operate reliably. When free space drops near zero, Outlook may fail with *"Cannot create work file"* and installers fail.

## Fast Cleanup Procedure

### 1. Turn On Windows Storage Sense
- Open **Settings (`Win+I`) > System > Storage** and toggle **Storage Sense** to **On**.
- Set **Run Storage Sense** to **Every week**, check **Delete temporary files that my apps aren't using**, and set the Recycle Bin threshold to **14 days**.
- Click **Cleanup recommendations > Temporary files**, select **Previous Windows installations (`Windows.old`)** and unneeded **Downloads**, then click **Clean up**.

### 2. Enable OneDrive Files On-Demand
- Click the taskbar **OneDrive** cloud icon **> Settings > Sync and backup > Advanced settings** and toggle **Files On-Demand** to **On**.
- In File Explorer, right-click large project folders in OneDrive that you don't need offline and select **Free up space**.

### 3. Purge `%temp%` and Unused Company Portal Apps
```powershell
# Press Win+R, run %temp%, or run in PowerShell to clear user temp files:
Remove-Item -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
```
- Check **Settings > Apps > Installed apps** (sort by **Size**) and uninstall unused optional tools via **Company Portal** (KB-019).
- **Warning:** Never manually delete files inside `C:\Windows`, `C:\Program Files`, or `C:\ProgramData`.

## Hardware Storage Upgrades & IT Escalation
- If you still have **< 10 GB free** after running the steps above, open a ticket at https://help.northwind.example under **Hardware > Storage**.
- Engineers, data scientists, and lab researchers needing a **1 TB NVMe upgrade** or secondary drive can submit a **Hardware Storage Upgrade Request** with department cost-center approval.
