import isan.tagging.eval as tagging_eval
import random
import numpy
import gzip
import pickle
import sys
import json
from isan.utls.indexer import Indexer
from isan.tagging.cb_subsymbolic import Mapper as Mapper
from isan.tagging.cb_subsymbolic import PCA as PCA
from isan.tagging.cb_symbolic import Character
from isan.tagging.cb_symbolic import Tag_Bigram



"""
基于字标注的中文分词词性标注
"""

class Codec :
    with_gold=False
    output_json=False
    dep_format=False
    
    def decode(self,line):
        if not line: return None

        if self.dep_format :
            items=line.split()
            items=[item.split('_') for item in items]
            raw=''.join(item[0] for item in items)
            if any(len(item[0])==0 for item in items) : return None
            seq=[(item[0],item[1]) for item in items]
            self.gold_dep=items
        else :
            seq=[word for word in line.split()]
            seq=[(word.partition('_')) for word in seq]
            seq=[(w,t) for w,_,t in seq]
            raw=''.join(x[0] for x in seq)

        if self.with_gold :
            self.gold=seq

        return {'raw':raw, 'y': seq, 'Y_a': 'y'}

    def encode(self,y):
        return ' '.join(x[0]+ '_'+x[1] if x[1] else '' for x in y)

    def check_connections(self,rst):
        keys=set(rst.keys())
        begins={}
        ends={}
        for k in keys :
            b,e,t=k
            if b not in begins : begins[b]=set()
            begins[b].add(k)
            if e not in ends : ends[e]=set()
            ends[e].add(k)

        check=list(sorted(begins.keys()|set(ends.keys())))
        begins[check[-1]]={'$'}
        ends[0]={'^'}
        while check :
            ind=check.pop()
            left=(ind in begins and len(begins[ind])>0)
            right=(ind in ends and len(ends[ind])>0)
            if left and right :
                continue
            if not left and not right :
                continue
            if ind in begins :
                for k in begins[ind] :
                    ends[k[1]].remove(k)
                    keys.remove(k)
                    check.append(k[1])
                begins[ind]={}
            if ind in ends :
                for k in ends[ind] :
                    begins[k[0]].remove(k)
                    keys.remove(k)
                    check.append(k[0])
                ends[ind]={}

        return {k:v for k,v in rst.items() 
                if k in keys
                }



    def encode_candidates(self,x):
        raw,candidates=x
        rst={}
        for b,e,t,m in candidates :
            if m <-1 : 
                print(raw,file=sys.stderr)
                print(b,e,raw[b:e],t,m,file=sys.stderr)
            key=(b,e,t)
            if key in rst and rst[key][1]<m : continue
            rst[(b,e,t)]=[0,m if m>0 else 0]
        offset=0

        self.raw=raw
        rst=self.check_connections(rst)

        for w,t in self.gold :
            key=(offset,offset+len(w),t)
            offset+=len(w)
            if key in rst : 
                rst[key][0]=1
            else : 
                rst[key]=[1,-9]

        cands=[]
        for k,v in rst.items():
            cands.append([v[0],k[0],k[1],raw[k[0]:k[1]]
                    ,k[2],round(v[1]*10000)/10000,
                ])
        cands=sorted(cands,key=lambda x: (x[1],x[2]))

        if not self.output_json :
            return(' '.join(("%d,%d,%d,%s,%s,%0.4f"%(
                l,b,e,w,t,m))
                for l,b,e,w,t,m in cands))
        else :
            if self.dep_format :
                arcs={}
                offset=0
                for i in range(len(self.gold_dep)):
                    word,tag,ind,label=self.gold_dep[i]
                    ind=int(ind)
                    self.gold_dep[i]=((offset,offset+len(word),word,tag),ind,label)
                    offset+=len(word)
                for i in range(len(self.gold_dep)):
                    k,ind,label=self.gold_dep[i]
                    if ind != -1 :
                        arcs[k]=(self.gold_dep[ind][0],label)
                    else :
                        arcs[k]=(None,label)

                cands=[((b,e,w,t),m,arcs.get((b,e,w,t),None))for l,b,e,w,t,m in cands]
                a=sum(1 for x in cands if x[2]!=None)
                assert(a==len(arcs))
                return json.dumps(cands, ensure_ascii=False)
            else :
                return json.dumps(cands, ensure_ascii=False)

class Task  :
    name="sub-symbolic Character-based CWS"

    codec=Codec()
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

    def gen_candidates(self,margins,threshold):
        score,margins=margins
        candidates=[]
        cands=[]
        for i,ml in enumerate(margins):
            cands.append([])
            for j,it in enumerate(ml):
                a,e,b=it
                if(a+b+e+threshold < score ) : continue
                if a+b+e> score+1 :
                    print('xxxxxxxxxxxxxx',file=sys.stderr)
                cands[-1].append((j,a,e,b))

        for i,column in enumerate(cands):
            for a_tid,a_alpha,a_e,a_beta in column :
                a_t=self.indexer[a_tid]
                if a_t[0]=='S' or (i==0 and a_t[0]=='E') or (i+1==len(cands) and a_t[0]=='B'):
                    candidates.append((i,i+1,a_t[2:],score-(a_alpha+a_beta+a_e)))
                elif a_t[0]=='B' or (i==0 and a_t[0]=='M'):
                    value=a_alpha+a_e
                    tag=a_t[2:]
                    last_tid=a_tid
                    next_value=value
                    next_tid=last_tid
                    for j in range(i+1,len(margins)):
                        flag=False
                        value=next_value
                        last_tid=next_tid
                        for b_tid,b_alpha,b_e,b_beta in cands[j]:
                            b_t=self.indexer[b_tid]
                            if b_t[2:]!=tag : continue
                            if b_t[0]=='E' or (j+1==len(cands) and b_t[0]=='M'):
                                s=value+b_e+b_beta+self.trans[last_tid][b_tid]
                                if s+threshold >= score :
                                    if score-s <-1 :
                                        print(i,j,file=sys.stderr)
                                        print(self.indexer[last_tid],b_t,file=sys.stderr)
                                        print(value,b_e,b_beta,self.trans[last_tid][b_tid],file=sys.stderr)
                                    candidates.append((i,j+1,tag,score-s))
                            if b_t[0]=='M' :
                                next_value=value+b_e+self.trans[last_tid][b_tid]
                                next_tid=b_tid
                                flag=True
                        if flag==False : break

        return self.raw,candidates

    def check(self,std_moves,rst_moves):
        return std_moves[0][-1]==rst_moves[0][-1]

    def remove_oracle(self):
        self.oracle=None

    def __init__(self,model=None,paras=None,cmd_args='',**others):
        class Args :
            pass


        self.indexer=Indexer() # index of tags

        self.logger=others.get('logger',None)

        self.corrupt_x=0
        self.paras=paras
        self.feature_class={
                'ae': lambda x,args={} : Mapper(self.ts,x,args) ,
                'pca': lambda x,args={} : PCA(self.ts,x,args),
                'base': lambda x : Character(self.ts,self.paras,x),
                'trans' : lambda x : Tag_Bigram(self.ts,self.paras,x),
                }

        self.feature_models={}

        args=Args()
        args.eta=0.001
        args.use_pca=False
        args.use_ae=False
        if hasattr(cmd_args,'task_seg'):
            for k,v in cmd_args.task_seg.items():
                setattr(args,k,v)
        
        dargs=vars(args)
        self.codec.dep_format=('dep_format' in dargs)
        if model==None :
            for train in cmd_args.train :
                for line in open(train) :
                    x=self.codec.decode(line)
                    if x is None : continue
                    self.set_oracle(x['raw'],x['y'])[0][-1]


            self.corrupt_x=dargs.get('noise_rate',0)
            self.ts=len(self.indexer)

            self.trans=numpy.zeros((self.ts,self.ts))

            self.feature_models['base']=self.feature_class['base'](None)
            self.feature_models['trans']=self.feature_class['trans'](None)

            if self.logger :
                self.logger.debug('eta: %f'%args.eta)
            self.eta=args.eta

            if args.use_pca :
                self.feature_models['pca']=self.feature_class['pca'](None,args=args.use_pca)
            if args.use_ae :
                self.feature_models['ae']=self.feature_class['ae'](None,args=args.use_ae)
        else :
            self.codec.with_gold=('with_gold' in dargs)
            self.codec.output_json=('output_json' in dargs)
            self.codec.dep_format=('dep_format' in dargs)

            self.oracle=None
            self.indexer,self.ts,self.trans,features=model
            for k,v in features.items():
                self.feature_models[k]=self.feature_class[k](v)

        self.transition_features=[v for v in self.feature_models.values()
                    if hasattr(v,'transition')]
        self.emission_features=[v for v in self.feature_models.values()
                    if hasattr(v,'emission')]

    def add_model(self,features):
        self.indexer,self.ts,trans,others=features
        if len(self.trans)==0 :
            self.trans=trans
            self.trans_s=[[0.0 for y in x]for x in trans]
        else :
            for i,a in enumerate(self.trans):
                for j,b in enumerate(a):
                    if trans[i][j]==0 : continue
                    self.trans[i][j]=(self.trans[i][j]*self.trans_s[i][j]+trans[i][j])/(self.trans_s[i][j]+1)
                    self.trans_s[i][j]+=1
            #self.trans_s+=1
        for k,v in others.items() :
            self.feature_models[k].add_model(v)

    def dump_weights(self):
        others={k:v.dump() for k,v in self.feature_models.items()}
        features=[self.indexer,self.ts,self.trans,others]
        return features

    def cal_delta(self,std_moves,rst_moves) :
        std_tags=std_moves[0][-1]
        rst_tags=rst_moves[0][-1]

        for sm in self.feature_models.values() : 
            sm.cal_delta(std_tags,rst_tags,self.eta)

    def set_raw(self,raw,Y):
        raw=raw[:]
        if self.oracle and self.corrupt_x :
            raw=''.join(c if random.random()>self.corrupt_x else chr(0)  for c in raw)
        self.raw=raw
        for sm in self.feature_models.values() : sm.set_raw(raw)

    def emission(self,raw):
        emissions = [numpy.zeros(self.ts,dtype=float) for i in range(len(self.raw))]
        for sm in self.emission_features : 
            sm.emission(emissions)
        return [x.tolist() for x in emissions]

    def transition(self,_):
        self.trans*=0
        for sm in self.transition_features : 
            self.trans+=sm.transition()
        return self.trans.tolist()
