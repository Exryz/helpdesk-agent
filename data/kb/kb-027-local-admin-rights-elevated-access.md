---
id: KB-027
title: Local Administrator Rights, Elevated Access, and Acceptable Use Policy
category: Security
tags: [local-admin, elevated-access, admin-rights, security, laps, privileges, acceptable-use]
---

# Local Administrator Rights, Elevated Access, and Acceptable Use Policy

## Symptoms
- An installation wizard or driver update prompts: "User Account Control: Do you want to allow this app to make changes? Enter an administrator username and password".
- A developer command-line tool, virtualization suite, or hardware flashing utility fails with "Access is denied: Requires elevated administrative privileges".
- You need to edit system configuration files, register a local service, or install third-party developer libraries.
- An attempt to install unsanctioned consumer software or connect unapproved personal cloud storage (e.g. personal Dropbox or Google Drive) is blocked by endpoint protection.

## Cause
Under Northwind Labs Information Security Standard **SEC-08 (Principle of Least Privilege)**, standard workstation user accounts operate without permanent local administrator rights. Permanent local administrative access creates severe security exposures, including the automated spread of ransomware, credential dumping from memory, and unvetted software execution. Furthermore, company policy strictly prohibits installing software from unapproved sources, USB thumb drives, personal cloud sync clients, and peer-to-peer file sharing utilities. Workstations require temporary, audited elevation using **Admin By Request (ABR)** or Microsoft LAPS for sanctioned business activities.

## Resolution steps
1. **Verify if software is in Company Portal**: Before requesting admin elevation, launch **Company Portal** (KB-019). Over 150 standard applications and tools can be installed self-service without requiring administrative rights.
2. **On-demand elevation with Admin By Request**:
   - Right-click the executable, installer, or command prompt shortcut you need to elevate and select **Run with Admin By Request** from the context menu.
   - In the prompt window that opens, enter a specific **Business Justification** (e.g., "Updating Node.js packages for Project Alpha" or "Calibrating lab sensor interface driver").
   - For pre-whitelisted engineering tools, elevation is approved instantly for a duration of **15 minutes**.
   - For novel or non-whitelisted installers, your request is automatically routed to the IT Service Desk for real-time review (typical approval turnaround is under **10 minutes** during working hours, 08:00 to 18:00).
3. **Session auditing and revocation**: During the active 15-minute elevation window, all executed processes and modified system registry keys are logged to the corporate SIEM. Once the timer elapses, administrative rights revoke automatically.
4. **Developer Workstation Profiles**: Software engineers requiring continuous elevated privileges for kernel debugging or Hyper-V virtualization must submit a formal **Developer Exception Request** approved by their Department Director and the Head of Information Security, subject to quarterly audit re-certification.
5. **Comply with Acceptable Use**: Installing personal cloud clients (Dropbox, Google Drive, iCloud), torrent software, or cryptocurrency mining tools is strictly forbidden and results in immediate automated account quarantine.

## When to contact IT
Submit a ticket at https://help.northwind.example under **Accounts & Access > Elevated Privileges** if Admin By Request is not operating properly on your laptop or if an elevation request is repeatedly rejected.

For emergency server or lab infrastructure elevation outside normal working hours, call the on-call systems team via the IT hotline at local **4357**.
