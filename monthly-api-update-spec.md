# Monthly API Update Spec

## Goal

Run a monthly GitHub Action that checks:

- official NHI price refresh logic
- drug indication / coverage semantics
- exported API consistency
- calculator and Netlify function smoke tests

## Scope

The workflow is a validation job, not an automatic DB writer.

It runs:

1. `python update_official_prices.py --dry-run`
2. `python tools/check_api.py`

## Schedule

- Monthly on the 23rd at 15:15 UTC
- Equivalent to 23:15 Asia/Taipei

## Failure handling

If either command fails, GitHub Actions marks the run red.
That gives a visible signal that price data, indication text, exported API
payloads, or smoke tests need review.

## Manual trigger

The workflow can also be started manually from the GitHub Actions tab.
