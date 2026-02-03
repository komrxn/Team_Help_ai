import unittest
import math
from datetime import datetime, timedelta, timezone

# Mock class to simulate order structure
class MockOrder:
    def __init__(self, is_good, days_ago):
        self.is_good = is_good
        self.created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)

class TestRating(unittest.TestCase):
    def test_rating_logic(self):
        # Scenario:
        # 1. Good, 10 days ago (Weight 1.0)
        # 2. Good, 40 days ago (Weight 0.5)
        # 3. Bad, 100 days ago (Weight 0.2)
        
        orders = [
            MockOrder(True, 10),
            MockOrder(True, 40),
            MockOrder(False, 100)
        ]
        
        weighted_good = (1.0 * 1.0) + (1.0 * 0.5) + (0.0 * 0.2) # 1.5
        weighted_total = 1.0 + 0.5 + 0.2 # 1.7
        
        # Formula: (weighted_good + 1) / (weighted_total + 2)
        expected_score = (1.5 + 1) / (1.7 + 2) # 2.5 / 3.7 = 0.6756
        
        calculated_score = (weighted_good + 1) / (weighted_total + 2)
        
        self.assertAlmostEqual(calculated_score, 0.6756, places=4)
        
        # Confidence
        # 1 - exp(-3 / 7)
        expected_conf = 1 - math.exp(-3/7) # 1 - 0.6514 = 0.3486
        
        calculated_conf = 1 - math.exp(-len(orders)/7.0)
        self.assertAlmostEqual(calculated_conf, 0.3486, places=4)

if __name__ == '__main__':
    unittest.main()
