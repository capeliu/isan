#!/usr/bin/python3
from struct import Struct
import pickle
import json
import time
import math
import sys
from isan.common.lattice import Lattice_Task as Base_Task
from isan.data.lattice import Lattice as Lattice

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
        std=[x[:3] for x in std]
        #print(std)
        #print(rst)

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
                weight=[math.floor(math.log(int(weight)+1)/log2)] if weight!=None else []
                raw.append([(k[0],k[2],k[3]),weight])
            if 'dep' in v :
                #y.append((k[0],k[2],k[3],v['dep'][1],v['dep'][0]))
                y.append((k[0],k[2],k[3]))
        raw,weights=zip(*raw)
        raw=[(it[0],it[0]+len(it[1]),it[1],it[2]) for it in raw]
        raw=Lattice(raw,weights)
        return {'raw':raw,
                'y':y,
                'Y_a' : None,
                'Y_b' : None,
                }
    @staticmethod
    def encode(y):
        return ' '.join(y)

class State :
    init_state=pickle.dumps([(-1,-1)])
    init_stat=pickle.dumps([(-1,-1)])
    def __init__(self,bt,lattice):
        words,*_=pickle.loads(bt)
        self.w1,self.w0=words
    def shift(self,wid):
        return pickle.dumps([(self.w0,wid)])
    @staticmethod
    def load(bt):
        return pickle.loads(bt)

class Path_Finding (Base_Task):
    """
    finding path in a DAG
    """
    codec=codec
    State=State

    def update_moves(self,std_moves,rst_moves) :
        for move in rst_moves :
            if self.stop_step>=0 and move[0]>=self.stop_step : return
            yield move, -1
        for move in std_moves :
            if self.stop_step>=0 and move[0]>=self.stop_step : return
            yield move, 1


    def moves_to_result(self,moves,_):
        if not moves : return []
        actions=list(zip(*moves))[2]
        states=list(zip(*moves))[1]
        states=[self.State.load(x)[0] for x in states]
        inds=[x[1] for x in states[:]]
        result=[
                (self.lattice.items[ind][0],
                    self.lattice.items[ind][2],
                    self.lattice.items[ind][3])
                for ind in inds[1:]]
        return result


    init_state=State.init_state#


    def shift_step(self,step,ind):
        return step+len(self.lattice.items[ind][2])

    def shift(self,step,state):
        state=self.State(state,self.lattice)
        if step not in self.lattice.begins : # 如果没有后续节点，标志为结束
            return [(-1,-1,state.shift(-1))]
        nexts=[]
        for ind3 in self.lattice.begins[step] :
            next_step=self.shift_step(step,ind3)
            print(next_step)
            input()
            n=(
                    ind3, #shift action id
                    next_step,
                    state.shift(ind3)
                )
            nexts.append(n)
        return nexts
    reduce=None


    def actions_to_moves(self,actions):

        state=self.init_state
        step=0
        moves=[]
        for action in actions :
            moves.append((step,state,action))
            for a,n,s in self.shift(step,state) :
                if a == action :
                    step=n
                    state=s
        return moves

        


    def set_oracle(self,raw,y):
        self.set_raw(raw,None)
        words=list(reversed(y[:]))
        inds=[-1,-1]
        offset=0
        offsets=[offset]

        for ind,item in enumerate(self.lattice.items) :
            if not words : break
            if (item[0]==words[-1][0] 
                    and item[2]==words[-1][1]
                    and item[3]==words[-1][2]
                    ) :
                word=words.pop()
                inds.append(ind)
                offset+=len(word[1])
                offsets.append(offset)
        inds.append(-1)
                

        actions=inds[2:]
        moves2=self.actions_to_moves(actions)

        self.oracle={}
        for step,state,action in moves2 :
            self.oracle[step]=self.State.load(state)
        
        #print(self.lattice)
        #for move in moves2:
        #    print(move[0],self.State.load(move[1]),move[2])
        #print(moves2)
        #input()

        return moves2
    def remove_oracle(self):
        self.oracle=None
        pass
    def early_stop(self,step,next_states,moves):
        if not moves : return False
        last_steps,last_states,actions=zip(*moves)
        if not hasattr(self,'oracle') or self.oracle==None : return False
        self.stop_step=-1
        if step in self.oracle :
            next_states=[self.State.load(x) for x in next_states]
            if not (self.oracle[step]in next_states) :
                self.stop_step=step
                return True
        return False

    def set_raw(self,raw,Y):
        self.lattice=raw

    def gen_features(self,state,actions):
        fvs=[]
        state=self.State(state,self.lattice)
        ind1,ind2=state.w1,state.w0
        for action in actions :
            ind3=action
            if ind1==-1 :
                w1,t1=b'~',b'~'
                len1=b'0'
                f1,b1=b'~',b'~'
                m1=b''
            else :
                r=[(self.lattice.items[ind1][0],
                        self.lattice.items[ind1][2],
                        self.lattice.items[ind1][3]),
                        self.lattice.weights[ind1]]#raw[ind1]
                w1,t1=r[0][1].encode(),str(r[0][2]).encode()
                len1=str(len(r[0][1])).encode()
                f1,b1=r[0][1][0].encode(),r[0][1][-1].encode()
                m1=b'' if not r[1] else str(r[1][0]).encode()
            if ind2==-1 :
                w2,t2=b'~',b'~'
                len2=b'0'
                f2,b2=b'~',b'~'
                m2=b''
            else :
                r=[(self.lattice.items[ind2][0],
                        self.lattice.items[ind2][2],
                        self.lattice.items[ind2][3]),
                        self.lattice.weights[ind2]]#raw[ind1]
                w2,t2=r[0][1].encode(),str(r[0][2]).encode()
                len2=str(len(r[0][1])).encode()
                f2,b2=r[0][1][0].encode(),r[0][1][-1].encode()
                m2=b'' if not r[1] else str(r[1][0]).encode()
            if ind3==-1 :
                w3,t3=b'~',b'~'
                len3=b'0'
                f3,b3=b'~',b'~'
                m3=b''
            else :
                r=[(self.lattice.items[ind3][0],
                        self.lattice.items[ind3][2],
                        self.lattice.items[ind3][3]),
                        self.lattice.weights[ind3]]#raw[ind1]

                w3,t3=r[0][1].encode(),str(r[0][2]).encode()
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
        return fvs
    Eval=Eval
