from gamegenie_x.models import Platform
from gamegenie_x.profiles import load_all_profiles, load_profile


def test_load_xboxone_profile() -> None:
    profile = load_profile("xboxone")
    assert profile.platform == "xboxone"
    assert profile.name == "Xbox One"
    assert profile.io_strategy is not None
    assert profile.io_strategy.strategy == "binary"
    assert "bin" in profile.io_strategy.save_formats
    assert profile.fields is not None
    assert "currency" in profile.fields
    assert profile.fields["currency"].offset == 0x1000

def test_load_ps5_profile() -> None:
    profile = load_profile("ps5")
    assert profile.platform == "ps5"
    assert profile.name == "PlayStation 5"
    assert profile.io_strategy is not None
    assert profile.io_strategy.strategy == "container"
    assert "sfo" in profile.io_strategy.save_formats

def test_load_all_profiles_includes_modern() -> None:
    profiles = load_all_profiles()
    assert "xboxone" in profiles
    assert "xboxseries" in profiles
    assert "ps4" in profiles
    assert "ps5" in profiles
    assert Platform.NES in profiles
