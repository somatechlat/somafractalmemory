"""Unit tests for Django ORM models.

Tests coordinate conversion and model methods without database.

VIBE Coding Rules:
- NO mocks, only pure Python logic
- Tests Django model classmethod utilities
"""

from somafractalmemory.apps.core.models import Memory


class TestMemoryCoordinateConversion:
    """Test Memory.coord_to_key and key_to_coord methods."""

    def test_coord_to_key_basic(self):
        """Convert a basic 3D coordinate to string key."""
        key = Memory.coord_to_key((1.0, 2.0, 3.0))
        assert key == "1.0,2.0,3.0"

    def test_coord_to_key_negative(self):
        """Convert coordinate with negative values."""
        key = Memory.coord_to_key((-1.5, 2.5, -3.5))
        assert key == "-1.5,2.5,-3.5"

    def test_coord_to_key_list_input(self):
        """Accept list as well as tuple."""
        key = Memory.coord_to_key([4.0, 5.0, 6.0])
        assert key == "4.0,5.0,6.0"

    def test_coord_to_key_high_dimension(self):
        """Convert high-dimensional coordinate."""
        coord = tuple(float(i) for i in range(10))
        key = Memory.coord_to_key(coord)
        assert key == "0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0"

    def test_key_to_coord_basic(self):
        """Convert string key back to coordinate tuple."""
        coord = Memory.key_to_coord("1.0,2.0,3.0")
        assert coord == (1.0, 2.0, 3.0)

    def test_key_to_coord_with_spaces(self):
        """Handle keys with extra spaces."""
        coord = Memory.key_to_coord(" 1.0 , 2.0 , 3.0 ")
        assert coord == (1.0, 2.0, 3.0)

    def test_key_to_coord_negative(self):
        """Convert key with negative values."""
        coord = Memory.key_to_coord("-1.5,2.5,-3.5")
        assert coord == (-1.5, 2.5, -3.5)

    def test_roundtrip(self):
        """Verify coord_to_key and key_to_coord are inverse operations."""
        original = (7.7, 8.8, 9.9)
        key = Memory.coord_to_key(original)
        recovered = Memory.key_to_coord(key)
        assert recovered == original


class TestMemoryTypeChoices:
    """Test MemoryType enum values."""

    def test_episodic_value(self):
        """Verify EPISODIC choice value."""
        assert Memory.MemoryType.EPISODIC == "episodic"

    def test_semantic_value(self):
        """Verify SEMANTIC choice value."""
        assert Memory.MemoryType.SEMANTIC == "semantic"

    def test_choices_are_valid(self):
        """Verify choices format for Django."""
        choices = Memory.MemoryType.choices
        assert ("episodic", "Episodic") in choices
        assert ("semantic", "Semantic") in choices
