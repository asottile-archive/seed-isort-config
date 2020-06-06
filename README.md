[![Build Status](https://dev.azure.com/asottile/asottile/_apis/build/status/asottile.seed-isort-config?branchName=master)](https://dev.azure.com/asottile/asottile/_build/latest?definitionId=20&branchName=master)
[![Azure DevOps coverage](https://img.shields.io/azure-devops/coverage/asottile/asottile/20/master.svg)](https://dev.azure.com/asottile/asottile/_build/latest?definitionId=20&branchName=master)

seed-isort-config
=================

Statically populate the `known_third_party` `isort` setting.

[`isort`][isort] when run in isolation is not the best at determining what
dependencies are third party.

[`aspy.refactor_imports`][aspy.refactor_imports] is fortunately much better at
this static analysis.

Why not just use [`reorder-python-imports`][reorder_python_imports]?  Well, it
lacks a few features provided by `isort` (intentionally).

What this script does is seeds the `known_third_party` isort configuration
automatically.

## install

`pip install seed-isort-config`

## usage

`seed-isort-config` provides a single executable by the same name.  Run it
inside a `git` repository.

To specify custom application roots (such as with the `src` pattern) pass a
colon-separated `--application-directories` parameter.

Files may be excluded from the process using the `--exclude` flag.
This argument takes a python regular expression.

For a full list of arguments, see `seed-isort-config --help`.

## getting started

`seed-isort-config` looks for an existing `known_third_party` setting in an
isort configuration file.  It will modify that if it exists, otherwise it'll
create a brand new `.isort.cfg` file.

The easiest way to get started is to just add a blank `known_third_party =`
section to your isort configuration (or `known_third_party = []` if you are
using `pyproject.toml`).

## usage with pre-commit

This works especially well when integrated with [`pre-commit`][pre-commit].


```yaml
-   repo: https://github.com/asottile/seed-isort-config
    rev: v2.2.0
    hooks:
    -   id: seed-isort-config
-   repo: https://github.com/timothycrosley/isort
    rev: 4.3.21  # pick the isort version you'd like to use from https://github.com/timothycrosley/isort/releases
    hooks:
    -   id: isort
```

In this configuration, `seed-isort-config` will adjust the `known_third_party`
section of the `isort` configuration before `isort` runs!

Note that `seed-isort-config` doesn't act like a normal pre-commit linter so
file exclusion must be configured through `args: [--exclude=...]` instead.
For example: `args: [--exclude=tests/.*\.py]`.

[isort]: https://github.com/timothycrosley/isort
[aspy.refactor_imports]: https://github.com/asottile/aspy.refactor_imports
[reorder_python_imports]: https://github.com/asottile/reorder_python_imports
[pre-commit]: https://github.com/pre-commit/pre-commit
