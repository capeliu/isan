#!/usr/bin/python3
import collections
class Features(dict):
    def __init__(self):
        self.acc=collections.defaultdict(int)
    def update(self,feature,delta=0,step=0):
        self.setdefault(feature,0)
        self[feature]+=delta
        self.acc[feature]+=step*delta
    def __call__(self,fv):
        return sum(map(lambda x:self.get(x,0),fv))
    def updates(self,features,delta=0,step=0):
        for feature in features:
            self.setdefault(feature,0)
            self[feature]+=delta
            self.acc[feature]+=step*delta
    def average(self,step):
        for k in self.acc:
            self[k]=(self[k]-self.acc[k]/step)
            if self[k]==0:del self[k]
        del self.acc

