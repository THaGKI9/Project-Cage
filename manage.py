#!/usr/bin/env python3
from flask_script import Manager, prompt_bool
from coverage import Coverage

cov = Coverage(include=['./core/*'], branch=True)
cov.start()


def load_app(config_name='dev'):
    import config
    from core import create_app
    configuration = {
        'dev': config.DevelopmentConfig,
        'test': config.TestingConfig
    }
    app = create_app(configuration.get(config_name, config.DevelopmentConfig))
    return app


def _make_context():
    global manager
    app = manager()
    from core import db, models
    from core.models import tables

    models_dict = {t.__name__: t for t in tables}
    context = dict(app=app, db=db, models=models)
    context.update(models_dict)
    return context


manager = Manager(load_app)
manager.add_option('-c', '--config', dest='config_name')
manager.shell(_make_context)

setup_manager = Manager(usage='Application setup utilities')
build_manager = Manager(usage='Application development utilities.')

manager.add_command('setup', setup_manager)
manager.add_command('build', build_manager)


@setup_manager.command
def reset_database():
    from core import db
    from core.models import tables
    app = manager()  # noqa

    if prompt_bool('Your database will be reseted, are you sure?'):
        print('Reseting databases...')
        db.database.drop_tables(tables, True)
        db.database.create_tables(tables)


@build_manager.command
def clean():
    from os import walk
    from shutil import rmtree
    from os.path import split, normpath, exists

    pyc_folders = [normpath(root) for root, dirs, files in walk('./core')
                   if split(root)[-1] == '__pycache__']
    pyc_folders += [normpath(root) for root, dirs, files in walk('./test')
                    if split(root)[-1] == '__pycache__']
    pyc_folders.append(normpath('./__pycache__'))
    pyc_folders.append(normpath('./doc/build'))
    pyc_folders.append(normpath('./cov_report'))

    def on_rmtree_error(func, path, exc_info):
        print('Delete %s failed: %s' % (path, exc_info[1].message))

    for f in sorted(tuple(pyc_folders)):
        if not exists(f):
            continue
        rmtree(f, on_rmtree_error)
        if not exists(f):
            print('Deleted: %s' % f)


@build_manager.command
def doc():
    from shutil import rmtree
    from sys import stderr, stdout
    from os.path import abspath, join
    from subprocess import run as run_process

    print('Building document...')
    source_dir = './doc'
    output_dir = './doc/build/html'

    rmtree(output_dir, True)
    status = run_process(
        ['sphinx-build', '-bhtml', '-E', '-j2', '-q', source_dir, output_dir],
        stderr=stderr, stdout=stdout)

    if status.returncode != 0:
        print('Building document failed.')
    else:
        target_file = abspath(join(output_dir, 'index.html'))
        print('The document has been written to: ' + target_file)


@manager.option('-m', '--module')
@manager.option('-f', '--func')
@manager.option('-c', '--coverage', action='store_true')
@manager.option('-v', '--verbosity', action='store_true')
@manager.option('-e', '--failfast', action='store_true')
def test(module, func, coverage, verbosity, failfast):
    from unittest import TestLoader, TextTestRunner
    from os.path import abspath, normpath, dirname, join
    from sys import path

    if coverage:
        print('Run unittest with coverage monitor.')
    else:
        cov.stop()

    runner = TextTestRunner(verbosity=2 if verbosity else 1, failfast=failfast)
    loader = TestLoader()
    tests = None

    if module is None:
        tests = loader.discover('test')
    elif func is None:
        tests = loader.loadTestsFromName('test.test_' + module)
    else:
        path.append('test')
        module = __import__('test_' + module)

        loader = TestLoader()
        runner = TextTestRunner(verbosity=2)

        test_class = None
        for k, v in module.__dict__.items():
            if k.endswith('TestCase') and k != 'BaseTestCase':
                test_class = v
                break

        test_func_name = 'test_' + func
        tests = loader.loadTestsFromName(test_func_name, test_class)

    runner.run(tests)

    if coverage:
        cov.stop()
        cov.save()
        print('Coverage Summary:')
        cov.report()
        base_dir = abspath(dirname(__file__))
        cov_dir = normpath(join(base_dir, 'cov_report'))
        cov.html_report(directory=cov_dir)
        cov.erase()


if __name__ == '__main__':
    manager.run()
