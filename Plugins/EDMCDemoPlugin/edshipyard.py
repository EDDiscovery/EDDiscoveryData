"""Export ship loadout in ED Shipyard plain text format."""
from __future__ import annotations

import json
import os
import pathlib
import re
import time
from collections import defaultdict
from typing import Union

import util_ships
from config import config
from edmc_data import edshipyard_slot_map as slot_map
from edmc_data import ship_name_map
from EDMCLogging import get_main_logger

logger = get_main_logger()

__Module = dict[str, Union[str, list[str]]]  # Have to keep old-style here for compatibility

# Map API ship names to ED Shipyard names
ship_map = ship_name_map.copy()

# Ship masses
ships_file = config.respath_path / "ships.json"
with open(ships_file, encoding="utf-8") as ships_file_handle:
    ships = json.load(ships_file_handle)


