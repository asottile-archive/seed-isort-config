import os
import subprocess

import mock
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
        assert third_party_imports(()) == set()
        assert third_party_imports(('f.py',)) == {'cfgv'}
        assert third_party_imports(('f.py', 'g.py')) == {'pre_commit', 'cfgv'}
        assert third_party_imports(('h.py',)) == {'tokenize_rt'}


def test_third_party_imports_pkg(tmpdir):
    with tmpdir.as_cwd():
        pkgdir = tmpdir.join('pkg').ensure_dir()
        pkgdir.join('__init__.py').ensure()
        pkgdir.join('i.py').write('x = 1\n')
        pkgdir.join('j.py').write('from .i import x\n')
        assert third_party_imports(('pkg/i.py', 'pkg/j.py')) == set()


def test_third_party_imports_not_top_level(tmpdir):
    with tmpdir.as_cwd():
        tmpdir.join('f.py').write(
            'import cfgv\n'
            'try:\n'
            '    from x import y\n'
            'except ImportError:\n'
            '    from z import y\n'
            'try:\n'
            '    import x\n'
            'except ImportError:\n'
            '    import y\n',
        )
        assert third_party_imports(('f.py',)) == {'cfgv'}


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


def test_integration_known_packages(tmpdir):
    with tmpdir.as_cwd():
        cfg = tmpdir.join('.isort.cfg')
        cfg.write('[settings]\nknown_django=django\nknown_third_party=\n')
        tmpdir.join('f.py').write('import pre_commit\nimport cfgv\n')
        tmpdir.join('g.py').write('import f\nimport os\nimport django\n')
        _make_git()

        assert not main(())

        expected = (
            '[settings]\n'
            'known_django=django\n'
            'known_third_party=cfgv,pre_commit\n'
        )
        assert cfg.read() == expected


def test_integration_editorconfig(tmpdir):
    with tmpdir.as_cwd():
        tmpdir.join('.editorconfig').write('[*.py]\nknown_third_party=cfgv\n')
        tmpdir.join('f.py').write('import pre_commit\nimport cfgv\n')
        _make_git()

        assert not main(())

        expected = '[*.py]\nknown_third_party=cfgv,pre_commit\n'
        assert tmpdir.join('.editorconfig').read() == expected


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


@pytest.mark.parametrize(
    ('initial_filesystem', 'expected_filesystem'),
    (
        (
            (),
            (('.isort.cfg', '[settings]\nknown_third_party = cfgv\n'),),
        ),
        (
            (('.isort.cfg', '[settings]\ncombine_as_imports = true\n'),),
            (
                (
                    '.isort.cfg',
                    '[settings]\n'
                    'combine_as_imports = true\n'
                    'known_third_party = cfgv\n',
                ),
            ),
        ),
        (
            (('setup.cfg', '[bdist_wheel]\nuniversal = True\n'),),
            (('.isort.cfg', '[settings]\nknown_third_party = cfgv\n'),),
        ),
    ),
)
def test_integration_no_section(
        tmpdir,
        initial_filesystem,
        expected_filesystem,
):
    with tmpdir.as_cwd():
        tmpdir.join('f.py').write('import cfgv')
        for filename, initial in initial_filesystem:
            tmpdir.join(filename).write(initial)
        _make_git()

        assert not main(())

        for filename, expected in expected_filesystem:
            assert tmpdir.join(filename).read() == expected


def test_integration_src_layout(tmpdir):
    with tmpdir.as_cwd():
        src = tmpdir.join('src').ensure_dir()
        src.join('f.py').write('import cfgv')
        src.join('g.py').write('import f')
        _make_git()

        assert not main(('--application-directories', 'src'))

        expected = '[settings]\nknown_third_party = cfgv\n'
        assert tmpdir.join('.isort.cfg').read() == expected


def test_integration_settings_path(tmpdir):
    with tmpdir.as_cwd():
        src = tmpdir.join('src').ensure_dir()
        src.join('f.py').write('import cfgv')
        _make_git()

        assert not main(('--settings-path', 'cfg'))

        expected = '[settings]\nknown_third_party = cfgv\n'
        assert tmpdir.join('cfg/.isort.cfg').read() == expected
        assert not tmpdir.join('.isort.cfg').exists()


def test_integration_git_literal_pathspecs_1(tmpdir):
    """an emacs plugin, magit calls pre-commit in this way, see #5"""
    with mock.patch.dict(os.environ, {'GIT_LITERAL_PATHSPECS': '1'}):
        test_integration_isort_cfg(tmpdir)


def test_exclude(tmpdir):
    with tmpdir.as_cwd():
        tmpdir.join('f.py').write('import cfgv\n')
        tmpdir.join('g.py').write('syntax error')
        _make_git()

        assert not main(('--exclude', '^g.py$'))

        expected = '[settings]\nknown_third_party = cfgv\n'
        assert tmpdir.join('.isort.cfg').read() == expected
