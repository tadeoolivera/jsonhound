import pytest

import jsonhound

# main(--no-color) rewrites these module-level globals in place. Snapshot and
# restore them around every test so color state never leaks between tests.
_COLOR_GLOBALS = ("GREEN", "RED", "YELLOW", "CYAN", "BOLD", "RESET", "DIM")


@pytest.fixture(autouse=True)
def restore_color_globals():
    saved = {name: getattr(jsonhound, name) for name in _COLOR_GLOBALS}
    yield
    for name, value in saved.items():
        setattr(jsonhound, name, value)
