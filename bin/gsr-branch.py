#!/usr/bin/env python
import os
import sys
import re

from plumbum import local, cli
from plumbum import commands
from plumbum import FG

git = local["git"]

@cli.Predicate
def GitRevision(rev):
    '''valid git revision, branch name, or tag'''
    git_exit, so, se = git.run(["describe", "--always", rev], retcode=None)
    if git_exit != 0:
        raise ValueError(se)

    git_exit, so, se = git.run(["merge-base", "--is-ancestor", rev, "HEAD"], retcode=None)
    if git_exit != 0:
        raise ValueError("Not an ancestor of current head: %s" % (rev,))

    return rev

@cli.Predicate
def GsrArg(expr):
    '''valid gsr expression'''
    match = re.match(".+///", expr)
    if match is None:
        raise ValueError("GSR expression must contain the seperator (///)")
    return expr

def get_commit_msg(editor_cmd, *gsr_args):
    mktemp = local["mktemp"]
    commit_msg_file = mktemp("/tmp/gsr-commit-msg.XXXXXX").strip()
    gsr_base = ["{MODULE_NAME_HERE}: gsr -f"]
    for arg in gsr_args:
        gsr_base.append("'%s'" % (arg,))
    with open(commit_msg_file, "w") as f:
        f.write(" ".join(gsr_base))
        f.write("\n\n# Please enter the commit message for your changes. Lines starting")
        f.write("\n# with '#' will be ignored, and an empty message aborts the commit.")
    editor = local[editor_cmd]
    editor[commit_msg_file] & FG
    # 'git commit -F' doesn't actually ignore the '#' lines, so we remove them ourselves
    lines = [l for l in open(commit_msg_file, "r").readlines() if not l.startswith('#')]
    with open(commit_msg_file, "w") as f:
        f.write('\n'.join(lines))
    return commit_msg_file

class MyApp(cli.Application):
    MODE_INSERT = 'insert'
    MODE_EDIT = 'edit'

    git_editor = git("var", "GIT_EDITOR").strip()
    force_filter_branch = cli.Flag(["-f", "--force"], help = "Pass -f to git-filter-branch")
    internal_edit_todo = cli.Flag(["-i", "--internal-edit-todo"], requires = ["-t"],
                                  help = "Edit the git-rebase todo file. FOR INTERNAL USE ONLY")
    rebase_todo_filename = cli.SwitchAttr(["-t", "--internal-todo-filename"], requires = ["-i"],
                                          argtype = cli.ExistingFile, argname = "<file>",
                                          help = "Full path of the git-rebase todo file. FOR INTERNAL USE ONLY")
    gsr_cmd = cli.SwitchAttr(["-g", "--gsr-cmd"], argtype = str, argname = "<cmd>",
                             default = os.path.dirname(sys.argv[0]) + "/git-search-replace.py",
                             help = "Path to git-search-replace.py")
    commit_msg = cli.SwitchAttr(["-c", "--commit-msg"], argtype = str, argname = "<msg>",
                                excludes = ["-F"],
                                help = "Provide the git log message for insert mode")
    commit_msg_file = cli.SwitchAttr(["-F", "--commit-msg-file"],
                                     argtype = cli.ExistingFile, argname = "<file>",
                                     excludes = ["-c"],
                                     help = "Provide the git log message for insert mode (as filename)")
    mode = cli.SwitchAttr(["-m", "--mode"], argtype = cli.Set(MODE_INSERT, MODE_EDIT), argname = "mode",
                          default = MODE_EDIT,
                          help = '''Whether to insert a new commit at base, or edit the base commit.
                                    Use insert when renaming something that's already in upstream,
                                    and edit when renaming something that was only added in the current branch.''')

    def edit_internal(self, base, *args):
        gsr_base = ["%s -f" % (self.gsr_cmd,)]
        for arg in args:
            gsr_base.append("'%s'" % (arg,))
        full_gsr_cmd = " ".join(gsr_base)

        filter_branch_params = ["filter-branch"]
        if self.force_filter_branch:
            filter_branch_params.append("-f")
        filter_branch_params.extend(["--tree-filter", full_gsr_cmd, "%s..HEAD" % (base,)])
        try:
            # __getitem__ is the same as [] but accepts a list
            git.__getitem__(filter_branch_params) & FG
        except commands.processes.ProcessExecutionError:
            print "Error running git filter-branch. See error above"
            return False
        print "All done!"
        print "Check the new branch and then remove the backup ref."
        print "To remove all backup refs, run the command:"
        print 'git for-each-ref --format="%(refname)" refs/original/ | xargs -n 1 git update-ref -d'
        return True

    def edit(self, base, *args):
        if len(args) == 0:
            self.help()
            sys.exit(1)
        if not self.edit_internal(base, *args):
            sys.exit(1)

    def insert(self, base, *args):
        if len(args) == 0:
            self.help()
            sys.exit(1)
        old_head = git("log", "-1", "--pretty=format:%h")
        delete_commit_file = None
        if self.commit_msg is None:
            if self.commit_msg_file is None:
                self.commit_msg_file = get_commit_msg(self.git_editor, *args)
                delete_commit_file = self.commit_msg_file
            rebase_todo_editor = "%s %s -i -F '%s' -t " % (sys.argv[0], base, self.commit_msg_file)
        else:
            rebase_todo_editor = "%s %s -i -c '%s' -t " % (sys.argv[0], base, self.commit_msg)
        local.env["GIT_EDITOR"] = rebase_todo_editor
        git["rebase", "-i", base] & FG
        if delete_commit_file is not None:
            os.unlink(delete_commit_file)
        if not self.edit_internal(base, *args):
            print "Restoring old branch state"
            git("reset", "--hard", old_head)
            sys.exit(1)

    def edit_todo(self, base, *args):
        assert(len(args) == 0)
        if self.commit_msg is None:
            assert(self.commit_msg_file is not None)
            output = ["exec git commit --allow-empty -F '%s'\n" % self.commit_msg_file]
        else:
            output = ["exec git commit --allow-empty -m '%s'\n" % self.commit_msg]
        f = open(self.rebase_todo_filename)
        for line in f:
            if line.startswith('pick'):
                base_match = re.match("^%s" % base, line[5:])
                assert(base_match is None)
                base_match = re.match("^%s" % line[5:], base)
                assert(base_match is None)
                output.append(line)
        f.close()
        f = open(self.rebase_todo_filename, "w")
        f.write(''.join(output))
        f.close()

    @cli.positional(GitRevision, GsrArg)
    def main(self, base_revision, *gsr_args):
        if self.internal_edit_todo:
            self.edit_todo(base_revision, *gsr_args)
        elif self.mode == MyApp.MODE_EDIT:
            self.edit(base_revision, *gsr_args)
        elif self.mode == MyApp.MODE_INSERT:
            self.insert(base_revision, *gsr_args)
        else:
            raise Exception("unknown mode: %r" % (self.mode,))

if __name__ == "__main__":
    MyApp.run()
