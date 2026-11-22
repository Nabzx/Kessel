"""Loopback-only reference simulator and frozen actor, with no machine interface."""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from urllib.parse import urlsplit
import uuid

from kessel_training.policy import configure_cpu
from .runtime import ROOT, FAMILIES, SOURCES, Run


class Session:
    def __init__(self): self.run=None;self.run_id=None;self.lock=threading.Lock()
    def reset(self,body):
        seed=body.get('seed')
        if isinstance(seed,bool) or not isinstance(seed,int) or not 19000<=seed<=19999:
            raise ValueError('interactive seeds are restricted to practice range 19000–19999')
        run=Run(body.get('family'),seed,body.get('source'))
        self.run=run;self.run_id=uuid.uuid4().hex
        return self.response([run.frame()])
    def step(self,body):
        if not self.run or body.get('run_id')!=self.run_id: raise ValueError('stale run; reset or reload')
        if body.get('after')!=self.run.decisions: raise ValueError('stale decision counter; no steps executed')
        count=body.get('steps',1)
        if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=10: raise ValueError('steps must be 1–10')
        frames=[]
        for _ in range(count):
            if self.run.done:break
            frame=self.run.step();frame['last_action']=self.run.records[-1]['action'];frames.append(frame)
        return self.response(frames)
    def response(self,frames):
        return {'run_id':self.run_id,'identity':self.run.identity,'scenario':self.run.scenario,
                'source':self.run.source,'checkpoint_sha256':self.run.checkpoint_sha256,
                'frames':frames,'outcome':self.run.outcome(),
                'mode':'live_synthetic','decision_s':self.run.env.loader.decision_s,
                'control_description':'Conventional reference' if self.run.source=='reference' else 'Neural continuous actions with rule-based phase memory'}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
    def json(self,status,value):
        data=json.dumps(value,separators=(',',':'),allow_nan=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if not self.valid_host():return self.json(403,{'error':'loopback host required'})
        path=urlsplit(self.path).path
        if path=='/api/info':return self.json(200,{'families':FAMILIES,'sources':SOURCES,'seed_min':19000,'seed_max':19999,'mode':'live_synthetic'})
        if path=='/api/export':
            with self.server.session.lock:
                run=self.server.session.run
                if not run:return self.json(409,{'error':'start a run first'})
                return self.json(200,{'identity':run.identity,'scenario':run.scenario,'source':run.source,
                     'checkpoint_sha256':run.checkpoint_sha256,'outcome':run.outcome(),'frames':run.records+[run.frame()],
                     'applied_machine_commands':False})
        if path.startswith('/api/'):return self.json(404,{'error':'unknown endpoint'})
        # Static serving is intentionally limited to viewer dependencies, never training weights or dotfiles.
        if any(part.startswith('.') for part in path.split('/') if part) or not path.startswith(('/docs/phase-11/live-demo/','/docs/phase-11/phase-memory-demo/','/docs/phase-11/narrative-study/','/docs/phase-11/phase-memory-study.md','/index.html','/css/','/assets/','/js/','/data/')):
            return self.json(404,{'error':'open /docs/phase-11/live-demo/'})
        if '..' in self.path or '%2e' in self.path.lower() or not path.endswith(('/','.html','.js','.css','.json','.glb','.jpg','.png','.webp','.woff2','.txt','.md')):
            return self.json(404,{'error':'unsupported asset'})
                super().do_GET()
    def list_directory(self,path):
        return self.json(404,{'error':'directory listing disabled'})
    def do_HEAD(self):
        return self.json(405,{'error':'use GET for supported assets'})
    def do_POST(self):
        origin=self.headers.get('Origin')
        if not self.valid_host() or origin is not None and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
            return self.json(403,{'error':'same-origin loopback request required'})
        if self.headers.get('Content-Type')!='application/json':return self.json(415,{'error':'application/json required'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=2048:raise ValueError('request body must be 1–2048 bytes')
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict):raise ValueError('JSON object required')
            with self.server.session.lock:
                if self.path=='/api/reset':result=self.server.session.reset(body)
                elif self.path=='/api/step':result=self.server.session.step(body)
                else:return self.json(404,{'error':'unknown endpoint'})
            self.json(200,result)
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as error:self.json(400,{'error':str(error)})


def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8090);a=p.parse_args()
    configure_cpu(7);server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler);server.session=Session()
    print(f'Live synthetic demo: http://127.0.0.1:{a.port}/docs/phase-11/live-demo/',flush=True)
    server.serve_forever()

if __name__=='__main__':main()
