# Known Pitfalls — Index

Pitfalls are documented inline at the top of each reference file. This index links to the relevant file.

| Pitfall | Reference File |
|---------|---------------|
| `numval()`/`val()` return null — use `toNumber()` | [grel-functions.md](grel-functions.md) |
| Output dataset creation: `with_new_output` vs `with_output` | [prepare-recipe.md](prepare-recipe.md) |
| Schema propagation required after config | [prepare-recipe.md](prepare-recipe.md), [join-recipe.md](join-recipe.md), [group-recipe.md](group-recipe.md) |
| Case-sensitive join keys | [join-recipe.md](join-recipe.md) |
| Prefix double-underscore trap | [join-recipe.md](join-recipe.md) |
| DROP mode unreliable for column exclusion | [join-recipe.md](join-recipe.md) |
| `count_distinct` → `_distinct` suffix naming | [group-recipe.md](group-recipe.md) |
| `first`/`last` require `orderColumn` | [group-recipe.md](group-recipe.md) |
| Python recipe uses `with_new_output_dataset()` not `with_new_output()` | [python-recipe.md](python-recipe.md) |
| `recipe.run()` already waits — no `wait_for_completion()` | [python-recipe.md](python-recipe.md) |
| Silent data issues — always sample output | All recipes |
