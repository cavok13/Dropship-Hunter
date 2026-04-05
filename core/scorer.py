"""
Dropship Winner Scoring Algorithm
──────────────────────────────────
Winner Score = (Demand Score × w_d) + (Opportunity Score × w_o)

Demand Score  → how much people want this product
Opportunity   → how much room there is to win (low BSR rank = hard,
                high orders but few reviews = opportunity, etc.)
"""
import math


class ProductScorer:
    def __init__(self, cfg: dict):
        self.w_d = cfg["scoring"].get("demand_weight", 0.60)
        self.w_o = cfg["scoring"].get("competition_weight", 0.40)
        self.min_rating = cfg["scoring"].get("min_rating", 4.0)
        self.min_reviews = cfg["scoring"].get("min_reviews", 30)
        self.min_orders = cfg["scoring"].get("min_orders", 100)
        price_range = cfg["scoring"].get("price_range", {})
        self.price_min = price_range.get("min", 5)
        self.price_max = price_range.get("max", 150)

    # ── Public API ────────────────────────────────────────────────────────────

    def score_and_filter(self, products: list[dict]) -> list[dict]:
        """Score all products, filter obvious duds, return sorted top-N."""
        scored = []
        for p in products:
            if not self._passes_filters(p):
                continue
            p = self._compute_scores(p)
            scored.append(p)

        # De-duplicate by title similarity
        scored = self._deduplicate(scored)

        # Sort by winner_score descending
        scored.sort(key=lambda x: x["winner_score"], reverse=True)
        return scored

    # ── Filtering ─────────────────────────────────────────────────────────────

    def _passes_filters(self, p: dict) -> bool:
        if p.get("rating", 0) > 0 and p["rating"] < self.min_rating:
            return False
        price = p.get("price", 0)
        if price and not (self.price_min <= price <= self.price_max):
            return False
        if not p.get("title"):
            return False
        return True

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _compute_scores(self, p: dict) -> dict:
        demand = self._demand_score(p)
        opportunity = self._opportunity_score(p)
        winner = round(demand * self.w_d + opportunity * self.w_o, 1)

        p["demand_score"] = round(demand, 1)
        p["opportunity_score"] = round(opportunity, 1)
        p["winner_score"] = winner
        p["score_breakdown"] = self._score_breakdown(p)
        return p

    def _demand_score(self, p: dict) -> float:
        """
        Demand signals (0-100):
        - Review count       (log scale, max at 5000+)
        - Rating quality     (4.0–5.0 range mapped to 0–100)
        - Order count        (AliExpress, log scale)
        - BSR rank           (Amazon, inverted – lower rank = higher demand)
        - Price sweet spot   ($15-$60 is ideal for dropshipping margins)
        """
        score = 0.0

        # Reviews (weight 30)
        reviews = p.get("reviews", 0)
        if reviews > 0:
            score += min(30, 30 * math.log10(reviews + 1) / math.log10(5001))

        # Rating (weight 25)
        rating = p.get("rating", 0)
        if rating >= 4.0:
            score += ((rating - 4.0) / 1.0) * 25

        # Orders / AliExpress (weight 25)
        orders = p.get("orders", 0)
        if orders > 0:
            score += min(25, 25 * math.log10(orders + 1) / math.log10(100_001))

        # BSR rank / Amazon (weight 20) – lower rank = more demand
        bsr = p.get("bsr_rank", 999)
        if bsr < 999:
            score += max(0, 20 * (1 - (min(bsr, 100) / 100)))

        # Price sweet-spot bonus (weight 5)
        price = p.get("price", 0)
        if 15 <= price <= 60:
            score += 5
        elif 10 <= price <= 80:
            score += 2

        return min(score, 100)

    def _opportunity_score(self, p: dict) -> float:
        """
        Opportunity (0-100): Higher = better chance for a new dropshipper.
        Factors: review-to-orders gap, price margin, niche depth.
        """
        score = 50.0  # Base neutral

        # Low review count vs high orders → unreviewed goldmine
        reviews = p.get("reviews", 0)
        orders = p.get("orders", 0)
        if orders > 500 and reviews < 200:
            score += 20  # Lots of buyers, few leave reviews → SEO gap
        elif reviews > 10_000:
            score -= 15  # Very established, hard to compete

        # BSR rank – not in top 10 = still room to grow
        bsr = p.get("bsr_rank", 999)
        if 10 < bsr < 50:
            score += 10
        elif bsr <= 10:
            score -= 20  # Already dominated

        # Price margin potential
        price = p.get("price", 0)
        if 15 <= price <= 60:
            score += 15   # Good margin room
        elif price > 100:
            score -= 10   # High price = hard for new sellers
        elif price < 8:
            score -= 10   # Thin margins

        return min(max(score, 0), 100)

    def _score_breakdown(self, p: dict) -> str:
        parts = []
        if p.get("orders", 0) > 1000:
            parts.append(f"{p['orders']:,} orders")
        if p.get("reviews", 0) > 0:
            parts.append(f"{p['reviews']:,} reviews")
        if p.get("rating", 0) > 0:
            parts.append(f"★ {p['rating']}")
        if p.get("price", 0) > 0:
            parts.append(f"${p['price']:.2f}")
        return " · ".join(parts)

    # ── De-duplication ────────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(products: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for p in products:
            key = p["title"][:40].lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique
