---
id: KB-023
title: Reporting a Lost or Stolen Laptop, Phone, or Tablet
category: Security
tags: [lost, stolen, incident, remote-wipe, security, mobile]
---

# Reporting a Lost or Stolen Laptop, Phone, or Tablet

## Symptoms
- A Northwind Labs issued Dell laptop, company smartphone, tablet, or enrolled BYOD device has been misplaced, stolen from a vehicle or hotel room, or lost in transit.
- You suspect unauthorized physical access to a corporate device containing sensitive internal documents, emails, or stored session tokens.
- An enrolled mobile phone used for Microsoft Authenticator MFA has gone missing.

## Cause
A lost or stolen corporate endpoint is classified as an immediate security incident under Northwind Information Security Policy **SEC-04 (Endpoint Loss and Theft)**. Because Northwind devices may hold proprietary research data and cached authentication tokens, prompt mitigation is critical. All corporate laptops are secured with BitLocker full-disk encryption and registered in Microsoft Intune, allowing the IT Security Operations Center (SOC) to instantly execute remote wipe commands and isolate stolen hardware from internal networks.

## Resolution steps
1. **Report the incident immediately**: Do not spend time searching if theft is suspected. Immediately call the 24/7 IT Emergency Hotline at local **4357** (or `+1-555-019-4357` if outside the office) or email `security-incident@northwind.example`. Every lost device report is handled as a **P1 (Critical)** priority ticket.
2. **Provide essential details**:
   - Device type and manufacturer (e.g., Dell Latitude 7440, iPhone 14).
   - Asset tag or Dell Service Tag (7-character alphanumeric code on the bottom sticker), if known.
   - Approximate date, time, and geographic location where the device was last seen.
   - Whether the device was powered on, locked, and whether your temporary PIN/passcode was compromised.
3. **Obtain a police report**: If the device was stolen in a vehicle break-in, public venue, or during travel, file a police report with local authorities within **24 hours**. You must provide the police report or case reference number to IT for corporate insurance coverage and asset write-off.
4. **Security remediation taken by IT**:
   - The SOC immediately issues an Intune **remote wipe** or cryptographic lock.
   - All active Okta, Microsoft 365, and VPN user sessions are invalidated immediately.
   - MFA tokens associated with the lost device are revoked to prevent push-notification replay attacks (see KB-007).
5. **Update your credentials**: From a secondary trusted computer, log in to https://northwind.okta.com, navigate to **Settings**, and change your corporate password (KB-004).
6. **Request a replacement**: Have your line manager approve an expedited hardware replacement ticket via https://help.northwind.example under **Hardware > Replacement (Lost/Stolen)** referencing the incident case number.

## When to contact IT
Contact IT immediately upon discovering the loss. Call the hotline at local **4357** 24 hours a day, 7 days a week. Never wait until the next business day to report missing equipment.
