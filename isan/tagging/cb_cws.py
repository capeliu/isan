import isan.tagging.eval as tagging_eval
import argparse
import random
import shlex
import numpy
import gzip
import pickle
import sys
from isan.utls.indexer import Indexer
from isan.tagging.cb_subsymbolic import Mapper as Mapper
from isan.tagging.cb_subsymbolic import PCA as PCA
from isan.tagging.cb_symbolic import Character as Character

class codec:
    @staticmethod
    def decode(line):
        if not line: return None
        seq=[word for word in line.split()]
        seq=[(word.partition('_')) for word in seq]
        seq=[(w,t) for w,_,t in seq]
        raw=''.join(x[0] for x in seq)
        return {'raw':raw, 'y': seq, 'Y_a': 'y'}
    @staticmethod
    def encode(y):
        return ' '.join(y)

class Task  :
    name="sub-symbolic Character-based CWS"

    codec=codec
    Eval=tagging_eval.TaggingEval

    def get_init_states(self) : return None

    def set_oracle(self,raw,y) :
        tags=[]
        for w,t in y :
            if len(w)==1 : tags.append('S'+'-'+t)
            else :
                tags.append('B'+'-'+t)
                for i in range(len(w)-2): tags.append('M'+'-'+t)
                tags.append('E'+'-'+t)
        self.oracle=[None]
        tags=list(map(self.indexer,tags))
        return [(0,'',tags)]

    def moves_to_result(self,moves,_):
        _,_,tags=moves[0]
        tags=list(map(lambda x:self.indexer[x],tags))
        results=[]
        cache=[]
        for i,t in enumerate(tags):
            cache.append(self.raw[i])
            p,tg=t.split('-')
            if p in ['E','S'] :
                results.append((''.join(cache),tg))
                cache=[]
        if cache : results.append((''.join(cache),tg))
        return results


    def check(self,std_moves,rst_moves):
        return std_moves[0][-1]==rst_moves[0][-1]

    def update_moves(self,std_moves,rst_moves,step) :
        std_tags=std_moves[0][-1]
        rst_tags=rst_moves[0][-1]
        for sm in self.feature_models.values() : 
            sm.update(std_tags,rst_tags,1,step)

        for i in range(len(std_tags)-1):
            self.trans[std_tags[i]][std_tags[i+1]]+=1
            self.trans_s[std_tags[i]][std_tags[i+1]]+=1*step
            self.trans[rst_tags[i]][rst_tags[i+1]]-=1
            self.trans_s[rst_tags[i]][rst_tags[i+1]]-=1*step


    def remove_oracle(self):
        self.oracle=None

    def __init__(self,model=None,args=''):
        self.indexer=Indexer()
        self.corrupt_x=0
        self.feature_class={'ae': lambda : Mapper(self.ts) ,
                'pca': lambda : PCA(self.ts),'base':Character}
        if model==None :
            parser=argparse.ArgumentParser(
                    formatter_class=argparse.RawDescriptionHelpFormatter,
                    description=r"""""",)
            parser.add_argument('--corrupt_x',default=0,type=float, help='',metavar="")
            parser.add_argument('--use_ae',default=False,action='store_true')
            parser.add_argument('--use_pca',default=False,action='store_true',help='')
            parser.add_argument('--pre',default=None,type=str,help='')
            args=parser.parse_args(shlex.split(args))
            self.corrupt_x=args.corrupt_x

            if args.pre :
                for line in open(args.pre) :
                    x=self.codec.decode(line)
                    self.set_oracle(x['raw'],x['y'])[0][-1]
            self.ts=len(self.indexer)
            self.trans=[[0.0 for i in range(self.ts)] for j in range(self.ts)]
            self.trans_s=[[0.0 for i in range(self.ts)] for j in range(self.ts)]
            self.feature_models={'base':Character(self.ts)}

            if args.use_pca :
                self.feature_models['pca']=self.feature_class['pca']()
            if args.use_ae :
                self.feature_models['ae']=self.feature_class['ae']()
        else :
            features=model
            for k,v in features.items():
                self.feature_models[k]=self.feature_class[k](v)

    def add_model(self,features):
        for k,v in features[1].items() :
            self.feature_models[k].add_model(v)

    def dump_weights(self):
        others={k:v.dump() for k,v in self.feature_models.items()}
        features=[others]
        return features

    def average_weights(self,step):
        self.trans_d=list(list(x) for x in self.trans)
        for i in range(self.ts):
            for j in range(self.ts):
                self.trans[i][j]-=self.trans_s[i][j]/step
        for sm in self.feature_models.values() : sm.average_weights(step)

    def un_average_weights(self):
        self.trans=list(list(x) for x in self.trans_d)
        for sm in self.feature_models.values() : sm.un_average_weights()
    
    def set_raw(self,raw,Y):
        self.raw=raw
        for sm in self.feature_models.values() : sm.set_raw(raw)

    def emission(self,raw):
        emissions = [numpy.zeros(self.ts,dtype=float) for i in range(len(self.raw))]
        for sm in self.feature_models.values() : sm.emission(emissions)
        return [x.tolist() for x in emissions]

    def transition(self,_):
        return self.trans
