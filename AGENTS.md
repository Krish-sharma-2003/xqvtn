# Rules for AI coding assistants
- Read SPEC.md first. Do only the milestone I ask for. Do not touch unrelated files.
- Never invent data fields or endpoints. If the spec is unclear, ask one question instead of guessing.
- Python 3.11+, type hints, small pure functions, docstring on each module saying what and why. No pandas.
- Every logic function gets a pytest test. Run the tests and show the result before saying done.
- No secrets, no .env committed, no hard-coded absolute paths.
- Keep it simple: no extra libraries unless needed, and say why when adding one.
- After finishing, print a 5-line summary: files changed, how to run, what to verify manually.
- Think and respond in English only. Keep reasoning short; do not re-plan what SPEC.md already states.