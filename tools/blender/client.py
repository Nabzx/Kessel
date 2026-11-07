"""Execute a reviewed local asset script through the pinned Blender MCP tool.

Requires the isolated mcp-for-blender environment, not the training environment.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run(args):
    env={**os.environ,'BLENDER_HOST':'127.0.0.1','BLENDER_PORT':'9877',
         'DISABLE_TELEMETRY':'true','BLENDER_MCP_DISABLE_TELEMETRY':'1','BLENDER_MCP_SAFE_MODE':'1'}
    server=str(Path(sys.executable).with_name('mcp-for-blender'))
    params=StdioServerParameters(command=server,env=env)
    root=Path(__file__).resolve().parents[2]
    experience=json.loads((root/'data/experience.json').read_text());truck=json.loads((root/experience['assets']['truck']).read_text())
    code=f'REPO_ROOT = {str(root)!r}\nEXPERIENCE = {experience!r}\nTRUCK = {truck!r}\n'+args.script.read_text()
    if args.script.name=='rigs.py':
        import gzip,shutil,tempfile
        trace=json.loads(gzip.decompress((root/'docs/phase-11/reference-repair-evidence/legacy-100000.json.gz').read_bytes()))
        last=trace['records'][-1]
        trace={'records':[{'state':r['state'][:11],'next_t_s':r['next_t_s'],'wheel_angles_rad':r['wheel_angles_rad']} for r in trace['records']]}
        trace['records'].append({'state':last['next_state'][:11],'next_t_s':last['next_t_s'],'wheel_angles_rad':last['next_wheel_angles_rad']})
        target=Path(tempfile.mkdtemp(prefix='kessel-excavator-'))/'excavator'
        shutil.copytree(root/'assets/models/excavator',target)
        gltf=json.loads((target/'excavator.gltf').read_text())
        for i,node in enumerate(gltf['nodes']):
            node['name']=f'KesselNode_{i}'
            node.setdefault('extras',{})['original_node_index']=i
        (target/'excavator.gltf').write_text(json.dumps(gltf))
        code=f'REFERENCE_TRACE = {trace!r}\nEXCAVATOR_COPY = {str(target/"excavator.gltf")!r}\n'+code
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            result=await session.call_tool('execute_blender_code',{'code':code,'user_prompt':args.prompt})
            messages=[c.text for c in result.content if c.type=='text']
            print('\n'.join(messages),flush=True)
            if result.isError or any('Rejected by safe mode' in m or m.startswith('Error executing code') for m in messages):
                raise RuntimeError('Blender MCP authoring failed; inspect the retained log')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--script',type=Path,required=True)
    p.add_argument('--prompt',required=True,help='The maintainer instruction, quoted verbatim')
    asyncio.run(run(p.parse_args()))
