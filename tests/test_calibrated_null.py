"""research/calibrated_null.py: draws under a fair price centre on zero; a real edge sits in the far tail."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from calibrated_null import null_share  # noqa: E402


def test_fair_price_null_centres_on_zero_and_rejects_a_big_edge():
    n = 400
    cost = np.full(n, 0.8)                 # NO at 80c, fair when P(YES) = 0.2
    p_yes = np.full(n, 0.2)
    event = np.arange(n)
    x = null_share(cost, p_yes, event, observed=0.10, draws=2000)
    assert abs(x["null_mean"]) < 0.01
    assert x["share_ge"] < 0.01            # +10% a bet on 400 independent bets is far out
    # one event holding every bet: the null is all-or-nothing, so +10% is not rare at all
    y = null_share(cost, p_yes, np.zeros(n), observed=0.10, draws=2000)
    assert y["share_ge"] > 0.7
