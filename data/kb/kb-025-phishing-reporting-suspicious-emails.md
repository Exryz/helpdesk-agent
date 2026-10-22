---
id: KB-025
title: Reporting Phishing and Suspicious Emails with PhishAlarm
category: Security
tags: [phishing, email, phishalarm, security, spam, suspicious]
---

# Reporting Phishing and Suspicious Emails with PhishAlarm

## Symptoms
- You receive an unexpected email purporting to be from executive management (e.g., asking you to urgently purchase gift cards or initiate a wire transfer).
- An email claims your Okta, Microsoft 365, or payroll account is suspended and directs you to a non-Northwind external URL.
- An incoming message contains an unsolicited `.zip`, `.iso`, `.html`, or password-protected document attachment.
- You clicked a suspicious link in an email and entered your corporate password or MFA code on the destination web page.

## Cause
Phishing, credential harvesting, and business email compromise (BEC) represent the most frequent attack vectors against Northwind Labs. Threat actors frequently spoof trusted vendors, executive leadership, or IT automated notifications. Northwind provides the integrated **PhishAlarm** reporting tool inside Microsoft Outlook to enable rapid submission of suspicious messages directly into the Security Operations Center (SOC) threat intelligence platform for automated quarantine and tenant-wide blocking.

## Resolution steps
1. **Never engage with suspicious senders**: Do not reply to the sender, click embedded hyperlinks, download attachments, or call telephone numbers listed in unverified emails.
2. **Report via Outlook Desktop App**:
   - Select the suspicious message in your inbox.
   - Click the **PhishAlarm** button (represented by a golden fishhook icon) located on the right side of the **Home** tab ribbon.
   - In the confirmation pop-up dialogue, click **Report Phishing**.
   - The message is immediately extracted from your mailbox, forwarded to `soc-alerts@northwind.example` with full RFC headers, and moved to your Deleted Items folder.
3. **Report via Outlook Web App (OWA) or Outlook Mobile**:
   - Open the message in OWA or Outlook Mobile.
   - Tap the three dots (**...**) at the top right of the message container.
   - Select **PhishAlarm** from the add-ins list, then tap **Report Phishing**.
4. **Immediate action if you clicked a link or entered credentials**:
   - **Immediately disconnect** your computer from the network: unplug the Ethernet cable or switch off Wi-Fi in the Windows taskbar.
   - Using your smartphone or a clean secondary device, navigate to https://northwind.okta.com and reset your corporate password immediately (KB-004).
   - Immediately call the IT Security Hotline at local **4357** so the SOC can terminate active authentication tokens and initiate endpoint isolation.
5. **Do not forward manually**: Avoid forwarding suspicious emails directly to helpdesk staff or coworkers via standard email, as standard forwarding strips critical MIME header telemetry needed by the SOC.

## When to contact IT
If you suspect you entered credentials or ran an unauthorized file attachment from a phishing message, call the IT Emergency Hotline at local **4357** immediately.

For general queries regarding email delivery or to request whitelist review for legitimate vendor newsletters filtered as spam, submit a ticket at https://help.northwind.example under **Security > Email Filtering**.
