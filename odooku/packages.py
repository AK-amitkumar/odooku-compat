import os.path
import json
import importlib


ODOOKU_JSON_FILE = os.path.abspath('odooku.json')

addon_paths = []
cli_commands = []


def init_packages():
    odooku_json = {}
    if os.path.isfile(ODOOKU_JSON_FILE):
        with open(ODOOKU_JSON_FILE) as f:
            odooku_json = json.load(f)

    for module_name in odooku_json.get('odooku', {}).get('packages', []):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            # For now be explit..
            raise

        # Look for addons folder in module package
        addons_path = os.path.join(os.path.dirname(module.__file__), 'addons')
        if os.path.isdir(addons_path):
            addon_paths.append(addons_path)

        # Look for cli commands
        cli_commands += getattr(module, 'cli_commands', [])
