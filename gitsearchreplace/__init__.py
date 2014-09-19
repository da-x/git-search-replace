"""
Main git-search-replace module
"""

from optparse import OptionParser
import subprocess
import sys
import re
import tempfile
import os
import bisect

def run_subprocess(cmd):
    pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    output = pipe.communicate()[0]
    return output

def error(s):
    print "git-search-replace: error: " + s
    sys.exit(-1)

class Expression(object):
    def __init__(self, fromexpr, toexpr):
        self.fromexpr = fromexpr
        self.toexpr = toexpr

class GitSearchReplace(object):
    """Main class"""

    def __init__(self, separator=None, diff=None, fix=None, expressions=None):
        self.separator = separator
        self.diff = diff
        self.fix = fix
        self.expressions_str = expressions
        self.expressions = []

    def compile_expressions(self):
        if not self.expressions_str:
            error("no FROM-TO expressions specified")
            return

        expressions = []
        for expr in self.expressions_str:
            fromexpr, toexpr = expr.split(self.separator, 1)
            from_regex = re.compile(fromexpr)
            expressions.append(Expression(from_regex, toexpr))
        self.expressions = expressions

    def search_replace_in_files(self):
        filenames = run_subprocess(["git", "ls-files"]).splitlines()
        for filename in filenames:
            if not os.path.isfile(filename):
                continue
            fileobj = file(filename)
            filedata = fileobj.read()
            fileobj.close()

            if self.diff or self.fix:
                self.show_file(filename, filedata)
            else:
                self.show_lines_grep_like(filename, filedata)

        for filename in filenames:
            for expr in self.expressions:
                new_filename = filename
                new_filename = expr.fromexpr.sub(expr.toexpr, new_filename)
                if new_filename != filename:
                    print
                    print "rename-src-file: %s" % (filename, )
                    print "rename-dst-file: %s" % (new_filename, )
                    if self.fix:
                        dirname = os.path.dirname(new_filename)
                        if dirname and not os.path.exists(dirname):
                            os.makedirs(dirname)
                        cmd = ["git", "mv", filename, new_filename]
                        run_subprocess(cmd)

    def show_file(self, filename, filedata):
        new_filedata = filedata
        for expr in self.expressions:
            new_filedata = expr.fromexpr.sub(expr.toexpr, new_filedata)
        if new_filedata != filedata:
            self.act_on_possible_modification(filename, new_filedata)

    def show_lines_grep_like(self, filename, filedata):
        new_filedata = filedata
        expr_id = 0
        shown_lines = []
        for expr in self.expressions:
            lines = []
            line_pos = []
            pos = 0
            for line in new_filedata.split("\n"):
                lines.append(line)
                line_pos.append(pos)
                pos += len(line) + 1
            matches = expr.fromexpr.finditer(new_filedata)
            for match in matches:
                line_nr = bisect.bisect(line_pos, match.start())
                shown_lines.append('%s:%d:%s:%s' % (
                    filename, line_nr, expr_id*'_',
                    lines[line_nr - 1]))
            new_filedata = expr.fromexpr.sub(expr.toexpr, new_filedata)
            expr_id += 1
        shown_lines.sort()
        for line in shown_lines:
            print line

    def act_on_possible_modification(self, filename, new_filedata):
        if self.diff:
            print filename
            self.show_diff(filename, new_filedata)
        if self.fix:
            fileobj = open(filename, "w")
            fileobj.write(new_filedata)
            fileobj.close()

    def show_diff(self, filename, new_filedata):
        fileobj = None
        tempf = tempfile.mktemp()
        try:
            fileobj = open(tempf, "w")
            fileobj.write(new_filedata)
            fileobj.close()
            diff = run_subprocess(["diff", "-urN", filename, tempf])
            minus_matched = False
            plus_matched = False
            for line in diff.splitlines():
                if not minus_matched:
                    minus_matched = True
                    match = re.match("^--- ([^ ]+) (.*)$", line)
                    if match:
                        print "--- a/%s %s" % (filename,
                                               match.groups(0)[1], )
                        continue
                if not plus_matched:
                    plus_matched = True
                    match = re.match("^[+][+][+] ([^ ]+) (.*)$", line)
                    if match:
                        print "+++ b/%s %s" % (filename,
                                               match.groups(0)[1], )
                        continue
                print line
        finally:
            os.unlink(tempf)

    def run(self):
        self.compile_expressions()
        self.search_replace_in_files()


def main():
    """Main function"""
    parser = OptionParser(usage="usage: %prog [options] (FROM-SEPARATOR-TO...)")

    parser.add_option(
        "-s", "--separator", dest="separator", default="///",
        help="The separator string the separates FROM and TO regexes",
        metavar="STRING")

    parser.add_option("-f", "--fix",
        action="store_true", dest="fix", default=False,
        help="Perform changes in-place")

    parser.add_option("-d", "--diff",
        action="store_true", dest="diff", default=False,
        help="Use 'diff' util to show differences")

    (options, args) = parser.parse_args()
    gsr = GitSearchReplace(
        separator=options.separator,
        diff=options.diff,
        fix=options.fix,
        expressions=args)
    gsr.run()

__all__ = ["main"]
