# Tanjun contributing guidelines

First let me thank you in advanced for any contributions you may make to Tanjun; contributions are always welcome
and any amount of time spent on this project is greatly appreciated.

But before you get started contributing, it's recommended that you read through the following guide in-order to
ensure that any pull-requests you open can be at their best from the start.

### Pipelines

The most important thing to consider while contributing towards Tanjun is the checks the library's run against.
While these are run against all PRs by Github Actions, you can run these locally before any PR is opened using Nox.

To run the tests and checks locally you'll have to go through the following steps.

1. Ensure your current working directory is Tanjun's top-level directory.
2. `pip install -r nox-requirements.txt` to install Nox.
3. Use `nox -s` to run the default tasks.

A list of all the available tasks can be found by running `nox -l` with blue names being the tasks which are run
by default when `nox -s` is called alone. To call specific tasks you just call `nox -s name1 name2` where any number
of tasks can be called at once by specifying their name after `-s`.

It's worth noting that the reformat nox task will reformat additions to the project in-order to make them match
the expected style and is one of the default tasks and that nox will generate virtual environments for each task
instead of pollution the environment it was installed into.

### Documentation style

This project's documentation is written in [numpydoc style](https://numpydoc.readthedocs.io/en/latest/format.html)
and should also use styles which are specific to [pdoc](https://pdoc.dev/docs/pdoc.html).

A few examples of pdoc style would be:

* Links: Unlike sphinx, regardless of whether you're linking to a module, class, function or variable the link will
  always be in the style of `` `link.to.thing` `` with no type information included and relative links being supported
  for types in the current module (e.g. `` `Class.attribute` ``.
* Documenting fluent methods: The return type for fluent methods should be given as `Self` with the description for it
  following the lines of something like "the {x} instance to enable chained calls".

### CHANGELOG.md
 
While you aren't required to update the changelog as a contributor, a reference on the schema CHANGELOG.md follows
can be found [here](https://keepachangelog.com/en/1.0.0/).

It should be noted that not all changes will be included in the changelog (since some are just not significant enough)
and it comes down to a maintainer's discretion as to what is included. 

### Tests

All changes contributed to this project should be tested. This repository uses pytest and `nox -s test` for an easier and
less likely to be problematic way to run the tests.

### Type checking

All contributions to this project will have to be "type-complete" and, while [the nox tasks](###Pipelines) let you check
that the type hints you've added/changed are type safe,
[pyright's type-completness guidelines](https://github.com/microsoft/pyright/blob/main/docs/typed-libraries.md) and
[standard typing library's type-completness guidelines](https://github.com/python/typing/blob/master/docs/libraries.md) are
good references for how projects should be type-hinted to be `type-complete`.

---
**NOTES**

* This project deviates from the symbolic python standard of importing types from the typing module and instead
  imports the typing module itself to use generics and types in it like `typing.Union` and `typing.Optional`.
* Since this project supports python 3.9+, the `typing` types which were deprecated by
  [PEP 585](https://www.python.org/dev/peps/pep-0585/) should be avoided in favour of their `collections.abc`,
  builtin, `re` and `contextlib` equivalents.
* The standard way for using `collections.abc` types within this project is to `import collections.abc as collections`.
---

### Versioning

This project follows [semantic versioning 2.0.0](https://semver.org/) and [PEP 440](https://www.python.org/dev/peps/pep-0440/).

### General enforced style

* All modules present in Tanjun should start with the commented out licence (including the source encoding and cython
 languave level declarations), a relevant component documentation string, `from __future__ import annotations`, an
 `__all__` declaration and then imports. For an example see any of Tanjun's current components.
* Public type variables (e.g. `CommandCallbackSig = collections.Callable[..., collections.Awaitable[None]]` should be
  included in the `__all__` of the module they're declared in but not included in the `__all__` of any parent modules
  and should also be documented.
* [pep8](https://www.python.org/dev/peps/pep-0008/) should be followed as much as possible with notable cases where its
  ignored being that [black](https://github.com/psf/black) style may override this.
* The maximum character count for a line is 120 characters and this may only ever be ignored for docstrings where types
  go over this count, in which case a `# noqa: E501 - Line too long` should be added after the doc-string (on the same
  line as its trailing `"""`.
* All top-level modules should be included explicitly imported into `Tanjun.__init__` and included in
  `Tanjun.__init__.__all__` for type-completness with only the most important of their contents needing to be included in
  `Tanjun.__init__.__all__`.


