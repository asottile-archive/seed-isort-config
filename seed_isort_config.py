import argparse
import ast
import os.path
import re
import subprocess
from typing import Optional
from typing import Sequence
from typing import Set

from aspy.refactor_imports.classify import classify_import
from aspy.refactor_imports.classify import ImportType


ENV_BLACKLIST = frozenset((
    'GIT_LITERAL_PATHSPECS', 'GIT_GLOB_PATHSPECS', 'GIT_NOGLOB_PATHSPECS',
))
SUPPORTED_CONF_FILES = (
    '.editorconfig', '.isort.cfg', 'setup.cfg', 'tox.ini', 'pyproject.toml',
)
THIRD_PARTY_RE = re.compile(
    r'^([ \t]*)known_third_party([ \t]*)=([ \t]*)(?:.*?)?(\r?)$', re.M,
)
KNOWN_OTHER_RE = re.compile(
    r'^[ \t]*known_((?!third_party)\w+)[ \t]*=[ \t]*(.*)$', re.M,
)


class Visitor(ast.NodeVisitor):
    def __init__(self, appdirs: Sequence[str] = ('.',)) -> None:
        self.appdirs = appdirs
        self.third_party: Set[str] = set()

    def _maybe_append_name(self, name: str) -> None:
        name, _, _ = name.partition('.')
        imp_type = classify_import(name, self.appdirs)
        if imp_type == ImportType.THIRD_PARTY:
            self.third_party.add(name)

    def visit_Import(self, node: ast.Import) -> None:
        if node.col_offset == 0:
            for name in node.names:
                self._maybe_append_name(name.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.col_offset == 0:
            if not node.level:
                assert node.module is not None  # true for node.level == 0
                self._maybe_append_name(node.module)


def third_party_imports(
        filenames: Sequence[str],
        appdirs: Sequence[str] = ('.',),
) -> Set[str]:
    visitor = Visitor(appdirs)
    for filename in filenames:
        if not os.path.exists(filename):
            continue
        with open(filename, 'rb') as f:
            visitor.visit(ast.parse(f.read(), filename=filename))
    return visitor.third_party


def ini_load(imports: str) -> Sequence[str]:
    return imports.strip().split(',')


def ini_dump(imports: Sequence[str]) -> str:
    return ','.join(imports)


def toml_load(imports: str) -> Sequence[str]:
    return ast.literal_eval(imports)


def toml_dump(imports: Sequence[str]) -> str:
    return '[{}]'.format(', '.join(f'"{i}"' for i in imports))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--extra', action='append', default=[])
    parser.add_argument('--exclude', default='^$')
    parser.add_argument(
        '--application-directories', default='.',
        help=(
            'Colon separated directories that are considered top-level '
            'application directories.  Defaults to `%(default)s`'
        ),
    )
    parser.add_argument(
        '--settings-path', default='.',
        help=(
            'Directory containing isort config file. '
            'Defaults to `%(default)s`'
        ),
    )
    args = parser.parse_args(argv)

    cmd = ('git', 'ls-files', '--', '*.py')
    env = {k: v for k, v in os.environ.items() if k not in ENV_BLACKLIST}
    try:
        out = subprocess.check_output(cmd, env=env).decode('UTF-8')
    except OSError:
        raise OSError('Cannot find git. Make sure it is in your PATH')
    filenames = out.splitlines() + args.extra

    exclude = re.compile(args.exclude)
    filenames = [f for f in filenames if not exclude.search(f)]

    appdirs = args.application_directories.split(':')
    third_party = third_party_imports(filenames, appdirs)

    for filename in SUPPORTED_CONF_FILES:
        filename = os.path.join(args.settings_path, filename)
        if not os.path.exists(filename):
            continue

        if filename.endswith('.toml'):
            load = toml_load
            dump = toml_dump
        else:
            load = ini_load
            dump = ini_dump

        with open(filename, encoding='UTF-8', newline='') as f:
            contents = f.read()

        for match in KNOWN_OTHER_RE.finditer(contents):
            third_party -= set(load(match.group(2)))

        if THIRD_PARTY_RE.search(contents):
            third_party_s = dump(sorted(third_party))
            replacement = fr'\1known_third_party\2=\3{third_party_s}\4'
            new_contents = THIRD_PARTY_RE.sub(replacement, contents)
            if new_contents == contents:
                return 0
            else:
                with open(filename, 'w', encoding='UTF-8', newline='') as f:
                    f.write(new_contents)
                print(f'{filename} updated.')
                return 1
    else:
        filename = os.path.join(args.settings_path, '.isort.cfg')
        third_party_s = ','.join(sorted(third_party))
        if os.path.exists(filename):
            prefix = 'Updating'
            mode = 'a'
            contents = f'known_third_party = {third_party_s}\n'
        else:
            prefix = 'Creating'
            mode = 'w'
            contents = f'[settings]\nknown_third_party = {third_party_s}\n'

        print(
            f'{prefix} an .isort.cfg with a known_third_party setting. '
            f'Feel free to move the setting to a different config file in '
            f'one of {", ".join(SUPPORTED_CONF_FILES)}.\n\n'
            f'This setting should be committed.',
        )

        try:
            os.makedirs(args.settings_path)
        except OSError:
            if not os.path.isdir(args.settings_path):
                raise

        with open(filename, mode, encoding='UTF-8') as isort_cfg:
            isort_cfg.write(contents)
        return 1


if __name__ == '__main__':
    exit(main())
