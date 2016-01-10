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
import fnmatch

def run_subprocess(cmd):
    pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    output = pipe.communicate()[0]
    return output

def error(s):
    print "git-search-replace: error: " + s
    sys.exit(-1)

class Expression(object):
    def __init__(self, fromexpr, toexpr, big_g):
        self.fromexpr = fromexpr
        self.toexpr = toexpr
        self.big_g = big_g

def underscore_to_titlecase(name):
    l = []
    for p in name.split('_'):
        if p:
            p = p[:1].upper() + p[1:]
        l.append(p)
    return ''.join(l)

def titlecase_to_underscore(name):
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

class GitSearchReplace(object):
    """Main class"""

    def __init__(self, separator=None, diff=None, fix=None, exclude=None, expressions=None):
        self.separator = separator
        self.diff = diff
        self.fix = fix
        self.exclude = exclude
        self.expressions_str = expressions
        self.expressions = []
        self.stage = None

    BIG_G_REGEX = re.compile(r"[\]G[{][^}]*[}]")
    def calc_big_g(self, big_g_expr):
        """Transform the special interpolated \G{<python>}"""
        parts = []
        prefix = r'\G{'
        oparts = big_g_expr.split(prefix)
        parts = [oparts[0]]
        for part in oparts[1:]:
            if '}' in part:
                x = part.find('}')
                parts.append(prefix + part[:x+1])
                parts.append(part[x+1:])
            else:
                parts.append(part)

        def replacer_func(G):
            def m(i):
                return G.groups(0)[i]
            gen = []
            dotslash = '/'
            if self.stage == 'content':
                dotslash = '.'
            namespace = dict(
                G=G,
                m=m,
                underscore_to_titlecase=underscore_to_titlecase,
                titlecase_to_underscore=titlecase_to_underscore,
                dotslash=dotslash,
            )
            for part in parts:
                if part.startswith(r'\G{'):
                    gen.append(eval(part[3:-1:], namespace))
                else:
                    gen.append(part)
            return ''.join(gen)
        return replacer_func

    def compile_expressions(self):
        if not self.expressions_str:
            error("no FROM-TO expressions specified")
            return

        expressions = []
        for expr in self.expressions_str:
            fromexpr, toexpr = expr.split(self.separator, 1)
            toexpr = toexpr
            big_g = None
            if self.BIG_G_REGEX.search(toexpr):
                big_g = self.calc_big_g(toexpr)
            from_regex = re.compile(fromexpr)
            expressions.append(Expression(from_regex, toexpr, big_g))
        self.expressions = expressions

    def sub(self, expr, content, stage):
        self.stage = stage
        if expr.big_g:
            return expr.fromexpr.sub(expr.big_g, content)
        return expr.fromexpr.sub(expr.toexpr, content)

    def search_replace_in_files(self):
        filenames = run_subprocess(["git", "ls-files"]).splitlines()
        filtered_filenames = []
        for filename in filenames:
            excluded = False
            for exclude in self.exclude:
                if fnmatch.fnmatch(filename, exclude):
                    excluded = True
                    continue
            if excluded:
                continue
            filtered_filenames.append(filename)

        for filename in filtered_filenames:
            if not os.path.isfile(filename):
                continue
            fileobj = file(filename)
            filedata = fileobj.read()
            fileobj.close()

            if self.diff or self.fix:
                self.show_file(filename, filedata)
            else:
                self.show_lines_grep_like(filename, filedata)

        for filename in filtered_filenames:
            for expr in self.expressions:
                new_filename = filename
                new_filename = self.sub(expr, new_filename, 'filename')
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
            new_filedata = self.sub(expr, new_filedata, 'content')
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
            new_filedata = self.sub(expr, new_filedata, 'content')
            expr_id += 1
        shown_lines.sort()
        for line in shown_lines:
            print line

    def act_on_possible_modification(self, filename, new_filedata):
        if self.diff:
            print "diff -urN a/%s b/%s" % (filename, filename)
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

    parser.add_option("-e", "--exclude",
        dest="exclude", default=[], action="append",
        help="Exclude files matching the provided globbing "
                      "pattern (can be specified more than once)")

    (options, args) = parser.parse_args()
    gsr = GitSearchReplace(
        separator=options.separator,
        diff=options.diff,
        fix=options.fix,
        exclude=options.exclude,
        expressions=args)
    gsr.run()

__all__ = ["main"]
