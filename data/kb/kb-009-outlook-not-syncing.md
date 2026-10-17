---
id: KB-009
title: Outlook Not Syncing or Stuck on "Updating"
category: Email & Collaboration
tags: [outlook, email, sync, microsoft-365]
---

# Outlook Not Syncing or Stuck on "Updating"

## Symptoms
- New emails do not arrive in Outlook on the laptop, but appear in Outlook on the web (https://outlook.office.com).
- The status bar shows **Working Offline**, **Disconnected**, or **Trying to connect...**.
- Folders show "This folder was last updated at..." or Outlook is stuck on "Updating this folder".
- Sent items stay in the **Outbox**.

## Cause
Common causes are Outlook's Work Offline mode being turned on, a full mailbox, a corrupted offline cache (OST file), a large attachment stuck in the Outbox, or an expired password.

## Resolution steps
1. Check Outlook on the web. If mail is missing there too, the problem is not your laptop - contact IT.
2. In Outlook, go to the **Send / Receive** tab and make sure **Work Offline** is not highlighted. Click it to toggle off if needed.
3. Check mailbox size: **File > Info > Mailbox Settings**. Northwind mailboxes have a **100 GB** quota; at 99 GB you can no longer send. Empty **Deleted Items** and archive old mail.
4. Remove large items from the **Outbox** (maximum attachment size is **25 MB**; use a OneDrive link for larger files).
5. Close Outlook, wait 30 seconds, and reopen it. Restart the laptop if it still does not sync.
6. Repair the profile: **File > Account Settings > Account Settings**, select your account, click **Repair**.
7. If still stuck, create a new profile: close Outlook, open **Control Panel > Mail (Microsoft Outlook) > Show Profiles > Add**, name it, sign in, and set **Always use this profile** to the new one. Rebuilding the cache can take **1-2 hours** for large mailboxes.
8. Make sure your password has not expired (see KB-004).

## When to contact IT
If Outlook still does not sync after creating a new profile, open a ticket at https://help.northwind.example under **Email & Collaboration > Outlook**. Include screenshots of the status bar and the output of **File > Office Account > About Outlook** (version number). Email outages affecting multiple users should be reported via local **4357**.
