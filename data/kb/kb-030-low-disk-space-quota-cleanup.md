---
id: KB-030
title: Low Disk Space and Storage Quota Cleanup
category: Hardware
tags: [disk-space, storage, c-drive, storage-sense, cleanup, full-disk]
---

# Low Disk Space and Storage Quota Cleanup

## Symptoms
- Windows displays a low storage alert: "Low Disk Space: You are running out of disk space on Windows (C:)".
- Software updates or application installations fail unexpectedly with disk write errors.
- Microsoft Outlook fails to download new attachments and displays "Cannot create work file" or "Mailbox data file reaches maximum size".
- Laptop performance becomes noticeably sluggish or the system freezes when opening large documents.

## Cause
Standard Northwind corporate laptops are provisioned with a **512 GB NVMe solid-state drive** partitioned into a single local operating system volume (C:). To maintain adequate space for Windows cumulative updates, swap file paging, and BitLocker cryptographic operations, corporate compliance standards require at least **15% free disk space (approximately 75 GB)** on the primary drive. Primary drivers of disk exhaustion include accumulated temporary cache files, old Windows Update installation remnants, and OneDrive synchronization configured to retain local offline copies of all departmental directories instead of using Files On-Demand.

## Resolution steps
1. **Enable and configure Windows Storage Sense**:
   - Open **Settings** (**Win + I**) and click **System > Storage**.
   - Toggle **Storage Sense** to **On**.
   - Click **Storage Sense** to configure cleanup rules: set "Run Storage Sense" to **Every week**, set "Delete temporary files that my apps aren't using" to **Checked**, and set the Recycle Bin threshold to **14 days**.
2. **Review Cleanup Recommendations**:
   - In **Settings > System > Storage**, click **Cleanup recommendations**.
   - Expand **Temporary files** and check **Previous Windows installations** (Windows.old) and **Downloads folder** (ensure you save any personal files first).
   - Click **Clean up** to immediately reclaim several gigabytes of space.
3. **Turn on OneDrive Files On-Demand**:
   - Click the blue cloud **OneDrive** icon in the Windows taskbar tray, click the **Gear (Settings)** icon, and select **Settings**.
   - Under the **Sync and backup** tab, expand **Advanced settings**, and under **Files On-Demand**, ensure it is toggled **On**.
   - Open File Explorer, navigate to your Northwind OneDrive folder, right-click any large project folders that you do not require offline, and select **Free up space**. This replaces bulky local files with lightweight cloud-only shortcuts.
4. **Purge User Temp Directory**:
   - Press **Win + R**, type `%temp%`, and press Enter.
   - Select all files (**Ctrl + A**) and press **Delete**. If a prompt displays indicating a file is currently in use by an open program, click **Skip**.
5. **Uninstall unnecessary software**:
   - Open **Settings > Apps > Installed apps**, sort by **Size (Large to small)**.
   - If large optional tools (such as older IDEs, SDKs, or trial packages) are installed that you no longer need, launch **Company Portal** (KB-019) and click **Uninstall** on those applications.
6. **Important restrictions**: Never manually delete files directly inside `C:\Windows`, `C:\Program Files`, or `C:\ProgramData`, as modifying system directories can corrupt the operating system.

## When to contact IT
Open a support ticket at https://help.northwind.example under **Hardware > Storage** if you have less than **10 GB** of free space remaining after following these cleanup procedures.

Software engineers, data scientists, and lab researchers requiring secondary internal NVMe drives or high-capacity 1 TB upgrades for legitimate business needs may submit a **Hardware Storage Upgrade Request** with department cost center approval.
