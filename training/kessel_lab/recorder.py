"""Bounded, fsync-backed observation/proposal records with explicit tail recovery."""
import hashlib
import fcntl
import tempfile
import json
import os
from pathlib import Path
from kessel_training.contracts import canonical_json


def scan(path, *, identity=None):
    rows=[];previous=None;sequences={}
    with Path(path).open('rb') as stream:
        for line in stream:
            if not line.endswith(b'\n'): raise ValueError('incomplete final record; explicit recovery required')
            row=json.loads(line);expected=row.pop('sha256')
            if row['index']!=len(rows) or row['previous_sha256']!=previous:
                raise ValueError('record chain order differs')
            actual=hashlib.sha256(canonical_json(row).encode()).hexdigest()
            if actual!=expected: raise ValueError('record checksum differs')
            if row['stream']!='header':
                last=sequences.get(row['stream'],-1)
                if row['sequence']<=last or row['gap_before']!=row['sequence']-last-1:
                    raise ValueError('stream sequence or gap differs')
                sequences[row['stream']]=row['sequence']
            row['sha256']=expected;rows.append(row);previous=expected
    if not rows or rows[0]['stream']!='header': raise ValueError('missing header')
    if identity is not None and rows[0]['payload']!=identity: raise ValueError('run/checkpoint/calibration identity differs')
    return rows


class Recorder:
    def __init__(self,path,identity,quota_bytes=32*1024*1024,*,recover=False):
        self.path=Path(path);self.quota=quota_bytes
        if isinstance(quota_bytes,bool) or not isinstance(quota_bytes,int) or quota_bytes<512:
            raise ValueError('quota must be at least 512 bytes')
        if self.path.exists() and self.path.stat().st_size>quota_bytes: raise ValueError('existing log exceeds quota')
        if self.path.exists() and not self.path.read_bytes().endswith(b'\n'):
            if not recover: raise ValueError('incomplete tail; explicit recovery required')
            data=self.path.read_bytes();cut=data.rfind(b'\n')+1
            if cut==0: raise ValueError('incomplete header cannot be resumed')
            # Verify the intact prefix before modifying either file.
            with tempfile.NamedTemporaryFile(dir=self.path.parent,delete=False) as check:
                prefix=Path(check.name)
            try:
                with prefix.open('wb') as f: f.write(data[:cut])
                scan(prefix,identity=identity)
            finally:
                if prefix.exists():prefix.unlink()
            tail=self.path.with_suffix(self.path.suffix+'.recovered-tail')
            with tail.open('xb') as f: f.write(data[cut:]);f.flush();os.fsync(f.fileno())
            directory=os.open(self.path.parent,os.O_RDONLY)
            try:os.fsync(directory)
            finally:os.close(directory)
            with self.path.open('r+b') as f:f.truncate(cut);f.flush();os.fsync(f.fileno())
        if self.path.exists():
            self.rows=scan(self.path,identity=identity);self.expected_size=self.path.stat().st_size
        else:
            self.path.touch(exist_ok=False);self.rows=[];self.expected_size=0
            self._append('header',0,identity)
            directory=os.open(self.path.parent,os.O_RDONLY)
            try:os.fsync(directory)
            finally:os.close(directory)

    def append(self,stream,sequence,payload):
        if stream not in ('observation','proposal'): raise ValueError('only observation and shadow-proposal streams are supported')
        if isinstance(sequence,bool) or not isinstance(sequence,int) or sequence<0: raise ValueError('invalid sequence')
        self._append(stream,sequence,payload)

    def _append(self,stream,sequence,payload):
        previous=next((r['sequence'] for r in reversed(self.rows) if r['stream']==stream),-1)
        if sequence<=previous: raise ValueError('duplicate or decreasing stream sequence')
        row={'index':len(self.rows),'previous_sha256':self.rows[-1]['sha256'] if self.rows else None,
             'stream':stream,'sequence':sequence,'gap_before':sequence-previous-1,'payload':payload}
        row['sha256']=hashlib.sha256(canonical_json(row).encode()).hexdigest()
        data=(canonical_json(row)+'\n').encode()
        with self.path.open('ab') as f:
            fcntl.flock(f.fileno(),fcntl.LOCK_EX)
            if os.fstat(f.fileno()).st_size!=self.expected_size:raise ValueError('log changed through another writer; reopen before appending')
            if self.expected_size+len(data)>self.quota:raise BufferError('quota exhausted; unexported records preserved')
            f.write(data);f.flush();os.fsync(f.fileno());self.expected_size+=len(data)
        self.rows.append(row)
