"""Alternative data features — insider deals, institutional flows, sentiment."""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from app.domain.market_data.models import InsiderDeal, InstitutionalFlow


def compute_alternative_features(
    insider_deals: list[InsiderDeal],
    flows: list[InstitutionalFlow],
    n_rows: int,
) -> pd.DataFrame:
    features = pd.DataFrame(index=range(n_rows))

    # Insider activity
    if insider_deals:
        total_buy_value = sum(d.value for d in insider_deals if "increase" in d.deal_type or "bulk" in d.deal_type)
        total_sell_value = sum(d.value for d in insider_deals if "decrease" in d.deal_type)
        features["insider_net_value"] = float(total_buy_value - total_sell_value)
        features["insider_deal_count"] = len(insider_deals)
        features["insider_buy_ratio"] = (
            float(total_buy_value) / float(total_buy_value + total_sell_value)
            if (total_buy_value + total_sell_value) > 0
            else 0.5
        )
    else:
        features["insider_net_value"] = 0.0
        features["insider_deal_count"] = 0
        features["insider_buy_ratio"] = 0.5

    # Institutional flows
    if flows:
        recent_flows = sorted(flows, key=lambda f: f.date, reverse=True)[:5]
        avg_fii_net = float(sum(f.fii_net for f in recent_flows) / len(recent_flows))
        avg_dii_net = float(sum(f.dii_net for f in recent_flows) / len(recent_flows))
        features["fii_net_5d_avg"] = avg_fii_net
        features["dii_net_5d_avg"] = avg_dii_net
        features["flow_regime"] = 1 if avg_fii_net > 0 and avg_dii_net > 0 else (-1 if avg_fii_net < 0 and avg_dii_net < 0 else 0)
    else:
        features["fii_net_5d_avg"] = 0.0
        features["dii_net_5d_avg"] = 0.0
        features["flow_regime"] = 0

    return features
