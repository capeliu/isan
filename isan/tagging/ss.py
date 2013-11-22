import sys
import json
import gzip
import numpy as np
import pickle
import random

class Word : 
    def close(self):
        if self.use_hidden :
            if 'save' in self.use_hidden :
                fi=open(self.use_hidden['save'],'w')
                print(json.dumps(self.M.tolist()),file=fi)
                print(json.dumps(self.b.tolist()),file=fi)
                fi.close()
                pass
        pass
    def __init__(self,args={},model=None,paras=None):
        self.paras=paras

        print(args)
        self.s={} ## ??
        if model == None :
            words={}
            size=0
            for line in open(args['words']) :
                word,*vs = line.split()
                vs=list(map(float,vs))
                size=len(vs)
                words[word]=np.array(vs)

            
            self.use_hidden=args.get('hidden',None)


            self.words=words
            self.zw=np.zeros(size)
            self.size=size

            self.d=self.paras.add({})

            self.d_hidden=np.zeros(self.size)

            np.random.seed(0)


            self.M=np.random.uniform(-1,1,(self.size,self.size))
            self.b=np.zeros(self.size)
            if self.use_hidden and 'load' in self.use_hidden :
                m,b=open(self.use_hidden['load']).read().splitlines()
                self.M=np.array(json.loads(m))
                self.b=np.array(json.loads(b))

            
            if self.use_hidden and 'update' in self.use_hidden :
                self.M=self.paras.add(self.M)
                self.b=self.paras.add(self.b)
            

            self.s={k:v.copy()for k,v in self.d.items()}

        else :
            if type(model)==list :
                self.use_hidden=False
                self.size,self.d,self.words,self.zw=model
            else :
                for k,v in model.items():
                    setattr(self,k,v)

    def add_model(self,model):
        if type(model)==list :
            d=model[1]
        else :
            d=model['d']
        for k,v in d.items():
            #print(k)
            if k not in self.d :
                self.d[k]=v*0
                self.s[k]=0
            self.d[k]=(self.d[k]*self.s[k]+v)/(self.s[k]+1)
            self.s[k]+=1
        
    def dump_weights(self):
        if not self.use_hidden :
            return [self.size,self.d,self.words,self.zw]
        else :
            d={}
            for k in ['use_hidden','size','d','words','zw','tags','zt','sizet']:
                d[k]=getattr(self,k)
            return d


    def set_raw(self,atoms):
        self.atoms=atoms
        self.sen_word_vecs=[]
        self.sen_hidden_vecs=[]
        for w,*_ in atoms :
            wv=self.words.get(w,self.zw)
            self.sen_word_vecs.append(wv)
            if self.use_hidden :
                hidden=np.dot(self.M,wv)+self.b
                hidden=np.tanh(hidden)
                self.sen_hidden_vecs.append(hidden)
            else :
                self.sen_hidden_vecs.append(wv)

    def __call__(self,ind1,ind2,ind3,delta=0) :
        word2,t2,*_=self.atoms[ind2] # word on the top of the stack
        word3,t3,*_=self.atoms[ind3] # next word
        # get the vector
        w2=self.sen_hidden_vecs[ind2]
        w3=self.sen_hidden_vecs[ind3]

        wv2=self.sen_word_vecs[ind2]
        wv3=self.sen_word_vecs[ind3]

        score=0

        if delta ==0 : # cal the network, not update
            if t3 in self.d :
                score+=np.dot(w3,self.d([t3]))
            if t2!='~' :
                if t2 in self.d :
                    score+=np.dot(w3,self.d(['l'+t2]))
                if t3 in self.d :
                    score+=np.dot(w2,self.d(['r'+t3]))
        else :  # calculate the grad
            self.d.add_delta([t3],w3*delta)
            
            if self.use_hidden and 'update' in self.use_hidden :
                d_hidden=self.d([t3])*(1-w3**2)
                dM=(d_hidden[:,np.newaxis]*wv3)
                self.b.add_delta(d_hidden*delta)
                self.M.add_delta(dM*delta)

            # grad of 
            if t2!='~' :
                self.d.add_delta(['l'+t2],w3*delta)
                if self.use_hidden and 'update' in self.use_hidden :
                    d_hidden=self.d(['l'+t2])*(1-w3**2)
                    dM=(d_hidden[:,np.newaxis]*wv3)
                    self.b.add_delta(d_hidden*delta)
                    self.M.add_delta(dM*delta)

                self.d.add_delta(['r'+t3],w2*delta)
                if self.use_hidden and 'update' in self.use_hidden :
                    d_hidden=self.d(['r'+t3])*(1-w2**2)
                    dM=(d_hidden[:,np.newaxis]*wv2)
                    self.b.add_delta(d_hidden*delta)
                    self.M.add_delta(dM*delta)
        return score
