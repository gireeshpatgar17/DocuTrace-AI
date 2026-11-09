# Demonstration scenarios

Synthetic documents use fictional names and addresses and are created by `scripts/create_demo_data.py`. Three repeatable sets are stored under `data/demo/clean`, `data/demo/contextual_discrepancy`, and `data/demo/visual_manipulation`.

- Clean: consistent application, identity, address, salary slip and bank statement.
- Contextual discrepancy: mismatched name, address, date of birth, declared income and salary slip values across forms.
- Visual manipulation: original and altered synthetic image with a changed salary amount. Compare the pair; ELA/residual maps are heuristic and are not expected to flag every change.

Expected scenario descriptions are test guidance, not preloaded findings. Upload each scenario into a separate investigation and process it through the application.
