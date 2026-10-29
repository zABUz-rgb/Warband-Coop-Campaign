
# Point export_dir to the folder you will be keeping your module
# Make sure you use forward slashes (/) and NOT backward slashes (\)

# CoopWorld: build into the test copy of the game, never into the original install
import os
# the repository's game/Modules/Warband Coop Campaign, wherever the repository is
export_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/") + "/game/Modules/Warband Coop Campaign/"
