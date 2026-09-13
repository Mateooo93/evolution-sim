"""Shared colour palette and layout metrics — the lab dark theme.

Everything the UI draws pulls its colour from here, so the whole app can
be re-skinned in one place. Surfaces are stacked (BG < PANEL < RAISED)
so panels read as layers instead of one flat sheet.
"""

# --- surfaces ---------------------------------------------------------
BG = (11, 15, 20)          # window background
PANEL = (16, 22, 29)       # chrome panels
RAISED = (23, 31, 41)      # tiles inside a panel, buttons
RAISED_HOVER = (30, 41, 54)  # tile/button under the cursor
PANEL_BORDER = (29, 39, 51)
BORDER_HOVER = (52, 69, 88)
METER_BG = (26, 35, 46)    # empty part of a bar

# --- text -------------------------------------------------------------
TEXT = (226, 232, 240)
TEXT_DIM = (128, 144, 168)
TEXT_FAINT = (78, 93, 113)

# --- accents ----------------------------------------------------------
ACCENT = (52, 211, 153)    # organism green / interactive accent
ACCENT_DIM = (26, 92, 71)  # accents that must sit behind text
PREDATOR = (248, 113, 113)  # predator organism — warm red, the danger read
PREDATOR_DIM = (110, 48, 48)
FOOD = (212, 175, 55)      # food item — amber, distinct from organism green
FOOD_HI = (251, 211, 92)   # eat-pulse ring, brighter than the orb
HEADING = (32, 140, 102)   # prey heading tick, dimmer than the dot
HEADING_PRED = (160, 60, 60)  # predator heading tick
GOLD = (250, 204, 21)      # "recording" and highlight chrome
GRID_ALPHA = 14            # lab-plate grid line alpha (0-255)

# --- layout -----------------------------------------------------------
MARGIN = 12                # gap between window edge and chrome
GAP = 10                   # gap between stacked panels
PANEL_PAD = 12             # padding inside a panel
HEADER_H = 52
KEYBAR_H = 26
SIDEBAR_W = 300
