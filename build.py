import argparse
import distutils
from distutils.command.build_ext import build_ext, CompileError
from distutils.core import Distribution
from glob import glob
import os.path
import shutil
from importlib import import_module
import os
import sys


ext_dirs = ['parser', 'request', 'response', 'router', 'protocol']


def discover_extensions():
    extensions = []

    for directory in ext_dirs:
        def fix_path(path):
            return os.path.abspath(os.path.join(directory, path))

        ext_files = glob(os.path.join(directory, '*_ext.py'))
        for f in ext_files:
            print('Collected: ', f)
        ext_modules = [os.path.splitext(f)[0].replace('/', '.') for f in ext_files]
        dir_extensions = [import_module(m).get_extension(fix_path) for m in ext_modules]
        extensions.extend(dir_extensions)

    return extensions


def dest_folder(mod_name):
    return '/'.join(mod_name.split('.')[:-1])


def prune():
    paths = glob('build/**/*.o', recursive=True)
    paths.extend(glob('build/**/*.so', recursive=True))
    for path in paths:
        os.remove(path)


def main():
    argparser = argparse.ArgumentParser('build')
    argparser.add_argument(
        '-d', dest='debug', const=True, action='store_const', default=False)
    argparser.add_argument(
        '--profile-generate', dest='profile_generate', const=True,
        action='store_const', default=False)
    argparser.add_argument(
        '--profile-use', dest='profile_use', const=True,
        action='store_const', default=False)
    args = argparser.parse_args(sys.argv[1:])

    distutils.log.set_verbosity(1)

    ext_modules = discover_extensions()
    dist = Distribution(dict(ext_modules=ext_modules))

    if args.debug:
        for ext_module in ext_modules:
            ext_module.extra_compile_args.extend(['-g', '-O0'])
    if args.profile_generate:
        for ext_module in ext_modules:
            ext_module.extra_compile_args.append('--profile-generate')
            ext_module.extra_link_args.append('-lgcov')
    if args.profile_use:
        for ext_module in ext_modules:
            if ext_module.name == 'parser.cparser':
                continue
            ext_module.extra_compile_args.append('--profile-use')

    if not args.debug:
        for ext_module in ext_modules:
            ext_module.extra_compile_args.append('-flto')
            ext_module.extra_link_args.append('-flto')

    prune()

    cmd = build_ext(dist)
    cmd.finalize_options()

    try:
        cmd.run()
    except CompileError:
        sys.exit(1)

    for ext_module in ext_modules:
        shutil.copy(
            cmd.get_ext_fullpath(ext_module.name),
            dest_folder(ext_module.name))


if __name__ == '__main__':
    main()