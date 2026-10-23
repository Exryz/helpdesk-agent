---
id: KB-028
title: Troubleshooting Browser Errors and Okta SSO Login Loops
category: Software
tags: [browser, sso, okta-loop, chrome, edge, cookies, cache]
---

# Troubleshooting Browser Errors and Okta SSO Login Loops

## Symptoms
- When attempting to access internal web portals (such as Jira, Confluence, Workday, or SharePoint), the browser bounces repeatedly between `northwind.okta.com` and the destination URL without ever loading the page.
- The web browser displays an error screen stating "HTTP 400 Bad Request - Request Header Or Cookie Too Large" or "ERR_TOO_MANY_REDIRECTS".
- The Okta login screen reloads and requests your credentials or MFA approval repeatedly in an infinite loop.
- Certain internal cloud web applications render blank white screens or throw SAML assertion token errors.

## Cause
Single Sign-On (SSO) redirect loops typically occur when accumulated HTTP cookie payloads exceed browser header size limits, or when cached session cookies become corrupted across Northwind's identity providers. Additionally, aggressive third-party browser extensions (such as privacy blockers or custom script disablers) can intercept SAML/OIDC authentication tokens passed between Okta and internal applications. Finally, if your laptop's local system clock drifts by more than **5 minutes** from UTC network time, SAML assertion tokens are rejected as expired by security filters.

## Resolution steps
1. **Verify with a Private / InPrivate browsing window**:
   - In **Google Chrome**, press **Ctrl + Shift + N** to open an Incognito window.
   - In **Microsoft Edge**, press **Ctrl + Shift + P** to open an InPrivate window.
   - Navigate to `https://northwind.okta.com` and log in. If authentication succeeds normally, the problem is isolated to your standard profile's cached cookies or browser extensions.
2. **Clear domain-specific cookies and cache**:
   - In **Microsoft Edge**: Navigate to `edge://settings/siteData`. Type `okta.com` into the search box and click **Delete all shown**. Repeat the search for `northwind.example` and remove all matches.
   - In **Google Chrome**: Navigate to `chrome://settings/content/all`. Search for `okta.com` and select **Delete data**. Search for `northwind.example` and delete data.
3. **Perform a full browser cache flush**: Press **Ctrl + Shift + Delete** in either browser. In the dialogue, choose Time range: **All time**. Check the boxes for **Cookies and other site data** and **Cached images and files**. Click **Clear data**.
4. **Disable conflicting extensions**: Go to `chrome://extensions` or `edge://extensions`. Temporarily toggle off third-party ad blockers, cookie managers, and script blockers, then refresh the application.
5. **Synchronize system clock**:
   - Press **Win + I** to open Settings, then navigate to **Time & language > Date & time**.
   - Ensure **Set time automatically** and **Set time zone automatically** are both toggled **On**.
   - Under Additional settings, click the **Sync now** button to synchronize with Northwind domain time servers.
6. **Fully restart the browser**: Close all open browser windows and tabs (**Alt + F4**), verify via Task Manager that no background browser processes remain running, and relaunch.

## When to contact IT
If redirect loops or "Cookie Too Large" errors persist across multiple browsers and incognito sessions, your Okta user profile or application assignment may be corrupted. Submit a ticket at https://help.northwind.example under **Accounts & Access > Single Sign-On (SSO)**.

If SSO failures prevent you from accessing mission-critical systems during business hours, call the IT Helpdesk at local **4357**.
