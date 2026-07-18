"""Unit tests for the Web Viewer FastAPI endpoints and sharing system (E3)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from gamegenie_x.web.app import app

client = TestClient(app)


def test_web_index_serves_html() -> None:
    """Verifies the root endpoint serves our custom retro homepage."""
    response = client.get("/")
    assert response.status_code == 200
    assert "GameGenie-X Web Hub" in response.text


def test_web_decode_endpoint() -> None:
    """Verifies /decode?code=XXX returns structured JSON analysis."""
    # Create valid code for universal NES address 0x1000, value 0x55
    from gamegenie_x.game_profiles import load_game_profile_by_id
    from gamegenie_x.generator import CodeGenerator
    rpg_profile = load_game_profile_by_id("rpg_hero", profiles_dir="profiles")
    generator = CodeGenerator()
    code = generator.generate_code("player.stats.hp", 200, rpg_profile)

    response = client.get(f"/decode?code={code}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == code
    assert "legacy" in data
    assert data["legacy"]["value"] == 200
    assert "modern" in data


def test_web_preview_endpoint() -> None:
    """Verifies /preview runs non-destructive safety checks and outputs json."""
    from gamegenie_x.game_profiles import load_game_profile_by_id
    from gamegenie_x.generator import CodeGenerator
    rpg_profile = load_game_profile_by_id("rpg_hero", profiles_dir="profiles")
    generator = CodeGenerator()
    code = generator.generate_code("player.stats.hp", 200, rpg_profile)

    response = client.get(f"/preview?code={code}&profile=rpg_hero")
    assert response.status_code == 200
    data = response.json()
    assert data["game"] == "RPG Hero v2"
    assert len(data["results"]) == 1
    assert data["results"][0]["safety_passed"] is True


def test_web_library_endpoints() -> None:
    """Verifies listing patches and patch details from the library."""
    response = client.get("/library/rpg_hero")
    assert response.status_code == 200
    data = response.json()
    assert data["game"] == "rpg_hero"
    assert "Stats" in data["categories"]

    # Patch details
    response = client.get("/library/rpg_hero/infinite-hp")
    assert response.status_code == 200
    details = response.json()
    assert details["name"] == "Infinite HP"
    assert "code" in details


def test_web_sharing_link_flow() -> None:
    """Verifies hashing, persistent sharing, and resolving of links."""
    share_payload = {
        "code": "A1B2C-3D4E5-6F7G8",
        "metadata": {
            "title": "Invincibility",
            "author": "GhostHacker",
        }
    }

    # Post to create shareable link
    response = client.post("/share", json=share_payload)
    assert response.status_code == 200
    data = response.json()
    assert "hash" in data
    assert "url" in data

    # Get to resolve shared link
    hash_id = data["hash"]
    resolve_response = client.get(f"/share/{hash_id}")
    assert resolve_response.status_code == 200
    resolved_data = resolve_response.json()
    assert resolved_data["code"] == "A1B2C-3D4E5-6F7G8"
    assert resolved_data["metadata"]["author"] == "GhostHacker"
