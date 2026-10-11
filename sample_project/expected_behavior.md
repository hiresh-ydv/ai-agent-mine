# Sample project -- expected behavior

This folder is the demo repair target. Each module contains exactly one
deliberate bug and ships with an independent test that encodes the expected
behavior. Run the suite from inside this folder:

```bash
python -m pytest -q
```

The tests fail until the bugs are fixed.

| Module | Bug | Expected behavior |
| --- | --- | --- |
| `buggy_discount.py` | Percentage subtracted as a whole number | `apply_discount(100, 20) == 80.0`, `apply_discount(50, 10) == 45.0` |
| `buggy_cart.py` | Loop bound omits the final item | `cart_total([10, 20, 30]) == 60` |
| `buggy_pricing.py` | Exclusive comparison at the boundary | `is_eligible_for_free_shipping(50.0, 50.0) is True` |

Example Mini Codex invocation from this repository root:

```bash
uv run mini-codex --project ./sample_project
```
