# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

# Enable `python -m pants ...` style execution ala `json.tool` or `venv`.
python_library(
  name='entry_point',
  sources=['__main__.py'],
  dependencies=[
    'src/python/pants/bin',
  ],
  tags = {'partially_type_checked'},
)

python_library(
  name='pants-packaged',
  # NB: we must include at least one file in `sources` to avoid clang/gcc complaining
  # `error: no input files`. We don't actually need to put any meaningful files here,
  # though, because we use `with_binaries()` to link to the actual native code,
  # so clang/gcc do not need to build any native code. Instead, we pass a dummy file.
  sources=['dummy.c'],
  dependencies=[
    ':entry_point',
    ':version',
  ],
  tags = {'partially_type_checked'},
  provides=pants_setup_py(
    name='pantsbuild.pants',
    description='A scalable build tool for large, complex, heterogeneous repos.',
    namespace_packages=['pants', 'pants.backend'],
    # NB: by setting `ext_modules`, we signal to setup_py and bdist_wheel that this library
    # has native code. As a consquence, bdist_wheel pins the ABI (application binary interface)
    # used when creating the wheel, which is a good thing. We should be setting this ABI to ensure
    # consumers of pantsbuild.pants are using a compatible interpreter.
    # TODO(7344): the tuple syntax for ext_modules is deprecated. Use Extension once we support it.
    ext_modules=[('native_engine', {'sources': ['src/pants/dummy.c']})],
  ).with_binaries(
    pants='src/python/pants/bin:pants',
  )
)

page(
  name='readme',
  source='README.md',
)

python_library(
  name='version',
  sources=['version.py'],
  dependencies = [
    '3rdparty/python:packaging',
    ':version-resource',
  ],
  tags = {"type_checked"},
)

resources(
  name='version-resource',
  sources=['VERSION'],
)

page(
  name='changelog',
  source='CHANGELOG.md',
  links=[
    'src/python/pants/notes:notes-1.0.x',
    'src/python/pants/notes:notes-master',
  ],
  description='''
This file is no longer a changelog, but remains in this location in order to avoid breaking
older changelog links unnecessarily. Could consider removing it by 2.0.x, perhaps.
''',
)

# NB: This is used for the integration test `test_reversion.py`. It includes all transitive
# dependencies to ensure that the chroot can run `src/python/pants/releases:reversion` properly.
files(
  name='reversion_file_with_dependencies',
  sources=[
    'releases/BUILD',
    'releases/reversion.py',
    'util/BUILD',
    'util/contextutil.py',
    'util/dirutil.py',
    'util/strutil.py',
    'util/tarutil.py',
  ],
)
