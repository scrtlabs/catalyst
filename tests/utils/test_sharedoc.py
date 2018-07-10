from catalyst.testing import CatalystTestCase
from catalyst.utils.sharedoc import copydoc


class TestSharedoc(CatalystTestCase):

    def test_copydoc(self):
        def original_docstring_function():
            """
            My docstring brings the boys to the yard.
            """
            pass

        @copydoc(original_docstring_function)
        def copied_docstring_function():
            pass

        self.assertEqual(
            original_docstring_function.__doc__,
            copied_docstring_function.__doc__
        )
