---
id: KB-008
title: Requesting Access to Shared Drives and SharePoint Sites
category: Accounts & Access
tags: [sharepoint, shared-drive, permissions, access-request]
---

# Requesting Access to Shared Drives and SharePoint Sites

## Overview
Northwind Labs department files are stored in **SharePoint Online** team sites (for example *Finance*, *HR*, *Engineering*). The legacy network shares (`\\nw-fs01\dept`) are read-only and will be retired; all new access is granted on SharePoint. Access follows the principle of **least privilege** and every request must be approved by the **data owner** - usually the department head.

## Symptoms
- "You need permission to access this item" or "Access denied" when opening a SharePoint link.
- A department folder does not appear in your OneDrive / File Explorer shortcuts.

## Resolution steps
1. Open the service portal at **https://help.northwind.example**.
2. Select **Request something > Access Request > SharePoint / Shared Drive**.
3. Fill in:
   - The site or folder name (or paste the link).
   - The access level: **Read**, **Edit**, or **Owner** (Owner is rarely approved).
   - A business justification.
   - Duration: permanent or temporary (temporary access expires automatically, maximum **90 days**).
4. Submit. The request is routed automatically to the data owner for approval.
5. Once approved, IT provisions access within **1 business day**. You will receive an email confirmation.
6. To see the site in File Explorer, open it in the browser, go to **Documents**, and click **Add shortcut to My files**.

## Notes
- Clicking **Request access** directly on a SharePoint "Access denied" page also notifies the site owner, but portal requests are preferred because they are tracked and audited.
- Access to **Restricted** data (see KB-024) such as HR or payroll records also needs Security team approval and takes up to **3 business days**.
- Managers review access to their sites every quarter; unused access may be removed.
- When you change departments, your old department access is removed after **30 days**.

## When to contact IT
If your request has been approved but you still cannot access the site after 1 business day, add a comment to your ticket on the portal or call local **4357**.
