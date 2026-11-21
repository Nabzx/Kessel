#!/usr/bin/env python3
"""Package the admitted recorded demo as an offline static preview, without weights."""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def package(output):
    source=ROOT/'docs/phase-11/phase-memory-demo';catalogue=json.loads((source/'catalogue.json').read_text())
    if catalogue.get('admitted') is not True or len(catalogue['recordings'])!=3:raise ValueError('no admitted recording bundle')
    if output.exists() or Path(str(output)+'.zip').exists():raise FileExistsError('choose a new package path')
    for record in catalogue['recordings']:
        if hashlib.sha256((source/record['path']).read_bytes()).hexdigest()!=record['sha256']:raise ValueError('recording hash differs')
    report=ROOT/'docs/phase-11/phase-memory-evidence/report.json'
    if hashlib.sha256(report.read_bytes()).hexdigest()!=catalogue['report_sha256']:raise ValueError('report identity differs')
    output.mkdir(parents=True)
    def copy(name):
        destination=output/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,destination)
    shutil.copytree(ROOT/'js',output/'js');shutil.copytree(ROOT/'assets/vendor',output/'assets/vendor')
    config=json.loads((ROOT/'data/experience.json').read_text())
    paths={config['assets'][k] for k in ('ore','floor','loader')}
    paths.add(config['visuals']['authored']['reference_loader']['path']);paths.add('assets/fonts/space-grotesk-latin.woff2')
    paths.update(('assets/README.md','assets/textures/README.md','assets/authored/README.md'))
    for name in sorted(paths):copy(name)
    visual={'source':'Visual asset selection for the recorded technical preview',
        'assets':{k:config['assets'][k] for k in ('ore','floor','loader')},
        'visuals':{'authored':{'reference_loader':config['visuals']['authored']['reference_loader']}}}
    (output/'data').mkdir();(output/'data/experience.json').write_text(json.dumps(visual,indent=2)+'\n')
    for name in ('index.html','viewer.css','viewer.js','catalogue.json',*(r['path'] for r in catalogue['recordings'])):copy('docs/phase-11/phase-memory-demo/'+name)
    html=output/'docs/phase-11/phase-memory-demo/index.html';text=html.read_text().replace('href="docs/phase-11/narrative-study/">Narrative study','href="docs/phase-11/phase-memory-study.md">Study notes');html.write_text(text)
    copy('docs/phase-11/phase-memory-study.md')
    for name in ('report.json','learning-curves.svg','independent-replay.json'):
        path=ROOT/'docs/phase-11/phase-memory-evidence'/name
        if path.exists():copy('docs/phase-11/phase-memory-evidence/'+name)
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=docs/phase-11/phase-memory-demo/"><title>Kessel recorded evaluation</title><a href="docs/phase-11/phase-memory-demo/">Open the recorded evaluation</a>\n')
    (output/'README.txt').write_text('Serve this folder with python3 -m http.server 8000, then open http://127.0.0.1:8000/.\nFinite measured synthetic recordings. Neural continuous actions use disclosed rule-based phase memory. No live browser inference or machine control. Training tools and weights remain in the full repository.\n')
    manifest={'kind':'kessel-recorded-static-preview-v1','source_mode':'recorded_synthetic','method':catalogue['method'],
        'catalogue_sha256':hashlib.sha256((source/'catalogue.json').read_bytes()).hexdigest(),
        'files':{p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}}
    (output/'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    assert not list(output.rglob('*.pt')) and not list(output.rglob('*.py'))
    archive=shutil.make_archive(str(output),'zip',root_dir=output)
    print('Static recorded preview:',output,'ZIP:',archive,'files:',len(manifest['files']))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);package(p.parse_args().output)
