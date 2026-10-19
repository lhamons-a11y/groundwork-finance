# Contributing to Groundwork

Thank you for looking. Groundwork is maintained by one person, so please start small.

- **Bugs:** open an issue with what you did, what you expected, what happened, and the version (Settings → About).
  Use made-up figures. Never post real statements, account numbers or bank exports.
- **Ideas:** open an issue to discuss before writing code. Groundwork has firm rules (below), and a change that
  breaks one won't be merged however good the code is.
- **Pull requests:** welcome for bugs, and for ideas that were agreed in an issue first.
- **Security problems:** see `SECURITY.md`, not a public issue.

By contributing, you agree that your contribution is licensed under the GPL v3, the same as the rest of Groundwork.

## The rules a change must keep

- **The person decides.** Groundwork proposes and asks; it never changes a person's records, makes a rule, or
  moves money on its own.
- **Nothing leaves the computer** unless the Privacy page says so, and then only what it says.
- **No figure without a source.** Every number shown traces back to the person's own records or a named, public
  source. The AI never invents one.
- **Works with AI off.** Every core feature works without the local AI.

## Running the tests

```bash
pip install -r requirements.txt
python smoke_test.py
```

The smoke test boots the server against a throwaway database and checks the critical paths end to end. A pull
request must keep it passing (`0 failed`), and a new feature adds its own section in `smoke_sections/`. Some
sections run the page's scripts in Node.js; install Node to run those too.
