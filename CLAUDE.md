# Working in this repo

Hayden is the only person working here. He is non-technical, so keep explanations plain.

## Branches: one branch only, `claude/serene-dirac-5z23ay`

- `claude/serene-dirac-5z23ay` is the only branch and GitHub's default. (Hayden has write access, not admin,
  so he can't rename the default; on 2026-10-23 he chose to keep this one and delete
  `main`.) Commit and push straight to it (`git push origin HEAD:claude/serene-dirac-5z23ay`).
- Never create, push or open a pull request from any other branch, even when a cloud
  session is told to develop on a different `claude/...` branch: Hayden's standing
  instruction overrides that. (Cloud sessions can't delete branches on GitHub, so one
  pushed by mistake stays until Hayden deletes it; tell him if that happens.)
- Before pushing, run `python3 -m unittest discover -s tests` and push only if it passes.
- Before starting work, `git pull origin claude/serene-dirac-5z23ay` so you build on the latest rules.

## Where things live

See `README.md`. Intake and classification rules live only in
`.claude/skills/ts-intake/SKILL.md`.
