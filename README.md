# About

*git-search-replace* is a small utility on top of plain `git` for performing project-wide search-and-replace only on git-controlled files. It applies its searches to filenames as well as their content. The underlying syntax for the search regex is Python's.

It is designed to be a bit more instructive to the developer, compared to hackish `bash` scripts around `sed`.

Key features are:

* By default, only act as grep to show what is going to change.
* Dry run mode '--diff' shows a unidiff of the changes that the search-and-replace would do, so that the developer can review for correctness. No working directory files are modified.
* Fix mode '--fix' performs the actual changes and associated 'git mv'.

### Wait, but my awesome editor can already do that!

That's right, but when you are working within a group of people and everyone has their own editor, it becomes quite useful to be able to communicate renames in a way that everyone can easily reproduce, and during conflict resolution it is even more useful (see: [resolve-trivial-conflicts](https://github.com/ElastiLotem/resolve-trivial-conflicts)). This comes handy especially in commit message, for instance:

```
    commit 3ed68e243e76783fa2b92fa33f7e4681f0246332
    Author: Dan Aloni <alonid@gmail.com>
    Date:   Sun Jul 26 18:42:52 2015 +0300

    module: renamed with: gsr foo///bar -f

```

# Syntax

    Usage: gsr [options] (FROM-SEPARATOR-TO...)

    Options:
      -h, --help            show this help message and exit
      -s STRING, --separator=STRING
                        The separator string which separates FROM regex and TO expression
      -f, --fix             Perform changes in-place
      -d, --diff            Use 'diff' util to show differences
      -p GSR_PATH, --path=GSR_PATH
                            Limit the search to files matching the provided
                            globbing pattern (can be specified more than once)
      -e EXCLUDE, --exclude=EXCLUDE
                            Exclude files matching the provided globbing pattern
                            (can be specified more than once)

The expressions are tuples in the form of FROM-SEPARATOR-TO, with SEPARATOR defaults to '///'.

# Examples

Shell escaping needs to be taken into consideration. The examples below should work with the major UNIX shells.

    gsr old_name///new_name --diff

This shows a diff that represents the replacement of 'old_name' with 'new_name'.

    gsr \\bold_name\\b///new_name --fix

This uses Python regex expression \b for matching at word boundaries for whole identifiers. This invocation will perform changes in-place because of '--fix'.

    gsr 'things with space///with other stuff' --diff

Note that shells properly de-escape the commas from the expression above.
