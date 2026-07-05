"""Server-rendered /login page.

No React, no JavaScript dependency. Listed providers come from the
registry; clicking a provider sends a GET to
``/auth/login?provider=<name>``.

Visual styling mirrors the Nous Research design system (the
``@nous-research/ui`` package the React dashboard uses): the same
``Collapse`` / ``Rules Compressed`` typeface, amber-on-dark colour
tokens (``#170d02`` / ``#ffac02`` / ``#fff``), uppercase + wide-tracking
brand chrome, and the inset-bevel button shadow. Fonts are served
out of the SPA's ``/fonts/`` directory which the dashboard-auth gate
already allowlists pre-auth (see ``_GATE_PUBLIC_PREFIXES`` in
``middleware.py``), so the page renders without needing the React
bundle loaded.

Test-stable class names: the existing test suite extracts the
``class="provider-btn"`` anchor href to walk the OAuth flow. That
class name MUST NOT change without updating
``tests/hermes_cli/test_dashboard_auth_401_reauth.py``.
"""
from __future__ import annotations

import html

from hermes_cli.dashboard_auth import list_session_providers

# Inline minimal CSS. The dashboard's full skin lives in the React
# bundle, which we deliberately do NOT load here — the login page must
# not depend on the SPA build being present or on the injected session
# token.
#
# Single curly braces are placeholders for ``str.format``; CSS curlies
# are doubled (``{{`` / ``}}``).
_LOGIN_HTML_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in — Hermes Agent</title>
<style>
  /* Brand fonts shipped by @nous-research/ui — same files the SPA loads. */
  @font-face {{
    font-family: 'Collapse';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('/fonts/Collapse-Regular.woff2') format('woff2');
  }}
  @font-face {{
    font-family: 'Collapse';
    font-style: normal;
    font-weight: 700;
    font-display: swap;
    src: url('/fonts/Collapse-Bold.woff2') format('woff2');
  }}
  @font-face {{
    font-family: 'Rules Compressed';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('/fonts/RulesCompressed-Regular.woff2') format('woff2');
  }}
  @font-face {{
    font-family: 'Rules Compressed';
    font-style: normal;
    font-weight: 600;
    font-display: swap;
    src: url('/fonts/RulesCompressed-Medium.woff2') format('woff2');
  }}

  :root {{
    --background-base: #170d02;
    --midground: #ffac02;
    --foreground: #ffffff;
    --hairline: color-mix(in srgb, #ffac02 18%, transparent);
    --hairline-strong: color-mix(in srgb, #ffac02 35%, transparent);
  }}

  *, *::before, *::after {{ box-sizing: border-box; }}

  html, body {{
    margin: 0;
    padding: 0;
    min-height: 100vh;
    background: #0d0802;
    color: var(--foreground);
    font-family: 'Collapse', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 16px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }}

  /* Premium glowing backdrop dots and grid */
  body {{
    display: grid;
    place-items: center;
    padding: clamp(1.5rem, 6vh, 6rem) 1.25rem;
    overflow: hidden;
    position: relative;
    background-image:
      radial-gradient(
        ellipse at top,
        color-mix(in srgb, var(--midground) 4%, transparent) 0%,
        transparent 70%
      ),
      repeating-conic-gradient(
        color-mix(in srgb, var(--midground) 3%, transparent) 0% 25%,
        transparent 0% 50%
      );
    background-size: auto, 3px 3px;
    background-attachment: fixed;
  }}

  /* Ambient Blur Bubbles */
  .glow {{
    position: absolute;
    border-radius: 50%;
    filter: blur(90px);
    opacity: 0.08;
    background: var(--midground);
    pointer-events: none;
    z-index: 0;
  }}
  .glow-1 {{
    width: 350px;
    height: 350px;
    top: 5%;
    left: 10%;
  }}
  .glow-2 {{
    width: 400px;
    height: 400px;
    bottom: -5%;
    right: 10%;
  }}

  main {{
    width: 100%;
    max-width: 26rem;
    position: relative;
    z-index: 2;
    animation: slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
  }}

  @keyframes slide-up {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}

  @media (prefers-reduced-motion: reduce) {{
    main {{ animation: none; }}
  }}

  /* Brand wordmark above the card */
  .brand {{
    text-align: center;
    margin-bottom: 2rem;
    font-family: 'Rules Compressed', 'Collapse', sans-serif;
    font-weight: 600;
    font-size: 1.1rem;
    letter-spacing: 0.35em;
    text-transform: uppercase;
    color: var(--midground);
    opacity: 0.95;
    text-shadow: 0 0 20px rgba(255, 172, 2, 0.2);
  }}
  .brand .dot {{
    display: inline-block;
    width: 6px;
    height: 6px;
    background: var(--midground);
    margin: 0 0.55em 0.18em;
    vertical-align: middle;
    border-radius: 50%;
    box-shadow: 0 0 8px var(--midground);
  }}

  /* Glassmorphism Card Design */
  .card {{
    position: relative;
    padding: 2.75rem 2.25rem;
    background: rgba(23, 13, 2, 0.45);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 172, 2, 0.18);
    border-radius: 12px;
    box-shadow:
      0 12px 40px rgba(0, 0, 0, 0.5),
      inset 1px 1px 0 0 rgba(255, 255, 255, 0.05);
  }}

  h1 {{
    margin: 0 0 0.5rem;
    font-family: 'Rules Compressed', 'Collapse', sans-serif;
    font-weight: 600;
    font-size: 1.9rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--foreground);
    text-shadow: 0 2px 10px rgba(0,0,0,0.3);
  }}

  .subtitle {{
    margin: 0 0 2rem;
    color: color-mix(in srgb, var(--foreground) 60%, transparent);
    font-size: 0.92rem;
    line-height: 1.4;
  }}

  .provider-list {{
    display: grid;
    gap: 0.85rem;
  }}

  /* Premium Button Style */
  .provider-btn {{
    display: block;
    width: 100%;
    box-sizing: border-box;
    padding: 0.95rem 1rem;
    text-align: center;
    background: var(--midground);
    color: var(--background-base);
    font-family: 'Collapse', sans-serif;
    font-weight: 700;
    font-size: 0.78rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    text-decoration: none;
    border: 0;
    border-radius: 6px;
    cursor: pointer;
    box-shadow:
      inset 1px 1px 0 0 rgba(255, 255, 255, 0.25),
      inset -1px -1px 0 0 rgba(0, 0, 0, 0.15);
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }}
  .provider-btn:hover {{
    filter: brightness(1.1);
    box-shadow:
      0 0 16px rgba(255, 172, 2, 0.3),
      inset 1px 1px 0 0 rgba(255, 255, 255, 0.3);
    transform: translateY(-1px);
  }}
  .provider-btn:active {{
    filter: invert(1);
    transform: translateY(0);
  }}
  .provider-btn:focus-visible {{
    outline: 2px solid var(--midground);
    outline-offset: 3px;
  }}

  /* Password provider form */
  .provider-form {{
    display: grid;
    gap: 0.85rem;
    text-align: left;
  }}
  .form-title {{
    font-family: 'Rules Compressed', 'Collapse', sans-serif;
    font-weight: 600;
    font-size: 0.75rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: color-mix(in srgb, var(--foreground) 70%, transparent);
    border-bottom: 1px solid rgba(255, 172, 2, 0.15);
    padding-bottom: 0.5rem;
    margin-bottom: 0.25rem;
  }}
  .field {{
    display: grid;
    gap: 0.35rem;
  }}
  .field-label {{
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: color-mix(in srgb, var(--foreground) 50%, transparent);
  }}
  .field-input {{
    width: 100%;
    box-sizing: border-box;
    padding: 0.75rem 0.9rem;
    background: rgba(0, 0, 0, 0.35);
    color: var(--foreground);
    border: 1px solid rgba(255, 172, 2, 0.15);
    border-radius: 6px;
    font-family: 'Collapse', sans-serif;
    font-size: 0.95rem;
    transition: all 0.2s ease;
  }}
  .field-input:focus-visible {{
    outline: none;
    border-color: var(--midground);
    box-shadow: 0 0 0 2px rgba(255, 172, 2, 0.25);
    background: rgba(0, 0, 0, 0.5);
  }}
  .form-error {{
    color: #ff6b6b;
    font-size: 0.82rem;
    letter-spacing: 0.02em;
  }}
  .provider-form .provider-btn {{
    margin-top: 0.5rem;
  }}

  footer {{
    margin-top: 2rem;
    text-align: center;
    color: color-mix(in srgb, var(--foreground) 40%, transparent);
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    line-height: 1.7;
  }}
  footer .sep {{
    display: inline-block;
    width: 1.5rem;
    height: 1px;
    background: rgba(255, 172, 2, 0.15);
    vertical-align: middle;
    margin: 0 0.6em 0.2em;
  }}

  /* Selection */
  ::selection {{
    background: var(--midground);
    color: var(--background-base);
  }}
</style>
</head>
<body>
<div class="glow glow-1"></div>
<div class="glow glow-2"></div>
<main>
  <div class="brand">Nous<span class="dot"></span>Research</div>
  <div class="card">
    <h1>Sign in</h1>
    <p class="subtitle">Choose a sign-in method to continue to the Hermes Agent dashboard.</p>
    <div class="provider-list">
{provider_buttons}
    </div>
  </div>
  <footer>
    <span class="sep"></span>Public bind &middot; Auth required<span class="sep"></span>
  </footer>
</main>
{password_script}
</body>
</html>
"""

_EMPTY_HTML = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign-in unavailable — Hermes Agent</title>
<style>
  @font-face {
    font-family: 'Collapse';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('/fonts/Collapse-Regular.woff2') format('woff2');
  }
  @font-face {
    font-family: 'Rules Compressed';
    font-style: normal;
    font-weight: 600;
    font-display: swap;
    src: url('/fonts/RulesCompressed-Medium.woff2') format('woff2');
  }
  :root {
    --background-base: #170d02;
    --midground: #ffac02;
    --foreground: #ffffff;
    --hairline: color-mix(in srgb, #ffac02 18%, transparent);
  }
  *, *::before, *::after { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; min-height: 100%;
    background: var(--background-base);
    color: var(--foreground);
    font-family: 'Collapse', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 16px; line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }
  body {
    display: grid; place-items: center;
    padding: clamp(1.5rem, 6vh, 6rem) 1.25rem;
  }
  main {
    width: 100%; max-width: 32rem;
    padding: 2.25rem 2rem;
    background: color-mix(in srgb, #ffffff 2%, var(--background-base));
    border: 1px solid var(--hairline);
    box-shadow:
      inset 1px 1px 0 0 color-mix(in srgb, #ffffff 5%, transparent),
      inset -1px -1px 0 0 rgba(0, 0, 0, 0.4),
      0 24px 60px -20px rgba(0, 0, 0, 0.6);
  }
  h1 {
    margin: 0 0 1rem;
    font-family: 'Rules Compressed', 'Collapse', sans-serif;
    font-weight: 600; font-size: 1.5rem;
    letter-spacing: 0.05em; text-transform: uppercase;
    color: var(--midground);
  }
  p { margin: 0 0 1rem; }
  code {
    background: var(--midground);
    color: var(--background-base);
    padding: 0.1em 0.35em;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
  }
</style>
</head>
<body>
<main>
<h1>Sign-in unavailable</h1>
<p>This dashboard is bound to a non-loopback host but no authentication
providers are installed.</p>
<p>Install <code>plugins/dashboard-auth-nous</code> (default) or another
auth provider, or restart with <code>--insecure</code> to bypass the
auth gate (not recommended on untrusted networks).</p>
</main>
</body>
</html>
"""


# Inline script that wires every password provider form to POST JSON to
# ``/auth/password-login`` and navigate on success. Emitted ONLY when at
# least one ``supports_password`` provider is listed (OAuth-only login
# pages stay script-free, preserving the no-JS contract for that case).
#
# Plain string (NOT run through ``str.format``), so braces are literal —
# do not double them. A single delegated submit handler covers all forms;
# the provider name is read from the form's ``data-provider`` attribute.
_PASSWORD_FORM_SCRIPT = """\
<script>
(function () {
  function handle(form) {
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var err = form.querySelector('.form-error');
      var btn = form.querySelector('button[type=submit]');
      if (err) { err.hidden = true; err.textContent = ''; }
      if (btn) { btn.disabled = true; }
      var body = {
        provider: form.getAttribute('data-provider') || '',
        username: (form.querySelector('input[name=username]') || {}).value || '',
        password: (form.querySelector('input[name=password]') || {}).value || '',
        next: (form.querySelector('input[name=next]') || {}).value || ''
      };
      fetch('/auth/password-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'same-origin'
      }).then(function (resp) {
        if (resp.ok) {
          return resp.json().then(function (data) {
            window.location.assign((data && data.next) || '/');
          });
        }
        var msg = resp.status === 429
          ? 'Too many attempts. Please wait and try again.'
          : (resp.status === 401 ? 'Invalid username or password.'
                                 : 'Sign-in failed. Please try again.');
        if (err) { err.textContent = msg; err.hidden = false; }
        if (btn) { btn.disabled = false; }
      }).catch(function () {
        if (err) { err.textContent = 'Network error. Please try again.'; err.hidden = false; }
        if (btn) { btn.disabled = false; }
      });
    });
  }
  var forms = document.querySelectorAll('form.provider-form');
  for (var i = 0; i < forms.length; i++) { handle(forms[i]); }
})();
</script>
"""


def render_login_html(*, next_path: str = "") -> str:
    """Return the full HTML for ``GET /login``.

    ``next_path`` — when set, the post-login landing path the user
    originally requested. Threaded into each provider button's ``href``
    as a ``next=`` query parameter so the OAuth round trip carries it
    end-to-end. The caller (``routes.login_page``) is responsible for
    validating ``next_path`` against the same-origin rules before we
    emit it; we still HTML-escape it as defence in depth.
    """
    providers = list_session_providers()
    if not providers:
        return _EMPTY_HTML

    if next_path:
        # URL-encode then HTML-escape. The URL-encode step matches the
        # gate's ``_safe_next_target`` output shape (also URL-encoded),
        # so a value that round-tripped from /login?next=... back into
        # the button href is byte-identical.
        from urllib.parse import quote
        next_qs = f"&next={html.escape(quote(next_path, safe=''), quote=True)}"
    else:
        next_qs = ""

    buttons = []
    needs_password_script = False
    for p in providers:
        if getattr(p, "supports_password", False):
            needs_password_script = True
            buttons.append(_render_password_form(p, next_path))
        else:
            buttons.append(
                f'      <a class="provider-btn" '
                f'href="/auth/login?provider={html.escape(p.name, quote=True)}{next_qs}">'
                f'Sign in with {html.escape(p.display_name)}</a>'
            )
    script = _PASSWORD_FORM_SCRIPT if needs_password_script else ""
    return _LOGIN_HTML_TEMPLATE.format(
        provider_buttons="\n".join(buttons),
        password_script=script,
    )


def _render_password_form(provider, next_path: str) -> str:
    """Render a username/password form for a ``supports_password`` provider.

    The form is wired by :data:`_PASSWORD_FORM_SCRIPT` (a single delegated
    submit handler) to POST JSON to ``/auth/password-login`` and navigate
    on success. ``next_path`` is carried in a hidden field; it has already
    been validated same-origin by the caller and is HTML-escaped here as
    defence in depth. The provider ``name`` is emitted in a ``data-``
    attribute (not a hidden input) so the script reads it without trusting
    form-field ordering.
    """
    pname = html.escape(provider.name, quote=True)
    plabel = html.escape(provider.display_name)
    safe_next = html.escape(next_path, quote=True) if next_path else ""
    return (
        f'      <form class="provider-form" data-provider="{pname}" '
        f'autocomplete="on">\n'
        f'        <div class="form-title">Sign in with {plabel}</div>\n'
        f'        <input type="hidden" name="next" value="{safe_next}">\n'
        f'        <label class="field">\n'
        f'          <span class="field-label">Username</span>\n'
        f'          <input class="field-input" type="text" name="username" '
        f'autocomplete="username" autocapitalize="none" '
        f'autocorrect="off" spellcheck="false" required>\n'
        f'        </label>\n'
        f'        <label class="field">\n'
        f'          <span class="field-label">Password</span>\n'
        f'          <input class="field-input" type="password" name="password" '
        f'autocomplete="current-password" required>\n'
        f'        </label>\n'
        f'        <div class="form-error" role="alert" hidden></div>\n'
        f'        <button class="provider-btn" type="submit">Sign in</button>\n'
        f'      </form>'
    )
