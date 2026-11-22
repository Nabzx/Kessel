#!/usr/bin/env python3
"""All-family, all-source synthetic stress scorecard; no curated success subset."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
r=json.loads(a.report.read_text());families=r['plan']['families'];sources=r['plan']['sources']
values=np.array([[next(x['successes'] for x in r['summaries'] if x['family']==f and x['source']==s) for f in families] for s in sources])
fig,ax=plt.subplots(figsize=(15,4));fig.patch.set_facecolor('#fafaf6');ax.set_facecolor('#fafaf6')
ax.imshow(values,vmin=0,vmax=8,cmap='YlGn',aspect='auto')
for y,s in enumerate(sources):
    for x,f in enumerate(families):
        row=next(v for v in r['summaries'] if v['family']==f and v['source']==s)
        ax.text(x,y,f'{row["successes"]}/8\n{row["collisions"]} collisions',ha='center',va='center',fontsize=8,color='white' if row['successes']>=6 else '#172820')
ax.set_xticks(range(len(families)),[f.replace('_','\n') for f in families],fontsize=9)
ax.set_yticks(range(len(sources)),['Neural seed 7','Neural seed 19','Neural seed 41','Conventional reference'],fontsize=10)
ax.set_title('Frozen-policy synthetic stress test: complete empty-start deliveries',loc='left',pad=16,fontsize=14)
ax.tick_params(length=0);fig.text(.01,.01,'Eight shared base scenarios per family. Each source runs all 104 scenarios. The conventional reference is a separate comparator.',fontsize=9)
fig.tight_layout(rect=(0,.04,1,1));fig.savefig(a.output,format='svg');plt.close(fig)
