---
id: KB-024
title: Employee Offboarding, Data Handover, and Equipment Return
category: Accounts & Access
tags: [offboarding, departure, hardware-return, asset, data-classification, handover]
---

# Employee Offboarding, Data Handover, and Equipment Return

## Symptoms
- An employee departing Northwind Labs needs instructions for returning their company laptop, monitors, and security tokens.
- A departing employee or their manager needs to transfer ownership of project files, SharePoint document libraries, or OneDrive contents.
- A manager needs to request post-departure mailbox delegation or access to departing staff archives.
- An offboarding employee is unsure what personal files may be extracted prior to account decommissioning.

## Cause
Northwind IT standard **HR-OFF-02 (Separation & Asset Recovery)** and Data Classification Policy regulate employee departures. Account credentials, VPN profiles, and Single Sign-On tokens are automatically deactivated at **17:00 local time** on the employee's official last working day. Any files classified as **Restricted** or **Confidential** (including proprietary lab protocols, financial forecasts, and internal customer records) must remain strictly within Northwind systems and cannot be emailed to personal inboxes or uploaded to external storage. All hardware remains the exclusive property of Northwind Labs and must be returned within **5 business days** of departure.

## Resolution steps
1. **Personal data removal**: Prior to your final working day, delete personal web bookmarks, personal photos, and non-business documents from your laptop and OneDrive. Do not attempt to run factory reset tools or wipe Windows yourself; the IT Depot will perform DoD-compliant cryptographic sanitization upon return.
2. **Project handover and SharePoint migration**:
   - Move all active business documents out of your personal OneDrive and into your department's shared SharePoint site or Teams channel.
   - Reassign ownership of any automated Power Automate flows, Jira boards, or GitHub repositories to your teammate or manager.
   - Sharing or transferring files labeled **Restricted** externally is strictly prohibited and audited by automated DLP filters.
3. **Manager mailbox delegation**: Managers needing access to a former employee's mailbox or OneDrive files must submit an **Offboarding Access Delegation Request** at https://help.northwind.example with HR approval. Delegated mailbox access is granted for a maximum of **30 days** before the mailbox is converted to an inactive shared archive.
4. **On-site equipment return**: On your last day, hand in all corporate assets to the **IT Depot (Building A, 2nd Floor)** between 08:30 and 16:30. Required items include:
   - Dell laptop and 65W/130W USB-C AC power adapter.
   - Docking station, external monitors, and video adapters.
   - Corporate smartphone, tablet, and hardware YubiKey.
   - The depot technician will test the equipment and issue a signed **Asset Return Receipt**.
5. **Remote equipment return**: IT Logistics automatically ships a prepaid, custom-padded return box to remote staff **3 business days** prior to their separation date. Pack all items securely and drop the parcel off at an authorized UPS shipping point within **5 business days**.

## When to contact IT
Departing staff who have not received a prepaid return kit 2 days before their end date should open a ticket at https://help.northwind.example under **Hardware > Asset Return**.

Managers requiring immediate offboarding or emergency access termination for unexpected employee departures should call the IT hotline at local **4357**.
