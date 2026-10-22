---
id: KB-022
title: New Hire IT Onboarding and First-Day Account Setup
category: Accounts & Access
tags: [onboarding, new-hire, welcome-email, temporary-password, first-day]
---

# New Hire IT Onboarding and First-Day Account Setup

## Symptoms
- A newly hired employee has not received their initial Okta activation link or temporary corporate login credentials.
- The new hire cannot log into their assigned Northwind Dell laptop on their first day of employment.
- Day-one access is missing for departmental SharePoint sites, Microsoft 365 services, or required Slack channels.
- The one-time Okta activation link displays the error "This activation link has expired or has already been used".

## Cause
New employee accounts are automatically generated from Workday HR records **3 business days** prior to the employee's official start date. Once provisioned, an automated onboarding welcome message containing a temporary password and activation link is sent to the employee's **personal email address** provided during the recruitment process. The initial activation link has a strict **72-hour expiration window**. In addition, logging into the corporate Windows laptop for the first time requires completing initial multi-factor authentication enrollment (KB-006) on a mobile device so that cloud credentials can be validated.

## Resolution steps
1. **Locate the welcome message**: Search your personal email inbox and spam/junk folder for an email sent by `it-onboarding@northwind.example` with the subject "Welcome to Northwind Labs - IT Account Setup".
2. **Retrieve your credentials**: The email specifies your corporate username (format: `firstname.lastname`), your **6-digit employee ID number** (NW-######), and a single-use Okta activation link.
3. **Activate your Okta account**: On a mobile phone or personal computer, click the activation link. When prompted, establish your permanent corporate password meeting Northwind's 14-character complexity requirements (KB-004).
4. **Register Multi-Factor Authentication**: Immediately follow the on-screen prompts to register the **Microsoft Authenticator** app (see KB-006) as your primary MFA verification factor.
5. **Complete initial Windows workstation sign-in**:
   - Power on your assigned Northwind Dell laptop.
   - At the Windows login screen, connect to the office Wi-Fi network (or your home Wi-Fi via the network icon in the bottom-right corner).
   - Enter your full email address (`firstname.lastname@northwind.example`) and your newly chosen password.
   - Wait **15 to 30 minutes** after your initial desktop load while Intune applies device encryption, security certificates, and base software packages.
6. **Access the New Hire Portal**: Launch Microsoft Edge and navigate to `https://start.northwind.example` to review the Day 1 IT checklist and verify tool access.

## When to contact IT
Hiring managers must submit all hardware and account requisition forms at least **5 business days** before the start date to ensure on-time equipment provisioning.

If the new hire's activation link has expired, or if no welcome email was received by **09:00 local time** on Day 1, call the IT Helpdesk hotline at local **4357** for real-time identity verification and phone-assisted onboarding.
