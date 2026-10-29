---
description: >-
  Ban IP addresses after too many failed logins. Administrators configure the rate limiting from the settings page.
---

# Rate limiting

## What it does

Rate limiting protects the login page against password guessing(bruteforce attacks). It works on two levels:

- **Per IP address.** When the CISO Assistant rate limiting is enabled, it counts failed logins per IP address. An IP address that goes over the limit is banned for the rest of the time window.
- **Per account.** Failed logins are also limited for each account, independently of the IP address. This limit is handled by the login layer (allauth) and stays active whether or not rate limiting is enabled.

## Settings

The rate limiting settings are on the **Settings** page. The page has three fields:

| Field | What it controls | Default | Allowed values |
| --- | --- | --- | --- |
| **Enable rate limiting** | When disabled, IP addresses are no longer banned after too many failed logins. | Enabled | On / off |
| **Max failed login attempts** | Failed logins allowed per IP address and per time window before it is banned. | 20 | 5 to 1000 |
| **Time window size (minutes)** | Failed logins are counted per time window of this size. | 5 | 1 to 15 |

## Behaviour when rate limiting is enabled

- CISO Assistant alone decides on IP-based bans, using the settings described above.
- At most 15 attempts per account. (for every 5 minutes as we still use `allauth` for this).

## Behaviour when rate limiting is disabled

- At most 90 login attempts per IP can made (for every minute).
- At most 30 failed logins per IP can be made (for every minute)
- At most 15 attempts per account can be made (for every 5 minutes).

Note that all these limits were tripled because our backend docker image runs with `3` gunicorn worker processes.
In reality the limit should be 30/10/5(instead of 90/30/15).
This is due to the underlying library `allauth` using inconsistent caching.

## Permissions

Changing these settings requires the `change_globalsettings` permission. See [Settings](README.md#permissions).
