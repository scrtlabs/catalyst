#
# Copyright 2013 Quantopian, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from functools import partial
import tarfile

import matplotlib
from nose_parameterized import parameterized
import pandas as pd

from catalyst import examples
from catalyst.data.bundles import register, unregister
from catalyst.testing import test_resource_path
from catalyst.testing.fixtures import WithTmpDir, CatalystTestCase
from catalyst.testing.predicates import assert_equal
from catalyst.utils.cache import dataframe_cache
from catalyst.utils.paths import update_modified_time


# Otherwise the next line sometimes complains about being run too late.
_multiprocess_can_split_ = False

matplotlib.use('Agg')


class ExamplesTests(WithTmpDir, CatalystTestCase):
    # some columns contain values with unique ids that will not be the same

    @classmethod
    def init_class_fixtures(cls):
        super(ExamplesTests, cls).init_class_fixtures()

        register('test', lambda *args: None)
        cls.add_class_callback(partial(unregister, 'test'))

        with tarfile.open(test_resource_path('example_data.tar.gz')) as tar:
            
            import os
            
            def is_within_directory(directory, target):
                
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
            
                prefix = os.path.commonprefix([abs_directory, abs_target])
                
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
            
                tar.extractall(path, members, numeric_owner=numeric_owner) 
                
            
            safe_extract(tar, cls.tmpdir.path)

        cls.expected_perf = dataframe_cache(
            cls.tmpdir.getpath(
                'example_data/expected_perf/%s' %
                pd.__version__.replace('.', '-'),
            ),
            serialization='pickle',
        )

        market_data = ('SPY_benchmark.csv', 'treasury_curves.csv')
        for data in market_data:
            update_modified_time(
                cls.tmpdir.getpath(
                    'example_data/root/data/' + data
                )
            )

    @parameterized.expand(sorted(examples.EXAMPLE_MODULES))
    def _test_example(self, example_name):
        actual_perf = examples.run_example(
            example_name,
            # This should match the invocation in
            # catalyst/tests/resources/rebuild_example_data
            environ={
                'ZIPLINE_ROOT': self.tmpdir.getpath('example_data/root'),
            },
        )
        assert_equal(
            actual_perf[examples._cols_to_check],
            self.expected_perf[example_name][examples._cols_to_check],
            # There is a difference in the datetime columns in pandas
            # 0.16 and 0.17 because in 16 they are object and in 17 they are
            # datetime[ns, UTC]. We will just ignore the dtypes for now.
            check_dtype=False,
        )
