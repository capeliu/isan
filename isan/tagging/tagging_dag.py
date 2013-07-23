#!/usr/bin/python3
import pickle
import time
import math
import sys
from isan.common.task import Lattice, Base_Task, Early_Stop_Pointwise
from isan.tagging.eval import TaggingEval as Eval
import numpy as np
import gzip

sys.path.append('/home/zkx/exps/tagpath')
from bigram import Bigram as Bigram
from bigram import Trigram as Trigram
from bigram import Word as Word


class codec :
    @staticmethod
    def decode(line):
        """
        编码、解码
        从一行文本中，得到输入（raw）和输出（y）
        """
        if not line: return []
        log2=math.log(2)
        line=list(map(lambda x:x.split(','), line.split()))
        line=[[int(label),int(b),int(e),w,t,int(conf)] for label,b,e,w,t,conf in line]
        items2=[]
        gold=[]
        for l,b,e,w,t,conf in line :
            if conf != -2:
                if conf == -1 :
                    conf = None
                else :
                    #conf = str(math.floor(math.log(conf/500+1)))
                    conf = conf/1000
                items2.append((b,e,(w,t,conf)))
            if l ==1 :
                gold.append((w,t))
        raw=Lattice(items2)
        return {'raw':raw,
                'y':gold, }
    @staticmethod
    def encode(y):
        return ' '.join(y)

class State (list):
    init_state=pickle.dumps((-1,-1))

    decode=pickle.loads
    encode=pickle.dumps

    def __init__(self,lattice,bt=init_state):
        self.extend(pickle.loads(bt))
        self.lattice=lattice

    def shift(self):
        begin=0 if self[1]==-1 else self.lattice[self[1]][1]
        return [[n,pickle.dumps((self[1],n))] 
                for n in self.lattice.begins[begin]]

    def dumps(self):
        return pickle.dumps(tuple(self))

    @staticmethod
    def load(bt):
        return pickle.loads(bt)




class Path_Finding (Early_Stop_Pointwise, Base_Task):
    """
    finding path in a DAG
    """
    name='joint chinese seg&tag from a word-tag lattice'
    codec=codec
    State=State
    Eval=Eval

    def __init__(self,args):

        self.models=[]
        #self.models=[SubSym()]
        #self.models.append(Word())
        #self.models.append(Bigram())
        #self.models.append(Trigram())
        self.ae={}
        for line in open('ae_output.txt'):
            word,*inds=line.split()
            self.ae[word]=inds

    class Action :
        @staticmethod
        def encode(action):
            return action[0]
        @staticmethod
        def decode(action):
            return (action,None)


    # actions

    def result_to_actions(self,result):
        offset=0
        actions=[]
        for g in result :
            nex=[[ind,self.lattice[ind]] for ind in self.lattice.begins[offset]]
            nex=[ind for ind, it in nex if (it[2][0],it[2][1])==g]
            actions.append((nex[0],None))
            offset+=len(g[0])
        return actions

    def actions_to_result(self,actions):
        seq=[self.lattice[action[0]] for action in actions]
        seq=[(it[0],it[1])for _,_,it in seq]
        return seq

    # states

    def _next_ind(self,last_ind,action):
        next_ind=last_ind+len(self.lattice[action][2][0])
        return next_ind if next_ind != self.lattice.length else -1

    def shift(self,last_ind,stat):
        return [(a,self._next_ind(last_ind,a),s) 
                for a,s in self.State(self.lattice,stat).shift()]

    reduce=None



    # feature related

    def set_raw(self,raw,Y):
        self.lattice=raw
        self.atoms=[]
        for ind in range(len(self.lattice)):
            data=self.lattice[ind]
            w,t,m=data[2]
            inds=self.ae.get(w,['^']) if len(w)>1 else ['$']
            self.atoms.append((w,t,m,str(len(w)),inds))
        self.atoms.append(('~','~','','0',[]))

        for model in self.models :
            model.set_raw(self.atoms)


    def gen_features(self,state,actions,delta=0,step=0):
        strm=lambda x:'x' if x=='' else str(math.floor(math.log(x*2+1)))
        fvs=[]
        state=self.State(self.lattice,state,)
        ind1,ind2=state

        w1,t1,m1,len1,ae1=self.atoms[ind1]
        w2,t2,m2,len2,ae2=self.atoms[ind2]

        scores=[]
        for action in actions :
            ind3=action
            w3,t3,m3,len3,ae3=self.atoms[ind3]
            score=0#m3*self.m_d[0] if m3 is not None else 0
            for model in self.models :
                score+=model(ind1,ind2,ind3,delta*0.1,step)
            fv=(
                (['m3~'+strm(m3), ] if m3 is not None else []) +
                    ([ 'm3m2~'+strm(m3)+'~'+strm(m2), ] if m3 is not None  and m2 is not None else [])+
            [
                    'w3~'+w3, 't3~'+t3, 'l3~'+len3, 'w3t3~'+w3+t3, 'l3t3~'+len3+t3,

                    'w3w2~'+w3+"~"+w2, 'w3t2~'+w3+t2, 't3w2~'+t3+w2, 't3t2~'+t3+t2,

                    'l3w2~'+len3+'~'+w2, 'w3l2~'+w3+'~'+len2, 'l3t2~'+len3+'~'+t2, 't3l2~'+t3+'~'+len2,
                    'l3l2~'+len3+'~'+len2,
                    
                    't3t1~'+t3+'~'+t1, 't3t2t1~'+t3+'~'+t2+'~'+t1,
                    'l3l1~'+len3+'~'+len1, 'l3l2l1~'+len3+'~'+len2+'~'+len1,
                    ])
            """
            fv+=['AE1'+t3+ind for ind in ae3]
            fv+=['AE2'+t2+ind for ind in ae3]
            fv+=['AE3'+t3+ind for ind in ae2]"""
            fvs.append(fv)
            scores.append(score)

        if delta==0 :
            return [[self.weights(fv)+s] for fv,s in zip(fvs,scores)]
        else :
            for fv in fvs :
                self.weights.update_weights(fv,delta,step)
            return [[] for fv in fvs]
        return fvs

    """
    def update_moves(self,std_moves,rst_moves,step) :
        max_step=max(x[0] for x in rst_moves)
        std_moves=set(x for x in std_moves if x[0]<=max_step)
        rst_moves=set(rst_moves)
        for m in std_moves-rst_moves :
            self._update(m,1,step)
        for m in rst_moves-std_moves :
            self._update(m,-1,step)
    """
    def update_moves(self,std_moves,rst_moves,step) :
        for s,r in zip(std_moves,rst_moves) :
            if s!= r:
                self._update(s,1,step)
                self._update(r,-1,step)
                break

    def average_weights(self,step):
        self.weights.average_weights(step)
        for model in self.models:
            model.average_weights(step)

    def un_average_weights(self):
        self.weights.un_average_weights()
        for model in self.models:
            model.un_average_weights()
