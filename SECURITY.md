# Security

## Reporting something

Open a private security advisory on the repository
(Security → Report a vulnerability). Please do not open a public issue for
anything exploitable. A first response should take a couple of working days.

## What this software is today

A teaching tool for operational ERP decisions, run as a single process
against SQLite or Postgres. It is suitable for a local demo or a supervised
pilot. **It is not ready to be exposed to the open internet**, for one
reason above all:

- **There are no accounts.** A learner is a name typed into a box, and the
  instructor builder is open to anyone who can reach the app. Anyone can
  read any learner's record by guessing the name, and anyone can publish a
  scenario. This is recorded in DEBT.md with a repay trigger, and it is the
  work that has to land before hosting.

## What is already handled

| Concern | How |
|---|---|
| Instructor-authored text reaching a learner's browser | Escaped at render; option ids travel in data attributes, never inline handlers. Proven by a stored-XSS test that publishes markup and asserts it never executes. |
| Path traversal through template or locale ids | Ids must match `^[a-z0-9_]{1,64}$` before any path is built. |
| Learner ids used as paths | Trimmed, non-empty, no slashes, 64 characters maximum. |
| One learner acting in another's sitting | A named run refuses any other name (403); an anonymous run cannot be claimed. |
| Replaying a decision to inflate a score | A decision can be answered once per run (409). |
| Oversized or flooding requests | Body size limit and a per-client write limit, both configurable. |
| Clickjacking, sniffing, injected resources | `X-Frame-Options`, `X-Content-Type-Options`, a Content-Security-Policy allowing only the two font CDNs. |
| Crashes leaking internals | A single handler returns a request id and no stack trace. |
| Dependency vulnerabilities | Five runtime dependencies, audited with `pip-audit`; none known at the last check. |
| Secrets | None in the repository. The only configuration is a database URL and deployment switches (`.env.example`). |

## Running it safely

- Keep it on a private network or behind an authenticating proxy until
  accounts exist.
- Set `ERPSIM_PUBLIC_DOCS=false` and `ERPSIM_HTTPS_ONLY=true` when hosted.
- Back the database up before applying migrations; they are versioned and
  tested, but they are still the only thing that touches learner history.
