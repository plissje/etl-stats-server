from app.parsers.names import strip_quake_colors
from app.parsers.weapon_stats import unpack_weapon_stats, WS_SYRINGE_SLOT


def test_strip_quake_colors():
    assert strip_quake_colors("^7e^1S^7r") == "eSr"
    assert strip_quake_colors("") == ""


def test_unpack_sample_mask_48():
    # bits 4 and 5: two weapon blocks + 10 tail (from refs/sample_simple.json shape)
    ws = ["48", "7", "23", "1", "0", "0", "6", "20", "1", "0", "1", "250", "126", "0", "0", "0", "0", "0", "0", "100.0", "9"]
    u = unpack_weapon_stats(ws)
    assert u is not None
    assert u.mask == 48
    assert len(u.weapons) == 2
    assert u.weapons[0].slot == 4
    assert u.weapons[0].hits == 7
    assert u.weapons[1].slot == 5
    assert u.damage_given == 250
    assert u.damage_received == 126
    assert u.xp == 9


def test_syringe_slot_unpack():
    mask = 1 << WS_SYRINGE_SLOT
    ws = [str(mask), "3", "10", "0", "0", "1"] + ["0"] * 10
    u = unpack_weapon_stats(ws)
    assert u is not None
    assert u.weapons[0].slot == WS_SYRINGE_SLOT
    assert u.weapons[0].hits == 3
