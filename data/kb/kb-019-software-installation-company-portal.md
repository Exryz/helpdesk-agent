---
id: KB-019
title: Installing Software with Company Portal and Requesting New Software
category: Software
tags: [software, company-portal, install, approval]
---

# Installing Software with Company Portal and Requesting New Software

## Overview
Northwind laptops are managed with Microsoft Intune. Employees do **not** have local administrator rights, so software must be installed either from **Company Portal** (self-service) or through an approved software request. Installing software from the internet, USB drives or personal accounts is not permitted (see KB-027).

## Installing approved software (self-service)
1. Click **Start** and open **Company Portal**.
2. Select **Apps** to browse the catalog, or use the search box. The catalog includes more than 150 pre-approved apps, such as Zoom, 7-Zip, Notepad++, Visual Studio Code, Python, Git, Power BI Desktop, Adobe Acrobat Reader and Slack.
3. Click the app, then **Install**. Installation status appears under **Downloads & updates**.
4. Most apps install within **15 minutes**. Restart if prompted.

## Requesting software that is not in Company Portal
1. Go to https://help.northwind.example and select **Request something > Software Request**.
2. Provide the software name, vendor website, version, business justification, and whether a paid license is needed.
3. The request goes through:
   - **Manager approval**
   - **Security review** (checks vendor security, data handling and licensing)
   - **Packaging** by IT, after which the app is pushed to your laptop or added to Company Portal
4. Typical turnaround is **3-5 business days** for free software. Paid software also requires a license purchase (see KB-020) and may take up to **10 business days**.

## Browser extensions
Only extensions in the **Edge Add-ons** allowlist can be installed. Request others through the same Software Request form.

## Prohibited software
Peer-to-peer file sharing, cracked or unlicensed software, personal VPNs, remote access tools (e.g. AnyDesk, TeamViewer personal), and cryptocurrency miners are prohibited and are automatically blocked.

## When to contact IT
If an install from Company Portal fails with an error, retry once, then open a ticket under **Software > Installation** with the error code shown in **Company Portal > Downloads & updates**.
