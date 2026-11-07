# Local Blender authoring

The verified maintainer installation is Blender 5.2.3 LTS, build e13b728c6880.
Connector: ahujasid/mcp-for-blender revision
2e4b0bc294694b1570d76ed01be657c22e6d02a0, package 2.2.7, MCP SDK 1.30.0.
Use an isolated Python environment for the connector. No tool is installed in
or served by the static site. Do not replace the maintainer's active Blender
scene or disable MCP safe mode to run authoring scripts.

Launch a separate authoring window:

```sh
BLENDER_CONNECTOR_DIR=/path/to/pinned/connector \
BLENDER_USER_CONFIG=/private/tmp/kessel-blender-profile \
DISABLE_TELEMETRY=true BLENDER_MCP_SAFE_MODE=1 \
/Applications/Blender.app/Contents/MacOS/Blender --factory-startup \
  --python tools/blender/start.py
```

Run `client.py` in the isolated connector environment, with `--script` pointing
to author.py, rigs.py, bake.py or material-library.py and `--prompt` containing
the maintainer's instruction verbatim. Scripts are reviewed local code. The
client forwards it through MCP's execute_blender_code tool with safe mode on,
telemetry off and socket 127.0.0.1:9877. It never enables a hosted generator or
uploads source assets. The addon executes on Blender's main thread. A stdio
client disconnect releases its connection; the server remains in the dedicated
window. Close that window to stop the endpoint, then rerun start.py to recover.

Run author.py, rigs.py, bake.py and material-library.py in that order. The client
stages a copy of the licensed excavator and gives duplicate original node names
unique source-index identifiers before importing it. Each script explicitly
clears this isolated authoring scene, including hidden objects. Metre units,
seeds, pivots, physical scales and sources are explicit. Pack source images in
portable .blend scenes. Raw bakes and backups never enter the static package.

Convert the two raw PNG bakes under bakes/ to lossless WebP in assets/authored,
then run manifest.py, scripts/verify-authored-assets.py, the official Khronos
glTF validator and scripts/verify-authored.cjs. Keep native first-use and settled
measurements. The material study retains PNG/WebP/atlas/KTX2 comparisons; WebP
is selected for these small maps. The source library preserves cleared image
nodes and proper sRGB/linear channel interpretation. Original Blender source
geometry is not automatically the reference simulator's collision geometry.
