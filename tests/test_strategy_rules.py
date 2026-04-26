import unittest

try:
    from .strategy_rules_fundamentals import StrategyRulesFundamentalsTests
    from .strategy_rules_market_regime import StrategyRulesMarketRegimeTests
    from .strategy_rules_narrative import StrategyRulesNarrativeTests
    from .strategy_rules_taxonomy import StrategyRulesTaxonomyTests
    from .strategy_rules_technical_scoring import StrategyRulesTechnicalScoringTests
except ImportError:
    from strategy_rules_fundamentals import StrategyRulesFundamentalsTests
    from strategy_rules_market_regime import StrategyRulesMarketRegimeTests
    from strategy_rules_narrative import StrategyRulesNarrativeTests
    from strategy_rules_taxonomy import StrategyRulesTaxonomyTests
    from strategy_rules_technical_scoring import StrategyRulesTechnicalScoringTests


if __name__ == "__main__":
    unittest.main()
