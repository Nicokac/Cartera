import unittest


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    from tests import test_report_render_core, test_report_render_operations, test_report_render_ui

    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(test_report_render_core))
    suite.addTests(loader.loadTestsFromModule(test_report_render_operations))
    suite.addTests(loader.loadTestsFromModule(test_report_render_ui))
    return suite


if __name__ == "__main__":
    unittest.main()
