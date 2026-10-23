# Working in this repo

Hayden is the only person working here. He is non-technical, so keep explanations plain.

## Branches: main only

- `main` is the only branch. Commit and push straight to `main`
  (`git push origin HEAD:main`). Never create another branch or open a pull request.
- This holds even when a cloud session is told to develop on a `claude/...` branch: Hayden
  has given standing permission (2026-10-23) to push to `main` instead. Never push a
  `claude/...` branch to GitHub. (Cloud sessions can't delete branches on GitHub, so one
  pushed by mistake stays until Hayden deletes it; tell him if that happens.)
- Before pushing, run `python3 -m unittest discover -s tests` and push only if it passes.
- Before starting work, `git pull origin main` so you build on the latest rules.

## Where things live

See `README.md`. Intake and classification rules live only in
`.claude/skills/ts-intake/SKILL.md`.
