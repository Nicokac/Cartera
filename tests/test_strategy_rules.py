import unittest

try:
    from . import (
        strategy_rules_fundamentals,
        strategy_rules_market_regime,
        strategy_rules_narrative,
        strategy_rules_taxonomy,
        strategy_rules_technical_scoring,
    )
except ImportError:
    import strategy_rules_fundamentals
    import strategy_rules_market_regime
    import strategy_rules_narrative
    import strategy_rules_taxonomy
    import strategy_rules_technical_scoring


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str):
    suite = unittest.TestSuite()
    for module in (
        strategy_rules_fundamentals,
        strategy_rules_technical_scoring,
        strategy_rules_taxonomy,
        strategy_rules_narrative,
        strategy_rules_market_regime,
    ):
        suite.addTests(loader.loadTestsFromModule(module))
    return suite


if __name__ == "__main__":
    unittest.main()
