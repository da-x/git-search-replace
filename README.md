# About

*git-search-replace* is a small utility on top of plain `git` for performing project-wide search-and-replace only on git-controlled files. It applies its searches to filenames as well as their content. The underlying syntax for the search regex is Python's.

It is designed to be a bit more instructive to the developer, compared to hackish `bash` scripts around `sed`.

An accompanying utility is *gsr-branch*, which does the same thing as *git-search-replace* but on the *history of a branch* (using `git filter-branch`). It's especially useful for fixing a whole bunch of commits at once when the fix is a simple search & replace (retaining a clean history).

Key features are:

* By default, only act as grep to show what is going to change.
* Dry run mode (`--diff`) shows a unidiff of the changes that the search-and-replace would do, so that the developer can review for correctness. No working directory files are modified.
* Fix mode (`--fix`) performs the actual changes and associated 'git mv'.

### Wait, but my awesome editor can already do that!

That's right, but when you are working within a group of people and everyone has their own editor, it becomes quite useful to be able to communicate renames in a way that everyone can easily reproduce, and during conflict resolution it is even more useful (see: [git-mediate](https://github.com/Peaker/git-mediate)). This comes handy especially in commit message, for instance:

```
    commit 3ed68e243e76783fa2b92fa33f7e4681f0246332
    Author: Dan Aloni <alonid@gmail.com>
    Date:   Sun Jul 26 18:42:52 2015 +0300

    module: renamed with: gsr foo///bar -f

```

# Syntax

```
Usage: gsr [options] (FROM-SEPARATOR-TO...)
       gsr [options] -p FROM1 TO1  FROM2 TO2 ...

Options:
  -h, --help            show this help message and exit
  -s STRING, --separator=STRING
                        The separator string the separates FROM and TO
                        regexes. /// by default, if -p is not specified
  -p, --pair-arguments  Use argument pairs for FROM and TO regexes. Useful with
                        shell expansion. E.g: colo{,u}r
  -f, --fix             Perform changes in-place
  -d, --diff            Use 'diff' util to show differences
  -e PATTERN, --exclude=PATTERN
                        Exclude files matching the provided globbing pattern
                        (can be specified more than once)
  -i PATTERN, --include=PATTERN
                        Include files matching the provided globbing pattern
                        (can be specified more than once)
  --no-renames          Don't perform renames
```

The expressions are tuples in the form of FROM-SEPARATOR-TO, with SEPARATOR defaults to '///'.

The `-e` and `-i` options abide by the following rules:

* Each of these can be passed multiple times.
* The order matters, as they are checked in that order for each file. Last matcher takes effect when matched.
* If neither is passed, all files are included by default.
* If `-i` if given first, then by default all files are excluded.

# Examples

Shell escaping needs to be taken into consideration. The examples below should work with the major UNIX shells.

    gsr old_name///new_name --diff

This shows a diff that represents the replacement of 'old_name' with 'new_name'.

    gsr \\bold_name\\b///new_name --fix

This uses Python regex expression \b for matching at word boundaries for whole identifiers. This invocation will perform changes in-place because of '--fix'.

    gsr 'things with space///with other stuff' --diff

Note that shells properly de-escape the commas from the expression above.

Example of using *gsr-branch*:

    gsr-branch.py HEAD~10 '(\.|\-\>)ol_header///\1header'

Runs the search replace regex over the last 10 commits, modifying them in-place. The regex will replace the string `.ol_header` (or `->ol_header`) with `.header` (or `->header`).
