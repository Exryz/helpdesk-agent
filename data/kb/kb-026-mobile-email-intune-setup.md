---
id: KB-026
title: Setting Up Mobile Email and Intune App Protection
category: Email & Collaboration
tags: [mobile, intune, outlook-mobile, ios, android, company-portal, mam]
---

# Setting Up Mobile Email and Intune App Protection

## Symptoms
- Corporate email, calendar, or Microsoft Teams will not synchronize on your personal smartphone or tablet.
- The built-in iOS Mail or Samsung Email app shows the error "Your organization requires this device to be managed with Microsoft Intune".
- Outlook Mobile prompts for a 6-digit application PIN or displays the alert "Device out of compliance".
- Attempts to copy text from corporate email into personal messaging apps fail with the banner "Your organization's data cannot be pasted here".

## Cause
Northwind Labs utilizes Microsoft Intune **Mobile Application Management (MAM)** with Application Protection Policies (APP). This security architecture protects corporate data without requiring full Mobile Device Management (MDM) enrollment or supervision of your personal smartphone (BYOD). Access to Northwind Microsoft 365 services on mobile devices is strictly restricted to approved Microsoft apps (such as Microsoft Outlook, Microsoft Teams, and OneDrive). Native mobile mail clients (Apple Mail, Gmail app) are blocked by Conditional Access rules. In addition, mobile operating systems must run at least **iOS 16.0** or **Android 11.0**, have a secure device lockscreen passcode enabled, and cannot be rooted or jailbroken.

## Resolution steps
1. **Install required prerequisite broker software**:
   - **Android users**: Install the **Intune Company Portal** app from the Google Play Store. (Open the app once, but you do not need to enroll the entire phone; it simply serves as the security broker).
   - **iOS / iPhone users**: Install the **Microsoft Authenticator** app from the Apple App Store to broker MAM tokens.
2. **Install Microsoft Outlook**: Download the official **Microsoft Outlook** app from the Apple App Store or Google Play Store.
3. **Add your corporate account**:
   - Open Outlook and tap **Add Account** (or **Get Started**).
   - Enter your corporate Northwind email address (`firstname.lastname@northwind.example`) and tap **Continue**.
   - You will be redirected to the Northwind Okta authentication page. Enter your password and complete the multi-factor authentication push approval.
4. **Accept the Intune Application Protection Policy**:
   - When the Intune prompt appears stating "Your organization is protecting its data in this app", tap **OK**.
   - You will be prompted to restart Outlook. Close the app and re-open it.
5. **Establish your 6-digit App PIN**: Create a **6-digit PIN** dedicated to Northwind corporate apps. You may optionally enable Face ID or fingerprint biometrics for convenient subsequent unlocks.
6. **Data protection restrictions**: Remember that copy-pasting corporate text into unmanaged apps (such as WhatsApp, Notes, or personal email) is blocked by policy. To review attachments, use OneDrive or Microsoft 365 mobile viewers.

## When to contact IT
Open a support ticket at https://help.northwind.example under **Email & Collaboration > Mobile Device** if Outlook Mobile displays persistent compliance errors after following these steps.

If you misplace your mobile phone, immediately contact the IT Helpdesk at local **4357** so a selective remote wipe can be triggered to erase corporate data from the device without affecting personal photos or texts.
