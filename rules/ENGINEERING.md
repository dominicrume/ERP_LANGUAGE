# Engineering Rules

1. Contract before code. Every workspace stage has a CONTEXT.md; code
   implements the contract, never invents past it.
2. TEMPLATES x LOCALES ARE DATA, NOT CODE. A scenario = template x locale.
   Adding a country or an industry must never require touching src/.
3. One change at a time, committed. Deterministic by default — same
   template+locale+seed produces the same scenario, forever, reproducibly.
4. Every stage ships a contract test AND a loud-failure test. Unknown
   locale/template -> structured error, never a silent default.
5. No hardcoded config. Runtime values live in config.yaml or the
   locale/template YAML files — never inline in Python.
6. The frontend calls the API; it never re-implements scoring or
   localization logic in JavaScript. One brain, one place.
