# Zepp authentication

Milestone 1 uses an existing Zepp application token. It does not submit or store
your Zepp password and does not implement password login.

## Primary: browser cookies

1. Open <https://user.huami.com/privacy2/index.html> and sign in.
2. Open browser developer tools.
3. Select **Application** (called **Storage** in some browsers), then **Cookies**.
4. Locate the Huami/Zepp cookies and copy `apptoken` and `userid`.
5. Copy the repository template and add the values at the repository root:

   ```bash
   cp .env.example .env
   ```

   ```dotenv
   ZEPP_APP_TOKEN=<apptoken>
   ZEPP_USER_ID=<userid>
   ```

Keep the configured regional `ZEPP_HOST` unless captured traffic identifies a
different host.

## Fallback: Zepp app traffic

If the browser flow does not expose both values, capture your own Zepp app
traffic with a trusted HTTPS interception proxy or export a HAR. Find a request
to a host matching `api-mifit*.zepp.com`, then extract:

- the `apptoken` request header;
- the user ID from a `/users/{id}/...` request path;
- the exact regional API host.

Set these as `ZEPP_APP_TOKEN`, `ZEPP_USER_ID`, and `ZEPP_HOST` in the root
`.env`. Remove the capture after use; HAR and MITM files can contain credentials
and health data.

## Security and expiry

Treat `apptoken` like a password: do not paste it into issues, logs, examples,
commits, or chat. `.env` is gitignored. Tokens are expected to expire after
roughly 30 days, though actual lifetime is not guaranteed. On HTTP `401` or
`403`, repeat extraction and replace only the local `.env` value.

The endpoint, host, and live T-Rex Pro behavior are **unverified** until the
first successful sync.
