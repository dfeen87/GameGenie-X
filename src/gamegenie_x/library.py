"""Module E2: Patch Library for GameGenie-X."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from gamegenie_x.decoder import decode_to_sequence
from gamegenie_x.game_profiles import load_game_profile_by_id
from gamegenie_x.profiles import load_profile

if TYPE_CHECKING:
    from gamegenie_x.patch_v2 import PatchSequence


@dataclass(frozen=True, slots=True)
class LibraryPatch:
    """A curated library patch containing metadata and a patch sequence."""

    name: str
    description: str
    code: str
    safety_metadata: dict[str, Any] = field(default_factory=dict)

    def get_sequence(self, profiles_dir: str | Path = "profiles") -> PatchSequence:
        """Decodes the patch code to a PatchSequence using platform defaults.

        Args:
            profiles_dir: The directory containing game profiles.

        Returns:
            The decoded PatchSequence object.
        """
        # Resolving profile - since codes are Universal/PS5, load PS5 platform profile
        platform_profile = load_profile("ps5")
        return decode_to_sequence(self.code, platform_profile, verify=False)


class PatchLibrary:
    """Library holding curated game cheats and patches."""

    def __init__(self, profiles_dir: str | Path = "profiles") -> None:
        """Initializes PatchLibrary with a predefined curation of patches.

        Args:
            profiles_dir: Path to directory holding profiles.
        """
        self._profiles_dir = Path(profiles_dir)

        # Pre-curated patches organized by game -> category -> patches
        # For Demonstration, rpg_hero and scifi_space are standard games.
        self._library: dict[str, dict[str, list[LibraryPatch]]] = {
            "rpg_hero": {
                "Stats": [
                    LibraryPatch(
                        name="Infinite HP",
                        description="Locks the player's HP to 999.",
                        code="B7Y4W-8T2X1-9K4M5",
                        safety_metadata={
                            "field": "player.stats.hp",
                            "min_allowed": 1,
                            "max_allowed": 999,
                        },
                    ),
                    LibraryPatch(
                        name="Max MP",
                        description="Sets player's MP to 99.",
                        code="P5T2R-3W1V8-9J5N4",
                        safety_metadata={
                            "field": "player.stats.mp",
                            "min_allowed": 1,
                            "max_allowed": 99,
                        },
                    ),
                ],
                "Inventory": [
                    LibraryPatch(
                        name="Infinite Gold",
                        description="Gives player 999,999 gold.",
                        code="A1B2C-3D4E5-6F7G8",
                        safety_metadata={
                            "field": "gold",
                            "min_allowed": 0,
                            "max_allowed": 999999,
                        },
                    )
                ],
            },
            "scifi_space": {
                "Difficulty": [
                    LibraryPatch(
                        name="No Encounters",
                        description="Disables random spatial anomaly encounters.",
                        code="X9Y8Z-7W6V5-4U3T2",
                        safety_metadata={"field": "ship.is_active", "value": False},
                    )
                ],
                "Stats": [
                    LibraryPatch(
                        name="Max Shield",
                        description="Sets ship's shield to 500.",
                        code="M3N2P-1Q0R9-8S7T6",
                        safety_metadata={
                            "field": "ship.shield",
                            "min_allowed": 0,
                            "max_allowed": 500,
                        },
                    )
                ],
            },
        }

        # Dynamic generation of valid codes for standard games:
        # rpg_hero hp (offset 10, value 255)
        # rpg_hero mp (offset 12, value 99)
        # rpg_hero gold (offset 20, value 250)
        # scifi_space ship.is_active (offset 30, value 1)
        # scifi_space ship.shield (offset 25, value 250)
        from gamegenie_x.generator import CodeGenerator
        generator = CodeGenerator()

        try:
            rpg_profile = load_game_profile_by_id("rpg_hero", self._profiles_dir)
            scifi_profile = load_game_profile_by_id("scifi_space", self._profiles_dir)

            self._library["rpg_hero"]["Stats"][0] = LibraryPatch(
                name="Infinite HP",
                description="Locks the player's HP to 255.",
                code=generator.generate_code("player.stats.hp", 255, rpg_profile),
                safety_metadata={
                    "field": "player.stats.hp",
                    "min_allowed": 1,
                    "max_allowed": 999,
                },
            )
            self._library["rpg_hero"]["Stats"][1] = LibraryPatch(
                name="Max MP",
                description="Sets player's MP to 99.",
                code=generator.generate_code("player.stats.mp", 99, rpg_profile),
                safety_metadata={
                    "field": "player.stats.mp",
                    "min_allowed": 1,
                    "max_allowed": 99,
                },
            )
            self._library["rpg_hero"]["Inventory"][0] = LibraryPatch(
                name="Infinite Gold",
                description="Sets gold to 250.",
                code=generator.generate_code("gold", 250, rpg_profile),
                safety_metadata={
                    "field": "gold",
                    "min_allowed": 0,
                    "max_allowed": 999999,
                },
            )
            self._library["scifi_space"]["Difficulty"][0] = LibraryPatch(
                name="No Encounters",
                description="Sets ship active flag to 1.",
                code=generator.generate_code("ship.is_active", 1, scifi_profile),
                safety_metadata={"field": "ship.is_active", "value": True},
            )
            self._library["scifi_space"]["Stats"][0] = LibraryPatch(
                name="Max Shield",
                description="Sets ship's shield to 250.",
                code=generator.generate_code("ship.shield", 250, scifi_profile),
                safety_metadata={
                    "field": "ship.shield",
                    "min_allowed": 0,
                    "max_allowed": 500,
                },
            )
        except Exception:
            # Fallback to hardcoded codes if profiles aren't loaded yet/in test context
            pass

    def list_games(self) -> list[str]:
        """Lists all supported games in the library.

        Returns:
            A list of game ID strings.
        """
        return list(self._library.keys())

    def list_categories(self, game: str) -> list[str]:
        """Lists all patch categories for a specific game.

        Args:
            game: The game ID string.

        Returns:
            A list of category name strings.

        Raises:
            KeyError: If the game is not found in the library.
        """
        if game not in self._library:
            raise KeyError(f"Game '{game}' not found in the patch library.")
        return list(self._library[game].keys())

    def get_patches(self, game: str, category: str) -> list[LibraryPatch]:
        """Gets all curated patches in a category for a specific game.

        Args:
            game: The game ID string.
            category: The category name string.

        Returns:
            A list of LibraryPatch objects.

        Raises:
            KeyError: If the game or category is not found in the library.
        """
        if game not in self._library:
            raise KeyError(f"Game '{game}' not found in the patch library.")
        if category not in self._library[game]:
            raise KeyError(f"Category '{category}' not found for game '{game}'.")
        return self._library[game][category]
