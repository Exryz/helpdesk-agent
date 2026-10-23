---
id: KB-013
title: OneDrive Sync Errors
category: Software
tags: [onedrive, sync, files, microsoft-365]
---

# OneDrive Sync Errors

## Symptoms
- The OneDrive cloud icon in the taskbar shows a **red X**, a **pause** symbol, or "Sync pending" that never finishes.
- Files show a red circle with an X in File Explorer.
- Error messages such as "This item cannot be synced", "File name not valid", or "Your OneDrive is full".

## Cause
Each Northwind employee has **1 TB** of OneDrive storage. Sync errors are usually caused by:
- Invalid characters in file names: `" * : < > ? / \ |` or names starting with a space.
- Full path longer than **400 characters**.
- Single files larger than **250 GB**.
- Files open in another program, or locked by another user.
- OneDrive signed out after a password change.
- Low disk space on the laptop.

## Resolution steps
1. Click the OneDrive cloud icon in the taskbar to view the list of sync issues. Click each item for details.
2. Rename files with invalid characters and shorten deep folder paths.
3. Close the affected files in Word, Excel or other apps and wait a minute.
4. If OneDrive is paused, click the icon, then the gear **> Resume syncing**.
5. If you are signed out, click the icon and sign in with your Northwind account.
6. Free up local space: right-click large folders and choose **Free up space** so files stay online only (Files On-Demand).
7. Restart OneDrive: click the icon, gear **> Quit OneDrive**, then start OneDrive from the Start menu.
8. If the issue persists, reset OneDrive: press **Win + R**, enter `%localappdata%\Microsoft\OneDrive\onedrive.exe /reset`, click OK, then start OneDrive again after 2 minutes. Resetting does **not** delete your files, but re-sync can take several hours.

## Important
- Do not sync SharePoint libraries with more than **100,000 files**; use **Add shortcut to My files** selectively.
- Deleted files can be restored from the **OneDrive Recycle bin** at https://northwind-my.sharepoint.com for **93 days**.
- Personal cloud services (Dropbox, Google Drive) are not permitted for company data (see KB-027).

## When to contact IT
If files remain unsynced after a reset, open a ticket at https://help.northwind.example under **Software > OneDrive** with a screenshot of the sync issue list.
