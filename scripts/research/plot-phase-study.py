#!/usr/bin/env python3
"""Plot every declared seed, including unsuccessful memoryless runs."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(evidence):
    r=json.loads((evidence/'report.json').read_text());plt.rcParams['svg.hashsalt']='phase-imitation-v1'
    fig,axes=plt.subplots(1,2,figsize=(10,4.2),layout='constrained');colours={7:'#245d98',19:'#bf6b20',41:'#278063'}
    for ax,method in zip(axes,('memoryless','phase_memory')):
        for seed in (7,19,41):
            name=f'{method}-{seed}';rows=r['runs'][name];x=[1500+750*c['round'] for c in rows];y=[c['score'][0] for c in rows]
            ax.plot(x,y,marker='o',label=f'Seed {seed}',color=colours[seed]);chosen=r['selection'][name];ax.scatter([1500+750*chosen['round']],[chosen['score'][0]],s=110,facecolors='none',edgecolors=colours[seed],linewidths=1.6)
        ax.set(title='Explicit phase memory' if method=='phase_memory' else 'Memoryless comparator',xlabel='Supervised minibatch updates per seed',ylabel='Complete validation deliveries /16',ylim=(-.5,16.7),xticks=[1500,2250,3000,3750]);ax.grid(alpha=.2);ax.legend(loc='lower right')
    fig.suptitle('Shared teacher coverage and mixed-phase replay\nRings mark validation-selected checkpoints; final tests do not select',fontsize=12)
    fig.savefig(evidence/'learning-curves.svg',metadata={'Date':None});plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);plot(p.parse_args().evidence)
