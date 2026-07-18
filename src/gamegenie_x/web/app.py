"""Module E3: Web Application using FastAPI."""

from __future__ import annotations

import contextlib
import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from gamegenie_x import decode
from gamegenie_x.game_profiles import load_game_profile_by_id
from gamegenie_x.library import PatchLibrary
from gamegenie_x.patch_v2 import from_legacy_patch
from gamegenie_x.preview import PreviewEngine
from gamegenie_x.profiles import load_profile

app = FastAPI(
    title="GameGenie-X Web Hub",
    description="A retro web interface for modern patch decoding, library browsing, and sharing.",
)

# Setup path for metadata persistence
BASE_DIR = Path(__file__).resolve().parent
SHARES_FILE = BASE_DIR / "shares.json"
INDEX_FILE = BASE_DIR / "index.html"


def _load_shares() -> dict[str, Any]:
    """Loads shared codes metadata from shares.json."""
    if not SHARES_FILE.exists():
        return {}
    try:
        with open(SHARES_FILE, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_share(code: str, metadata: dict[str, Any]) -> str:
    """Stores a sharing link metadata using standard MD5 hash of the code."""
    shares = _load_shares()
    # Ensure code is normalized to standard format (strip whitespace)
    normalized = code.strip().upper()
    hashed = hashlib.md5(normalized.encode("utf-8")).hexdigest()[:12]
    shares[hashed] = {
        "code": normalized,
        "metadata": metadata,
    }
    try:
        with open(SHARES_FILE, "w", encoding="utf-8") as f:
            json.dump(shares, f, indent=2)
    except Exception:
        pass
    return hashed


@app.get("/", response_class=HTMLResponse)
def get_index() -> str:
    """Serves the Vanilla HTML+JS homepage.

    Returns:
        The content of index.html.
    """
    if INDEX_FILE.exists():
        return INDEX_FILE.read_text(encoding="utf-8")
    return "<h1>GameGenie-X Web Hub</h1><p>Frontend file index.html is missing.</p>"


@app.get("/decode")
def web_decode(
    code: str = Query(..., description="The GameGenie-X code string")
) -> dict[str, Any]:
    """Decodes a GameGenie-X code into structural explanation.

    Args:
        code: Code to decode.

    Returns:
        A dictionary representation of the decoded patch.
    """
    try:
        # Decode legacy patch
        legacy = decode(code, verify=False)
        # Determine platform profile for detailed mapping
        from gamegenie_x.models import Platform
        plat = legacy.platform
        plat_profile = (
            load_profile("ps5") if plat == Platform.UNIVERSAL else load_profile(plat)
        )
        patch_seq = from_legacy_patch(legacy, plat_profile)

        # Build response details
        patches_list = []
        for p in patch_seq.patches:
            patches_list.append({
                "target_type": p.target_type.value,
                "offset": p.offset,
                "key_path": p.key_path,
                "new_value": p.new_value,
                "compare_value": p.compare_value,
                "patch_type": p.patch_type.value,
            })

        return {
            "code": code,
            "legacy": {
                "address": legacy.address,
                "value": legacy.value,
                "compare": legacy.compare,
                "platform": legacy.platform.name,
                "patch_type": legacy.patch_type.name,
                "flags": {
                    "compare_enabled": legacy.flags.compare_enabled,
                    "wide_data": legacy.flags.wide_data,
                    "read_only": legacy.flags.read_only,
                    "persistent": legacy.flags.persistent,
                },
            },
            "modern": {
                "platform": plat_profile.name,
                "patches": patches_list,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to decode code: {e}"
        ) from e


@app.get("/preview")
def web_preview(
    code: str = Query(..., description="The GameGenie-X code string"),
    profile: str = Query(..., description="Path/name of game profile JSON or game_id"),
) -> dict[str, Any]:
    """Previews a patch sequence on a mock/loaded game profile.

    Args:
        code: Code to preview.
        profile: Profile identifier.

    Returns:
        Preview results as a structured dictionary.
    """
    try:
        # Decode the code
        legacy = decode(code, verify=False)
        from gamegenie_x.models import Platform
        plat = legacy.platform
        plat_profile = (
            load_profile("ps5") if plat == Platform.UNIVERSAL else load_profile(plat)
        )
        patch_seq = from_legacy_patch(legacy, plat_profile)

        # Retrieve game profile
        # First attempt loading by ID or from typical directory
        try:
            # First try profiles/ relative path or standard profiles directory
            p_path = Path("profiles") / f"{profile}.json"
            if p_path.exists():
                game_profile = load_game_profile_by_id(profile, profiles_dir="profiles")
            else:
                p_dir = Path(__file__).resolve().parents[3] / "profiles"
                game_profile = load_game_profile_by_id(profile, profiles_dir=p_dir)
        except Exception:
            # Fallback to load direct filepath
            from gamegenie_x.game_profiles import load_game_profile
            game_profile = load_game_profile(profile)

        # Mock save file content depending on profile format
        save_bytes = b"\x00" * 1000
        if game_profile.format == "json":
            # Valid minimal JSON dictionary
            save_bytes = b"{}"

        # Preview execution
        preview_engine = PreviewEngine()
        results = preview_engine.preview(patch_seq, save_bytes, game_profile)

        # Format results
        output = []
        for r in results:
            output.append({
                "field_name": r.field_name,
                "offset_or_key_path": r.offset_or_key_path,
                "old_value": r.old_value,
                "new_value": r.new_value,
                "compare_matched": r.compare_matched,
                "safety_passed": r.safety_passed,
                "safety_errors": r.safety_errors,
                "applied": r.applied,
            })

        return {
            "code": code,
            "game": game_profile.display_name,
            "results": output,
        }
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to preview code: {e}"
        ) from e


@app.get("/library/{game}")
def web_list_library(game: str) -> dict[str, Any]:
    """Lists categories and curated patch names for a specific game in the library."""
    try:
        # Load profile first from profiles dir
        with contextlib.suppress(Exception):
            load_game_profile_by_id(game, profiles_dir="profiles")

        lib = PatchLibrary(profiles_dir="profiles")
        categories = lib.list_categories(game)
        cats_dict = {}
        for cat in categories:
            patches = lib.get_patches(game, cat)
            cats_dict[cat] = [
                {
                    "name": p.name,
                    "description": p.description,
                    "code": p.code,
                }
                for p in patches
            ]
        return {
            "game": game,
            "categories": cats_dict,
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/library/{game}/{patch}")
def web_patch_details(game: str, patch: str) -> dict[str, Any]:
    """Gets details of a specific patch from the library."""
    try:
        lib = PatchLibrary(profiles_dir="profiles")
        categories = lib.list_categories(game)
        found_patch = None
        for cat in categories:
            for p in lib.get_patches(game, cat):
                p_name_norm = p.name.lower().replace(" ", "-")
                if p_name_norm == patch.lower() or p.name.lower() == patch.lower():
                    found_patch = p
                    break
            if found_patch:
                break

        if not found_patch:
            raise HTTPException(status_code=404, detail=f"Patch '{patch}' not found.")

        return {
            "game": game,
            "name": found_patch.name,
            "description": found_patch.description,
            "code": found_patch.code,
            "safety_metadata": found_patch.safety_metadata,
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/share")
def web_share_code(payload: dict[str, Any]) -> dict[str, str]:
    """Saves minimal sharing metadata and returns a generated hash/link."""
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing required 'code' field.")
    metadata = payload.get("metadata", {})
    hashed = _save_share(code, metadata)
    return {
        "hash": hashed,
        "url": f"/share/{hashed}",
    }


@app.get("/share/{hash_id}")
def web_resolve_share(hash_id: str) -> dict[str, Any]:
    """Resolves a shared link back to its saved metadata and code details."""
    shares = _load_shares()
    if hash_id not in shares:
        raise HTTPException(status_code=404, detail="Shared link not found or expired.")
    result = shares[hash_id]
    if isinstance(result, dict):
        return result
    raise HTTPException(status_code=500, detail="Malformed share data stored.")
