---
id: KB-028
title: Troubleshooting Browser Errors and Okta SSO Login Loops
category: Software
tags: [browser, sso, okta-loop, chrome, edge, cookies, cache]
---

# Troubleshooting Browser Errors and Okta SSO Login Loops

## Error Reference
| Error / Symptom | Typical Root Cause |
|---|---|
| `HTTP 400 Bad Request - Request Header Or Cookie Too Large` | Oversized or corrupted `okta.com` / `northwind.example` session cookies |
| `ERR_TOO_MANY_REDIRECTS` or infinite Okta MFA reload loop | Stale SAML session cookie or privacy/ad-blocker extension stripping OIDC tokens |
| SAML assertion rejected / blank white screen on Jira, Workday, SharePoint | System clock drifted by **> 5 minutes** from UTC |

## Step-by-Step Fix
1. **Test in Incognito / InPrivate** (`Ctrl+Shift+N` in Chrome, `Ctrl+Shift+P` in Edge) at `https://northwind.okta.com`. If it works there, your main profile cache/extensions are the culprit.
2. **Clear domain cookies:**
   - **Edge:** `edge://settings/siteData` -> remove `okta.com` and `northwind.example`
   - **Chrome:** `chrome://settings/content/all` -> delete `okta.com` and `northwind.example`
   - Or full flush: `Ctrl+Shift+Delete` -> **All time** -> check **Cookies** + **Cached images and files** -> **Clear data**.
3. **Check extensions & clock:**
   - Disable script/cookie blockers at `chrome://extensions` or `edge://extensions`.
   - Sync Windows time: **Settings (`Win+I`) > Time & language > Date & time** -> enable **Set time automatically** & click **Sync now**.
4. **Full browser restart:** Close all browser windows (`Alt+F4`), ensure no background Chrome/Edge processes remain in Task Manager, and relaunch.

## Escalation
If the loop persists in Incognito across multiple browsers, your Okta app assignment may need a reset—open a ticket under **Accounts & Access > Single Sign-On (SSO)** at https://help.northwind.example (or call ext. **4357** if blocked from critical apps).
