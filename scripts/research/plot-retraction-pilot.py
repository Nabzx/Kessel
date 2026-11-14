"""Plot all predeclared pilot seeds from retained measured validation results."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt'] = 'kessel-retraction-pilot-v1'
import matplotlib.pyplot as plt

folder = Path(__file__).resolve().parents[2] / 'docs/phase-11/retraction-pilot-evidence'
report = json.loads((folder / 'report.json').read_text())
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), sharey=True)
colours = {7: '#b47c2a', 19: '#397a6a', 41: '#4c6e9f'}
for ax, setting in zip(axes, ('baseline', 'steering')):
    for run in report['runs']:
        if run['configuration']['setting'] != setting:
            continue
        seed = run['configuration']['seed']
        points = run['candidates']
        ax.plot([p['rollout'] * 256 for p in points], [p['score'][0] for p in points],
                marker='o', markersize=4, lw=1.8, color=colours[seed], label=f'Seed {seed}')
    ax.axhline(14, color='#777777', linestyle='--', lw=.9, label='14/16 pilot threshold')
    ax.set_title('Default exploration' if setting == 'baseline' else 'Reduced steering exploration')
    ax.set_xlabel('Training decisions')
    ax.set_xticks([0, 8192, 16384, 24576, 32768])
    ax.set_xticklabels(['0', '8,192', '16,384', '24,576', '32,768'], fontsize=8)
    ax.set_ylim(-.5, 16.7)
    ax.set_yticks([0, 4, 8, 12, 16])
    ax.grid(axis='y', alpha=.18)
    ax.spines[['top', 'right']].set_visible(False)
axes[0].set_ylabel('Successful fixed validation starts / 16')
fig.suptitle('Prepared retraction pilot: all predeclared seeds', fontsize=13)
fig.legend(*axes[0].get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(.5, .91), ncol=4, fontsize=9, frameon=False)
fig.text(.5, .02, '1,500 kg initial payload. This is an isolated skill, not an empty-start delivery cycle.', ha='center', fontsize=9)
fig.tight_layout(rect=(0, .06, 1, .84))
fig.savefig(folder / 'learning-curves.svg', metadata={'Creator': 'Kessel', 'Date': None})
