# Issue tracker: personal GitHub

Issues and specifications for this project live in GitHub Issues. Use the `gh`
CLI for issue operations.

## Ownership boundary

- Required repository owner: `rajpaladitiya`
- Organization-owned repositories are prohibited.
- Never create or mutate repositories, issues, pull requests, labels, releases,
  secrets, settings, or workflows under EC-aware or another organization.
- Before the first GitHub write in a session, verify the destination with:
  `gh repo view --json nameWithOwner,owner`
- If the destination is not owned by `rajpaladitiya`, stop without writing.
- If no remote exists, create or select a personal repository before using the
  issue tracker.

## Conventions

- Create: `gh issue create --title "..." --body "..."`
- Read: `gh issue view <number> --comments`
- List: `gh issue list --state open --json number,title,body,labels,comments`
- Comment: `gh issue comment <number> --body "..."`
- Add a label: `gh issue edit <number> --add-label "..."`
- Remove a label: `gh issue edit <number> --remove-label "..."`
- Close: `gh issue close <number> --comment "..."`
- Infer the repository from the verified Git remote.

## Pull requests as a triage surface

**PRs as a request surface: no.**

Pull requests are implementation and review surfaces, not substitutes for
feature requests or planning issues.

## Skill operations

When an engineering skill says “publish to the issue tracker,” create a GitHub
issue in the verified personal repository.

When a skill says “fetch the relevant ticket,” use:

`gh issue view <number> --comments`

## Wayfinding operations

- A map is one issue labelled `wayfinder:map`.
- Child work is represented by linked sub-issues where GitHub supports them.
- Otherwise, use a task list in the map and add `Part of #<map>` to each child.
- Use `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, or
  `wayfinder:task` to identify the child type.
- Use GitHub issue dependencies for blockers when available.
- Claim work by assigning the issue to the active developer.
- Resolve work with a summary comment before closing the issue.
