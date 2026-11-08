"""Run a reviewed authoring script in headless Blender.

    /Applications/Blender.app/Contents/MacOS/Blender --background \
      --factory-startup --python tools/blender/run-headless.py -- portal

Same reviewed local scripts as client.py executes through the pinned MCP
connector, with the same REPO_ROOT/EXPERIENCE/TRUCK prelude. This route needs
no connector checkout and no Blender window, so the authored assets can be
rebuilt reproducibly from the repository alone. The MCP path stays available
for interactive work; see tools/blender/README.md.
"""
import json
import pathlib
import sys

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if not argv:
    raise SystemExit('Name a script, e.g. -- portal')

root = pathlib.Path(__file__).resolve().parents[2]
script = (root / 'tools/blender' / (argv[0] + '.py'))
if not script.exists():
    raise SystemExit(f'No such authoring script: {script}')

experience = json.loads((root / 'data/experience.json').read_text())
truck = json.loads((root / experience['assets']['truck']).read_text())

namespace = {
    '__name__': '__main__',
    'REPO_ROOT': str(root),
    'EXPERIENCE': experience,
    'TRUCK': truck,
}
exec(compile(script.read_text(), str(script), 'exec'), namespace)
