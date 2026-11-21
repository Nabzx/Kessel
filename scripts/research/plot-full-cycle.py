#!/usr/bin/env python3
"""Plot all predeclared seeds and both methods from the retained study report."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def plot(evidence):
    report = json.loads((evidence/'report.json').read_text())
    plt.rcParams.update({'svg.hashsalt': 'kessel-full-cycle-v1', 'font.size': 10})
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout='constrained')
    colours = {7: '#245d98', 19: '#bf6b20', 41: '#278063'}
    for column, method in enumerate(('plain', 'curriculum')):
        for run in report['runs']:
            cfg = run['configuration']
            if cfg['method'] != method:
                continue
            seed = cfg['seed']; candidates = run['candidates']
            axes[0, column].plot([c['training_decisions'] for c in candidates],
                [c['score'][0] for c in candidates], marker='o', ms=3,
                color=colours[seed], label=f'Seed {seed}')
            rows = run['curve']
            if rows:
                # Fixed blocks, not a tuned smoothing window.
                blocks = [rows[i:i+16] for i in range(0, len(rows), 16)]
                axes[1, column].plot([b[-1]['counters']['training_decisions'] for b in blocks],
                    [np.mean([r['mean_step_reward'] for r in b]) for b in blocks],
                    color=colours[seed])
        axes[0, column].set(title=f'{method.capitalize()}: empty-start validation', ylim=(-.5, 16.5),
                                  ylabel='Complete deliveries /16')
        axes[1, column].set(title=f'{method.capitalize()}: training return', ylabel='Mean reward per decision\n(fixed 16-rollout blocks)')
        for row in range(2):
            axes[row, column].set(xlabel='On-policy training decisions', xlim=(0, 163840))
            axes[row, column].grid(alpha=.2)
        axes[0, column].legend(loc='upper right')
    fig.suptitle('Bounded synthetic full-cycle comparison: every declared seed\nPrepared-stage rewards are not complete-task successes', fontsize=13)
    fig.savefig(evidence/'learning-curves.svg', metadata={'Date': None})
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    plot(parser.parse_args().evidence)
