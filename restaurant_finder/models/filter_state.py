"""Filter state model for tracking accumulated filters across conversation turns."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class FilterState(BaseModel):
    """Tracks accumulated filters across a conversation session.

    This model maintains all filter criteria that have been applied through
    the conversation, allowing follow-up queries to refine or expand results.
    """

    # Base search criteria
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None  # "San Jose", "Downtown", etc.

    # Filter criteria
    cuisine: Optional[str] = None  # "Italian", "Thai", etc.
    min_rating: Optional[float] = None  # 1.0-5.0
    max_price_level: Optional[int] = None  # 1=$ 2=$$ 3=$$$ 4=$$$$
    radius_miles: float = Field(default=5.0, ge=1.0, le=25.0)
    dietary_restrictions: List[str] = Field(default_factory=list)  # ["Vegetarian", "Vegan"]
    keywords: Optional[str] = None  # "sushi", "burger", "outdoor seating"

    # Sort/ranking criteria
    sort_by: Optional[Literal["distance", "rating", "price_low", "price_high"]] = None

    # Meta
    limit: int = Field(default=10, ge=1, le=50)

    def to_search_params(self) -> dict:
        """Convert to search_restaurants() parameters.

        Returns:
            Dictionary of parameters suitable for the search_restaurants function
        """
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "radius_miles": self.radius_miles,
            "limit": self.limit,
        }

        if self.cuisine:
            params["cuisine"] = self.cuisine

        if self.min_rating:
            params["min_rating"] = self.min_rating

        if self.keywords:
            params["keywords"] = self.keywords

        return params

    def get_filter_summary(self) -> str:
        """Generate human-readable summary of active filters.

        Returns:
            String like "Italian • San Jose • $$ • ≥4★ • Vegetarian • within 3mi"
        """
        parts = []

        if self.cuisine:
            parts.append(self.cuisine)

        if self.location_name:
            parts.append(self.location_name)

        if self.max_price_level:
            parts.append("$" * self.max_price_level)

        if self.min_rating:
            parts.append(f"≥{self.min_rating}★")

        if self.dietary_restrictions:
            parts.append(" + ".join(self.dietary_restrictions))

        if self.radius_miles != 5.0:
            parts.append(f"within {self.radius_miles}mi")

        return " • ".join(parts) if parts else "No filters"

    def validate_filters(self) -> List[str]:
        """Check for contradictory or overly restrictive filters.

        Returns:
            List of warning messages (empty if no issues)
        """
        warnings = []

        # Check if search radius is too small
        if self.radius_miles < 2:
            warnings.append("Small search radius may limit results")

        # Check if rating threshold is very high
        if self.min_rating and self.min_rating >= 4.5:
            warnings.append("High rating threshold may limit results")

        # Check if too many filters are applied
        filter_count = sum([
            bool(self.cuisine),
            bool(self.min_rating),
            bool(self.max_price_level),
            len(self.dietary_restrictions) > 0,
            bool(self.keywords),
        ])

        if filter_count >= 4:
            warnings.append("Many active filters may significantly limit results")

        return warnings
