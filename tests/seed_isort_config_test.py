import subprocess

import pytest

from seed_isort_config import main
from seed_isort_config import third_party_imports
from seed_isort_config import THIRD_PARTY_RE


def test_third_party_re():
    assert THIRD_PARTY_RE.search('[isort]\nknown_third_party=cfgv\n')
    assert THIRD_PARTY_RE.search('[isort]\nknown_third_party = cfgv\n')
    assert not THIRD_PARTY_RE.search('[isort]\nknown_stdlib = os\n')
    # make sure whitespace isn't greedily matched
    matched = THIRD_PARTY_RE.search('known_third_party=\n').group()
    assert matched == 'known_third_party='


def test_list_third_party_imports(tmpdir):
    with tmpdir.as_cwd():
        tmpdir.join('f.py').write('import cfgv\n')
        tmpdir.join('g.py').write('import os, pre_commit, f\n')
        tmpdir.join('h.py').write('from tokenize_rt import ESCAPED_NL\n')
        pkgdir = tmpdir.join('pkg').ensure_dir()
        pkgdir.join('__init__.py').ensure()
        pkgdir.join('i.py').write('x = 1\n')
        pkgdir.join('j.py').write('from .i import x\n')

        assert third_party_imports(()) == set()
        assert third_party_imports(('f.py',)) == {'cfgv'}
        assert third_party_imports(('f.py', 'g.py')) == {'pre_commit', 'cfgv'}
        assert third_party_imports(('h.py',)) == {'tokenize_rt'}
        assert third_party_imports(('pkg/i.py', 'pkg/j.py')) == set()


def _make_git():
    subprocess.check_call(('git', 'init', '.'))
    subprocess.check_call(('git', 'add', '.'))


def test_integration_isort_cfg(tmpdir):
    with tmpdir.as_cwd():
        tmpdir.join('.isort.cfg').write('[settings]\nknown_third_party=\n')
        tmpdir.join('f.py').write('import pre_commit\nimport cfgv\n')
        tmpdir.join('g.py').write('import f\nimport os\n')
        _make_git()

        assert not main(())

        expected = '[settings]\nknown_third_party=cfgv,pre_commit\n'
        assert tmpdir.join('.isort.cfg').read() == expected


@pytest.mark.parametrize('filename', ('setup.cfg', 'tox.ini'))
def test_integration_non_isort_cfg(filename, tmpdir):
    with tmpdir.as_cwd():
        tmpdir.join(filename).write('[isort]\nknown_third_party = cfgv\n')
        tmpdir.join('f.py').write('import pre_commit\nimport cfgv\n')
        _make_git()

        assert not main(())

        expected = '[isort]\nknown_third_party = cfgv,pre_commit\n'
        assert tmpdir.join(filename).read() == expected


def test_integration_multiple_config_files_exist(tmpdir):
    with tmpdir.as_cwd():
        tmpdir.join('setup.cfg').write('[bdist_wheel]\nuniversal = 1\n')
        tmpdir.join('tox.ini').write('[isort]\nknown_third_party=\n')
        tmpdir.join('f.py').write('import cfgv')
        _make_git()

        assert not main(())

        expected = '[isort]\nknown_third_party=cfgv\n'
        assert tmpdir.join('tox.ini').read() == expected


def test_integration_extra_file(tmpdir):
    with tmpdir.as_cwd():
        tmpdir.join('.isort.cfg').write('[settings]\nknown_third_party=\n')
        tmpdir.join('exe').write('import cfgv\n')
        tmpdir.join('f.py').write('import pre_commit\n')
        _make_git()

        assert not main(())

        expected = '[settings]\nknown_third_party=pre_commit\n'
        assert tmpdir.join('.isort.cfg').read() == expected

        assert not main(('--extra', 'exe'))

        expected = '[settings]\nknown_third_party=cfgv,pre_commit\n'
        assert tmpdir.join('.isort.cfg').read() == expected


def test_integration_no_config(tmpdir, capsys):
    with tmpdir.as_cwd():
        tmpdir.join('f.py').write('import cfgv')
        _make_git()

        assert main(())

        out, _ = capsys.readouterr()
        assert out.startswith('Could not find a `known_third_party` setting')
