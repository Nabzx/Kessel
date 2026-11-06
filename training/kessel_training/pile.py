"""Mass-tracked synthetic height fields; no granular dynamics claim."""

import numpy as np


class PileGrid:
    def __init__(self,num_envs,size=8,cell_m=0.5):
        self.size,self.cell_m = size,cell_m
        self.height = np.zeros((num_envs,size,size),dtype=np.float64)
        self.density = np.full(num_envs,1800.0)
        self.origin = np.zeros((num_envs,2))
        self.initial_mass = np.zeros(num_envs)
        self.cell_x,self.cell_y = np.meshgrid((np.arange(size)+0.5)*cell_m,
                                             (np.arange(size)+0.5)*cell_m,indexing="ij")

    def reset_one(self,index,rng,pile_front=8.0):
        self.density[index] = rng.uniform(1600,2100)
        self.origin[index] = (pile_front,-self.size*self.cell_m/2)
        x,y = np.meshgrid(np.linspace(-1,1,self.size),np.linspace(-1,1,self.size),indexing="ij")
        shape = 0.25+np.exp(-1.7*(x*x+y*y))+rng.uniform(0,0.1,(self.size,self.size))
        mass = rng.uniform(9000,14000)
        self.height[index] = shape * mass/(shape.sum()*self.cell_m**2*self.density[index])
        self.initial_mass[index] = self.mass()[index]

    def mass(self):
        return self.height.sum(axis=(1,2))*self.cell_m**2*self.density

    def sample(self,points):
        points = np.asarray(points,dtype=np.float64)
        if points.shape[0] != len(self.height) or points.shape[-1] != 2 or not np.isfinite(points).all():
            raise ValueError("sample points must be finite batched xy positions")
        extra = (1,)*(points.ndim-2)
        local = points-self.origin.reshape((len(self.height),)+extra+(2,))
        ix = np.floor(local[...,0]/self.cell_m).astype(int)
        iy = np.floor(local[...,1]/self.cell_m).astype(int)
        valid = (ix>=0)&(ix<self.size)&(iy>=0)&(iy<self.size)
        env = np.arange(len(self.height)).reshape((len(self.height),)+extra)
        height = self.height[env,np.clip(ix,0,self.size-1),np.clip(iy,0,self.size-1)]
        return np.where(valid,height,0)

    def extract(self,mouth,forward,bottom,room_kg,fraction):
        if not all(np.isfinite(a).all() for a in (mouth,forward,bottom,room_kg,fraction)):
            raise ValueError("non-finite bucket contact")
        dx = self.origin[:,0,None,None]+self.cell_x-mouth[:,0,None,None]
        dy = self.origin[:,1,None,None]+self.cell_y-mouth[:,1,None,None]
        along = dx*forward[:,0,None,None]+dy*forward[:,1,None,None]
        across = -dx*forward[:,1,None,None]+dy*forward[:,0,None,None]
        inside = (np.abs(along)<=0.6)&(np.abs(across)<=0.75)
        available = np.minimum(np.maximum(self.height-bottom[:,None,None],0),0.7)
        proposed = available*inside*self.cell_m**2*self.density[:,None,None]*np.clip(fraction,0,1)[:,None,None]
        total = proposed.sum(axis=(1,2))
        ratio = np.minimum(1,np.maximum(room_kg,0)/np.maximum(total,1e-12))
        removed = proposed*ratio[:,None,None]
        self.height -= removed/(self.cell_m**2*self.density[:,None,None])
        np.maximum(self.height,0,out=self.height)
        return removed.sum(axis=(1,2)),removed
