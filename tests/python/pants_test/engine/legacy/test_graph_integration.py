# Copyright 2018 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent
from typing import Iterator

from pants.option.scope import GLOBAL_SCOPE_CONFIG_SECTION
from pants.testutil.pants_run_integration_test import PantsRunIntegrationTest


class GraphIntegrationTest(PantsRunIntegrationTest):

  @classmethod
  def use_pantsd_env_var(cls):
    """
    Some of the tests here expect to read the standard error after an intentional failure.
    However, when pantsd is enabled, these errors are logged to logs/exceptions.<pid>.log
    So stderr appears empty. (see #7320)
    """
    return False

  _WARN_FMT = """[WARN] Globs did not match. Excludes were: {excludes}. Unmatched globs were: {unmatched}."""

  _NO_BUILD_FILE_TARGET_BASE = 'testprojects/src/python/no_build_file'

  _SOURCES_TARGET_BASE = 'testprojects/src/python/sources'

  _SOURCES_ERR_MSGS = {
    'missing-globs': ("globs('*.a')", ['*.a']),
    'missing-rglobs': ("rglobs('*.a')", ['**/*.a']),
    'missing-zglobs': ("zglobs('**/*.a')", ['**/*.a']),
    'missing-literal-files': (
      "['another_nonexistent_file.txt', 'nonexistent_test_file.txt']", [
      'another_nonexistent_file.txt',
      'nonexistent_test_file.txt',
    ]),
  }

  _BUNDLE_TARGET_BASE = 'testprojects/src/java/org/pantsbuild/testproject/bundle'
  _BUNDLE_ERR_MSGS = [
    ['*.aaaa'],
    ['**/*.aaaa', '**/*.bbbb'],
    ['**/*.abab'],
    ['file1.aaaa', 'file2.aaaa'],
  ]

  _ERR_TARGETS = {
    'testprojects/src/python/sources:some-missing-some-not': [
      "globs('*.txt', '*.rs')",
      "Snapshot(PathGlobs(include=(\'testprojects/src/python/sources/*.txt\', \'testprojects/src/python/sources/*.rs\'), exclude=(), glob_match_error_behavior<Exactly(GlobMatchErrorBehavior)>=GlobMatchErrorBehavior(value=error), conjunction<Exactly(GlobExpansionConjunction)>=GlobExpansionConjunction(value=all_match)))",
      "Globs did not match. Excludes were: []. Unmatched globs were: [\"testprojects/src/python/sources/*.rs\"].",
    ],
    'testprojects/src/python/sources:missing-sources': [
      "*.scala",
      "Snapshot(PathGlobs(include=(\'testprojects/src/python/sources/*.scala\',), exclude=(\'testprojects/src/python/sources/*Test.scala\', \'testprojects/src/python/sources/*Spec.scala\'), glob_match_error_behavior<Exactly(GlobMatchErrorBehavior)>=GlobMatchErrorBehavior(value=error), conjunction<Exactly(GlobExpansionConjunction)>=GlobExpansionConjunction(value=any_match)))",
      "Globs did not match. Excludes were: [\"testprojects/src/python/sources/*Test.scala\", \"testprojects/src/python/sources/*Spec.scala\"]. Unmatched globs were: [\"testprojects/src/python/sources/*.scala\"].",
    ],
    'testprojects/src/java/org/pantsbuild/testproject/bundle:missing-bundle-fileset': [
      "['a/b/file1.txt']",
      "RGlobs('*.aaaa', '*.bbbb')",
      "Globs('*.aaaa')",
      "ZGlobs('**/*.abab')",
      "['file1.aaaa', 'file2.aaaa']",
      "Snapshot(PathGlobs(include=(\'testprojects/src/java/org/pantsbuild/testproject/bundle/*.aaaa\',), exclude=(), glob_match_error_behavior<Exactly(GlobMatchErrorBehavior)>=GlobMatchErrorBehavior(value=error), conjunction<Exactly(GlobExpansionConjunction)>=GlobExpansionConjunction(value=all_match)))",
      "Globs did not match. Excludes were: []. Unmatched globs were: [\"testprojects/src/java/org/pantsbuild/testproject/bundle/*.aaaa\"].",
    ]
  }

  @contextmanager
  def setup_sources_targets(self) -> Iterator[None]:
    build_path = Path(self._SOURCES_TARGET_BASE, "BUILD")
    original_content = build_path.read_text()
    new_content = dedent("""\
      scala_library(
        name='missing-sources',
      )

      resources(
        name='missing-globs',
        sources=globs('*.a'),
      )

      resources(
        name='missing-rglobs',
        sources=rglobs('*.a'),
      )
  
      resources(
        name='missing-zglobs',
        sources=zglobs('**/*.a'),
      )
      
      resources(
        name='missing-literal-files',
        sources=[
          'nonexistent_test_file.txt',
          'another_nonexistent_file.txt',
        ],
      )
      
      resources(
        name='some-missing-some-not',
        sources=globs('*.txt', '*.rs'),
      )

      resources(
        name='overlapping-globs',
        sources=globs('sources.txt', '*.txt'),
      )
      """)
    with self.with_overwritten_file_content(build_path,  f"{original_content}\n{new_content}"):
      yield

  @contextmanager
  def setup_bundle_target(self) -> Iterator[None]:
    build_path = Path(self._BUNDLE_TARGET_BASE, "BUILD")
    original_content = build_path.read_text()
    new_content = dedent("""\
      jvm_app(
        name='missing-bundle-fileset',
        binary=':bundle-bin',
        bundles=[
          bundle(fileset=['a/b/file1.txt']),
          bundle(fileset=rglobs('*.aaaa', '*.bbbb')),
          bundle(fileset=globs('*.aaaa')),
          bundle(fileset=zglobs('**/*.abab')),
          bundle(fileset=['file1.aaaa', 'file2.aaaa']),
        ],
      )
      """)
    with self.with_overwritten_file_content(build_path,  f"{original_content}\n{new_content}"):
      yield

  def test_missing_sources_warnings(self):
    with self.setup_sources_targets():
      for target_name in self._SOURCES_ERR_MSGS.keys():
        target_full = f'{self._SOURCES_TARGET_BASE}:{target_name}'
        glob_str, expected_globs = self._SOURCES_ERR_MSGS[target_name]
        pants_run = self.run_pants(['filedeps', target_full], config={
          GLOBAL_SCOPE_CONFIG_SECTION: {
            'glob_expansion_failure': 'warn',
          },
        })
        self.assert_success(pants_run)
        warning_msg = (
          self._WARN_FMT.format(
            excludes="[]",
            unmatched="[{}]".format(', '.join(
              f'"{os.path.join(self._SOURCES_TARGET_BASE, g)}"' for g in expected_globs)
            )
          )
        )
        self.assertIn(warning_msg, pants_run.stderr_data)

  def test_existing_sources(self):
    target_full = f'{self._SOURCES_TARGET_BASE}:text'
    pants_run = self.run_pants(['filedeps', target_full], config={
      GLOBAL_SCOPE_CONFIG_SECTION: {
        'glob_expansion_failure': 'warn',
      },
    })
    self.assert_success(pants_run)
    self.assertNotIn("Globs", pants_run.stderr_data)

  def test_missing_bundles_warnings(self):
    target_full = f'{self._BUNDLE_TARGET_BASE}:missing-bundle-fileset'
    with self.setup_bundle_target():
      pants_run = self.run_pants(['filedeps', target_full], config={
        GLOBAL_SCOPE_CONFIG_SECTION: {
          'glob_expansion_failure': 'warn',
        },
      })
    self.assert_success(pants_run)
    for msgs in self._BUNDLE_ERR_MSGS:
      warning_msg = (
        "WARN] Globs did not match. Excludes were: " +
        "[]" +
        ". Unmatched globs were: " +
        "[{}]".format(', '.join(('"' + os.path.join(self._BUNDLE_TARGET_BASE, m) + '"') for m in msgs)) +
        ".")
      self.assertIn(warning_msg, pants_run.stderr_data)

  def test_existing_bundles(self):
    target_full = f'{self._BUNDLE_TARGET_BASE}:mapper'
    pants_run = self.run_pants(['filedeps', target_full], config={
      GLOBAL_SCOPE_CONFIG_SECTION: {
        'glob_expansion_failure': 'warn',
      },
    })
    self.assert_success(pants_run)
    self.assertNotIn("Globs", pants_run.stderr_data)

  def test_existing_directory_with_no_build_files_fails(self):
    pants_run = self.run_pants(['list', f"{self._NO_BUILD_FILE_TARGET_BASE}::"])
    self.assert_failure(pants_run)
    self.assertIn("does not match any targets.", pants_run.stderr_data)

  @unittest.skip('Flaky: https://github.com/pantsbuild/pants/issues/6787')
  def test_error_message(self):
    with self.setup_bundle_target(), self.setup_sources_targets():
      for target in self._ERR_TARGETS:
        expected_excerpts = self._ERR_TARGETS[target]
        pants_run = self.run_pants(['filedeps', target], config={
          GLOBAL_SCOPE_CONFIG_SECTION: {
            'glob_expansion_failure': 'error',
          },
        })
        self.assert_failure(pants_run)
        for excerpt in expected_excerpts:
          self.assertIn(excerpt, pants_run.stderr_data)
