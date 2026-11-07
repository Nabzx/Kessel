"""Run with Blender --factory-startup --python tools/blender/start.py.

Set BLENDER_CONNECTOR_DIR to the inspected pinned checkout. This creates an
isolated authoring server; it never opens or modifies a user's working file.
"""
import importlib.util
import os
from pathlib import Path
import sys
import bpy
connector=Path(os.environ['BLENDER_CONNECTOR_DIR']).resolve()
spec=importlib.util.spec_from_file_location('kessel_blender_mcp',connector/'addon.py')
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon)
addon.register()
server=addon.BlenderMCPServer(host='127.0.0.1',port=9877)
server.start();bpy.app.driver_namespace['kessel_mcp_server']=server
print('KESSEL_AUTHORING_READY',bpy.app.version_string,flush=True)
