About
-----
*git-search-replace* is a small utility on top of plain `git` for performing project-wide search-and-replace only on git-controlled files. It applies its searches to filenames as well as their content. The underlying syntax for the search regex is Python's.

It is designed to be a bit more instructive to the developer, compared to hackish `bash` scripts around `sed`.

Key features are:

* By default, only act as grep to show what is going to change.
* Dry run mode '--diff' shows a unidiff of the changes that the search-and-replace would do, so that the developer can review for correctness. No working directory files are modified.
* Fix mode '--fix' performs the actual changes and associated 'git mv'.

Syntax
------
    Usage: gsr [options] [FROM-TO-REGEXES]

    Options:
      -h, --help            show this help message and exit
      -s STRING, --separator=STRING
                        The separator string the separates FROM and TO regexes
      -f, --fix             Perform changes in place
      -d, --diff            Use 'diff' util to show differences

The expressions are tuples in the form of FROM-SEPARATOR-TO, with SEPARATOR defaults to '///'. For example, it can be invoked as such:

    gsr old_name///new_name --diff

This would replace all places containing 'old_name' with 'new_name'.
