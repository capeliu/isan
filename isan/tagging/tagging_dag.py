#!/usr/bin/python3
from struct import Struct
import json

import time
import math
import sys
xx='s'
class Path_Finding :
    do_not_set_raw_for_searcher=None
    """
    finding path in a DAG
    """
    class codec :
        @staticmethod
        def decode(line):
            """
            编码、解码
            从一行文本中，得到输入（raw）和输出（y）
            """

            if not line: return []
            log2=math.log(2)
            ldep=json.loads(line)
            raw=[]
            y=[]
            #print(ldep)
            for k,v in ldep :
                if 'tag-weight' in v or v.get('is_test',True)==False :
                    weight=v.get('tag-weight',None)
                    weight=[math.floor(math.log(int(weight)+1)/log2)] if weight else []
                    raw.append([(k[0],k[2],k[3]),weight])
                if 'dep' in v :
                    y.append((k[0],k[2],k[3]))
            #print(raw)
            #print(y)
            #input()
            return {'raw':raw,
                    'y':y,
                    'Y_a' : None,
                    'Y_b' : None,
                    }
            seq=[word.split('_') for word in line.split()]


            raw=[]
            y=[]
            for offset,word,tag,weight,oracle in seq :
                offset=int(offset)
                weight=[math.floor(math.log(int(weight)+1)/log2)] if weight else []
                item=[(offset,word,tag),weight]
                if oracle!='-1': raw.append(item)
                if oracle!='0' : y.append(item[0])

            global xx
            xx=[a for a,b in raw if b and b[0]==0]
            print(raw)
            print(y)
            input()

            return {'raw':raw,
                    'y':y,
                    'Y_a' : None,
                    'Y_b' : None,
                    }
        @staticmethod
        def encode(y):
            return ' '.join(y)
    def update_moves(self,std_moves,rst_moves) :
        for move in rst_moves :
            yield move, -1
        for move in std_moves :
            if self.stop_step>=0 and move[0]>=self.stop_step : return
            yield move, 1
    def set_raw(self,raw,Y):
        self.raw=raw
        self.begins={}
        self.ends={}
        max_ind=0
        for ind,item in enumerate(raw) :
            b,word,tag=item[0]
            e=b+len(word)
            if max_ind<e : max_ind=e
            if b not in self.begins : self.begins[b]=[]
            if e not in self.ends : self.ends[e]=[]
            self.begins[b].append(ind)
            self.ends[e].append(ind)

    def moves_to_result(self,moves,raw):
        if not moves : return []
        actions=list(zip(*moves))[2]
        states=list(zip(*moves))[1]
        states=[Struct.unpack(self.stat_fmt,x) for x in states]
        inds=[x[1] for x in states[:]]
        result=[self.raw[ind][0] for ind in inds[1:]]

        return result
    stat_fmt=Struct('hh')
    def get_init_states(self):
        init_states=[Struct.pack(self.stat_fmt,*(-1,-1))]
        return init_states
        pass
    def shift(self,ind,state):
        state=Struct.unpack(self.stat_fmt,state)
        ind1,ind2=state
        #print(*(self.raw[i][0] if i>=0 else (None,None,None) for i in state))
        if ind not in self.begins : 
            return [(-1,-1,Struct.pack(self.stat_fmt,ind2,-1))]
        nexts=[]
        for ind3 in self.begins[ind] :
            n=(ind3,ind+len(self.raw[ind3][0][1]),Struct.pack(self.stat_fmt,ind2,ind3))
            #print(n)
            nexts.append(n)
        return nexts
        pass
    reduce=None
    def check(self,std_moves,rst_moves):
        return all(
                std_move[1]==rst_move[1]
                for std_move,rst_move in zip(std_moves,rst_moves)
                )
    def gen_features(self,state,actions):
        fvs=[]
        state=Struct.unpack(self.stat_fmt,state)
        for action in actions :
            ind1,ind2=state
            ind3=action
            raw=self.raw
            if ind1==-1 :
                w1,t1=b'~',b'~'
                len1=b'0'
                f1,b1=b'~',b'~'
                m1=b''
            else :
                r=raw[ind1]
                w1,t1=r[0][1].encode(),r[0][2].encode()
                len1=str(len(r[0][1])).encode()
                f1,b1=r[0][1][0].encode(),r[0][1][-1].encode()
                m1=b'' if not r[1] else str(r[1][0]).encode()
            if ind2==-1 :
                w2,t2=b'~',b'~'
                len2=b'0'
                f2,b2=b'~',b'~'
                m2=b''
            else :
                r=raw[ind2]
                w2,t2=r[0][1].encode(),r[0][2].encode()
                len2=str(len(r[0][1])).encode()
                f2,b2=r[0][1][0].encode(),r[0][1][-1].encode()
                m2=b'' if not r[1] else str(r[1][0]).encode()
            if ind3==-1 :
                w3,t3=b'~',b'~'
                len3=b'0'
                f3,b3=b'~',b'~'
                m3=b''
            else :
                r=raw[ind3]
                w3,t3=r[0][1].encode(),r[0][2].encode()
                len3=str(len(r[0][1])).encode()
                f3,b3=r[0][1][0].encode(),r[0][1][-1].encode()
                m3=b'' if not r[1] else str(r[1][0]).encode()

            fv=[
                    b'm3~'+m3,
                    b'm3m2~'+m3+b'~'+m2,
                    b'w3~'+w3,
                    b't3~'+t3,
                    b'w3t3~'+w3+t3,
                    b'l3~'+len3,
                    b'l3t3~'+len3+t3,
                    b'l3w2~'+len3+w2,
                    b'l3t2~'+len3+t2,
                    b'w3w2~'+w3+b"-"+w2,
                    b'w3t3w2~'+w3+t3+w2,
                    b'w3w2t2~'+w3+t2+w2,
                    b't3w2~'+t3+w2,
                    b'w3t2~'+w3+t2,
                    b'w3t3~'+w3+t3,
                    b't3t2~'+t3+t2,
                    b't3t1~'+t3+t1,
                    b't3t2t1~'+t3+t2+t1,
                    
                    ]
            fvs.append(fv)
            continue
            fv=[b'a0~'+str(x).encode() for x in raw3[1]]
            #fv+=[b'a0w3~'+str(x).encode()+b'~'+raw3[0][1].encode() for x in raw3[1]]
            #fv+=[b'a0t3~'+str(x).encode()+b'~'+raw3[0][2].encode() for x in raw3[1]]
            fv+=[
                    b'3w~'+raw3[0][1].encode(),
                    b'3t~'+raw3[0][2].encode(),
                    b'l3~'+str(len(raw3[0][1])).encode(),
                    b't3t2~'+raw3[0][2].encode()+b'~'+raw2[0][2].encode(),
                    b'w3w2~'+raw3[0][1].encode()+b'~'+raw2[0][1].encode(),
                    b'w3t2~'+raw3[0][1].encode()+b'~'+raw2[0][2].encode(),
                    b't3w2~'+raw3[0][2].encode()+b'~'+raw2[0][1].encode(),
                    b't3t2t1~'+raw3[0][2].encode()+b'~'+raw2[0][2].encode()+b'~'+raw1[0][2].encode(),
                    ]
            return fv
        return fvs



    def set_oracle(self,raw,y):
        words=list(reversed(y[:]))
        inds=[-1,-1]
        offset=0
        offsets=[offset]
        for ind,item in enumerate(raw) :
            if not words : break
            if item[0]==words[-1] :
                word=words.pop()
                inds.append(ind)
                offset+=len(word[1])
                offsets.append(offset)
        inds.append(-1)
                
        self.oracle={}
        for i in range(len(offsets)) :
            self.oracle[offsets[i]]=Struct.pack(self.stat_fmt,*inds[i:i+2])

        states=[inds[i:i+3] for i in range(len(inds)-2)]
        moves=[]
        for a,b,c in states:
            if b>=0 :
                step=raw[b][0][0]+len(raw[b][0][1])
            else :
                step=0
            state=Struct.pack(self.stat_fmt,a,b)
            action=c
            moves.append((step,state,action))
        return moves
    def remove_oracle(self):
        self.oracle=None
        pass
    def early_stop(self,step,next_states,moves):
        if not moves : return False
        last_steps,last_states,actions=zip(*moves)
        if not hasattr(self,'oracle') or self.oracle==None : return False
        self.stop_step=-1
        if step in self.oracle :
            if not (self.oracle[step]in next_states) :
                self.stop_step=step
                return True
        return False

    class Eval :
        def __init__(self):
            """
            初始化
            """
            self.otime=time.time()
            self.std,self.rst=0,0
            self.cor,self.seg_cor=0,0
            self.characters=0
            self.overlaps=0
            self.with_tags=True
        def __call__(self,std,rst):
            global xx
            std=set(std)
            rst=set(rst)
            self.std+=len(std)
            self.rst+=len(rst)
            self.cor+=len(std&rst)
            self.characters+=sum(len(w)for _,w,_ in std)
            self.seg_cor+=len({(b,e) for b,e,t in std}&{(b,e) for b,e,t in rst})
        def print_result(self):
            """
            打印结果
            """
            time_used=time.time()-self.otime
            speed=self.characters/time_used

            cor=self.cor
            p=cor/self.rst if self.rst else 0
            r=cor/self.std if self.std else 0
            f=2*p*r/(r+p) if (r+p) else 0

            if self.with_tags :
                seg_cor=self.seg_cor
                p=seg_cor/self.rst if self.rst else 0
                r=seg_cor/self.std if self.std else 0
                seg_f=2*p*r/(r+p) if (r+p) else 0

            if self.with_tags :
                line=("标准: %d 输出: %d seg正确: %d 正确: %d seg_f1: \033[32;01m%.4f\033[1;m tag_f1: \033[32;01m%.4f\033[1;m ol: %d 时间: %.4f (%.0f字/秒)"
                            %(self.std,self.rst,self.seg_cor,self.cor,seg_f,f,self.overlaps,time_used,speed))
            else :
                line=("标准: %d 输出: %d 正确: %d f1: \033[32;01m%.4f\033[1;m ol: %d 时间: %.4f (%.0f字/秒)"
                            %(self.std,self.rst,self.cor,f,self.overlaps,time_used,speed))
            print(line,file=sys.stderr)
            sys.stderr.flush()
            pass
        
if __name__ == '__main__':
    pf=Path_Finding()
    for line in open('/home/zkx/lattice/test.lat') :
        line=line.strip()
        pf.codec.decode(line)

