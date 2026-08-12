{% hint style="info" %}
Available on the PRO plan.
{% endhint %}

# Branding

Branding settings let you replace the default CISO Assistant visuals with your organisation's identity — useful when the platform is deployed for end-customers, when a parent company hosts multiple subsidiaries, or simply to align the UI with internal design guidelines.

## Settings

- **Client name** — the display name used in headings and email signatures.
- **Logo** — replaces the default product logo in the header. Accepted formats: `.png`, `.jpeg`, `.jpg`, `.webp`, `.svg`.
- **Favicon** — replaces the browser-tab icon. Accepted formats: `.ico`, `.png`, `.jpeg`, `.jpg`, `.webp`, `.svg`.
- **Show images to unauthenticated users** — when on (default), the logo and favicon are visible on the login screen and other pre-authentication pages. Turn off to keep branding gated behind authentication.

## Operational notes

- Logo and favicon are stored as files inside the instance, not as external URLs. Upload them through the Settings UI rather than editing the database directly.
- The platform serves a content-hash header alongside each image so browser caches stay coherent when the file is replaced.
