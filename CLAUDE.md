# ERP Decision Lab — Root Router (L0)

Operational-decision-support ERP training platform. Fills the gap between
high-level strategy simulations and daily transactional decision-making.
Core thesis: localization (tax, currency, accounting rules per country) is
proof the system teaches real business logic, not a UI skin.

## Read first
CONTEXT.md — what the product is, what is verified true today, what is left.
Then rules/ENGINEERING.md, rules/PRODUCT.md, rules/SCALING.md, BREAK.md and
DEBT.md before any change. PROMPT-02.md is the current build-to-v1.0 brief.

## Routing Table
| Job Slug            | Workspace    | Entry Stage    |
|----------------------|-------------|-----------------|
| `generate-scenario`  | `scenarios/` | `01-generate`  |
| `score-decision`     | `decisions/` | `01-score`     |
| `recall-learner`     | `tutor/`     | `01-recall`    |
| `serve-frontend`     | `static/`    | n/a (static)   |

## Facts (single source of truth)
- Code: src/erpsim/. DB: SQLModel — SQLite by default, Postgres via ERPSIM_DATABASE_URL.
- Localization rules: config/locales/*.yaml — ONE FILE PER COUNTRY.
  A new country is a new config file, never new code.
- Scenario templates: config/templates/*.yaml — ONE FILE PER INDUSTRY.
  A new industry is a new config file, never new code.
- Run: uvicorn erpsim.main:app --reload --app-dir src
