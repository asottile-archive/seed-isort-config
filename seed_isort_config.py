from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import ast
import io
import os.path
import re
import subprocess

from aspy.refactor_imports.classify import classify_import
from aspy.refactor_imports.classify import ImportType


THIRD_PARTY_RE = re.compile(r'^known_third_party(\s*)=(\s*?)[^\s]*$', re.M)


class Visitor(ast.NodeVisitor):
    def __init__(self):
        self.third_party = set()

    def _maybe_append_name(self, name):
        name, _, _ = name.partition('.')
        if classify_import(name) == ImportType.THIRD_PARTY:
            self.third_party.add(name)

    def visit_Import(self, node):
        for name in node.names:
            self._maybe_append_name(name.name)

    def visit_ImportFrom(self, node):
        if not node.level:
            self._maybe_append_name(node.module)


def third_party_imports(filenames):
    visitor = Visitor()
    for filename in filenames:
        with open(filename, 'rb') as f:
            visitor.visit(ast.parse(f.read()))
    return visitor.third_party


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--extra', action='append', default=[])
    args = parser.parse_args(argv)

    cmd = ('git', 'ls-files', '--', '*.py')
    filenames = subprocess.check_output(cmd).decode('UTF-8').splitlines()
    filenames.extend(args.extra)

    third_party = ','.join(sorted(third_party_imports(filenames)))

    for filename in ('.isort.cfg', 'setup.cfg', 'tox.ini'):
        if not os.path.exists(filename):
            continue

        with io.open(filename, encoding='UTF-8') as f:
            contents = f.read()

        if THIRD_PARTY_RE.search(contents):
            replacement = r'known_third_party\1=\2{}'.format(third_party)
            contents = THIRD_PARTY_RE.sub(replacement, contents)
            with io.open(filename, 'w', encoding='UTF-8') as f:
                f.write(contents)
            break
    else:
        print(
            'Could not find a `known_third_party` setting in any of '
            '.isort.cfg, setup.cfg, tox.ini.  '
            'Set up an initial config and run again!',
        )
        return 1


if __name__ == '__main__':
    exit(main())
