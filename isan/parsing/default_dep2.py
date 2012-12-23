import pickle
import json
#import marshal as pickle
import isan.parsing.eval as eval
from isan.data.lattice import Lattice as Lattice
from isan.common.lattice import Lattice_Task as Base_Task


class codec:
    class Json_Lattice_Data :
        def __init__(self,line):
            self.lattice=json.loads(line)
            self.lattice=[[k,v] for k,v in self.lattice if 'dep' in v]
        def make_raw(self):
            lat=self.lattice
            raw=[]
            for i in range(len(lat)):
                k,v =lat[i]
                k=tuple(k)
                lat[i][0]=k
                #if not ('is_test' in v and v['is_test']) :
                if True:
                    raw.append([k,v.get('tag-weight',None)])
                if 'dep' in v and v['dep'][1]!=None :
                    v['dep'][1]=tuple(v['dep'][1])
            l,w=zip(*raw)
            lattice=Lattice(l,w)
            return lattice

        def make_gold(self):
            lat=self.lattice
            gold=[]
            for k,v in lat :
                if 'tag-weight' in v : del v['tag-weight']
                if not v : v=None
                else :
                    v=[v['dep'][1]]
                gold.append([k,v])
            return gold
    @staticmethod
    def encode(raw,result):
        return ' '.join(['_'.join([item[0],item[1],str(head)]) for item,head in zip(raw,result)])

    @staticmethod
    def decode(line):
        data=codec.Json_Lattice_Data(line)
        lattice=data.make_raw()
        lat=data.make_gold()
        #raw=[(w,t)for b,e,w,t in lattice.items]
        raw=lattice
        inds={}
        for i,it in enumerate(lat):
            inds[it[0]]=i
        lat=[tuple([word[2],word[3]]+([inds[head[0]],'DEP'] if head[0] else [-1,'ROOT']))
                for word,head in lat]
        return {'raw':raw,'y':lat}


    @staticmethod
    def to_raw(line):
        return [(w,t)for w,t,*_ in line]

class Action :
    _shift_offset=200
    shift_action=ord('s')
    left_reduce=ord('l')
    right_reduce=ord('r')

class State(Action) :
    init_stat=pickle.dumps((0,(0,0),(None,None,None)))
    def __init__(self,bt,lattice):
        self.lattice=lattice
        state=pickle.loads(bt)
        self.ind,self.wspan,self.stack_top=state
        self.stop_step=2*len(self.lattice.items)-1
        pass


    @staticmethod
    def load(bt):
        return pickle.loads(bt)

class Dep (Base_Task):
    name="依存句法分析"
    Action=Action
    State=State

    
    shift_action=Action.shift_action
    left_reduce=Action.left_reduce
    right_reduce=Action.right_reduce


    Eval=eval.Eval
    codec=codec

    def shift(self,last_ind,stat):
        state=self.State(stat,self.lattice)

        next_ind=last_ind+1 if last_ind+1 <= (2*len(self.lattice.items)-2) else -1
        stat=State.load(stat)
        ind,span,stack_top=stat
        if ind>=len(self.lattice.items): return []
        #wind=state.ind
        #print(wind)
        #if wind<len(self.lattice.items) :
        #    span1=self.lattice.items[wind][1]
        #else :
        #    return []
        #shift_inds=self.lattice.begins.get(span1,[])
        #print(shift_inds,ind)
        #input()
        #rtn=[]
        #for shift_ind in shift_inds:
            
            #rtn+=state.shift(shift_ind)
        #return rtn

        rtn= [
                (self.shift_action,next_ind,
                    pickle.dumps(
                (ind+1,
                (ind,ind+1),
                #(self.lattice.items[ind][0],self.lattice.items[ind][1]),
                ((self.lattice.items[ind][2],self.lattice.items[ind][3],None,None),
                        stack_top[0],
                        stack_top[1][1] if stack_top[1] else None)
                )))
                ]

        return rtn

    def reduce(self,last_ind,stat,pred_inds,predictors):
        rtn=[]
        i=0
        for ind,predictor in zip(pred_inds, predictors) :
            s=self.reduce_one(last_ind,stat,ind,predictor,i)
            rtn+=s
            i+=1
        return rtn

    def reduce_one(self,last_ind,stat,pred_inds,predictor,alpha_ind):
        stat=State.load(stat)
        next_ind=last_ind+1 if last_ind+1 <= (2*len(self.lattice.items)-2) else -1

        ind,span,stack_top=stat
        predictor=State.load(predictor)
        _,p_span,_=predictor
        s0,s1,s2=stack_top
        assert(predictor[2][0]==s1)
        if s0==None or s1==None:return []
        rtn= [
             (self.left_reduce,next_ind,pickle.dumps((ind,
                (p_span[0],span[1]),
                ((s1[0],s1[1],s1[2],s0[1]),predictor[2][1],predictor[2][2]))),
                alpha_ind),
             (self.right_reduce,next_ind,pickle.dumps((ind,
                (p_span[0],span[1]),
                ((s0[0],s0[1],s1[1],s0[3]),predictor[2][1],predictor[2][2]))),
                alpha_ind),
             ]
        return rtn
    def set_raw(self,raw,Y):
        """
        对需要处理的句子做必要的预处理（如缓存特征）
        """
        self.lattice=raw
        self.f_raw=[[w.encode()if w else b'',t.encode()if t else b''] 
                for b,e,w,t in self.lattice.items]

    def gen_features(self,span,actions):
        fvs=[]
        fv=self.gen_features_one(span)
        for action in actions:
            action=chr(action).encode()
            fvs.append([action+x for x in fv])
            #print(sorted(fvs[-1]))
        #input()
        return fvs

    def gen_features_one(self,stat):
        stat=State.load(stat)
        ind,_,stack_top=stat
        s0,s1,s2_t=stack_top

        s2_t=b'~' if s2_t is None else s2_t.encode()

        if s0:
            s0_w,s0_t,s0l_t,s0r_t=s0
            s0l_t=b'~' if s0l_t is None else s0l_t.encode()
            s0r_t=b'~' if s0r_t is None else s0r_t.encode()
            s0_w=s0_w.encode()
            s0_t=s0_t.encode()
        else:
            s0_w,s0_t,s0l_t,s0r_t=b'~',b'~',b'~',b'~'

        if s1:
            s1_w,s1_t,s1l_t,s1r_t=s1
            s1l_t=b'~' if s1l_t is None else s1l_t.encode()
            s1r_t=b'~' if s1r_t is None else s1r_t.encode()
            s1_w=s1_w.encode()
            s1_t=s1_t.encode()
        else:
            s1_w,s1_t,s1l_t,s1r_t=b'~',b'~',b'~',b'~'

        q0_w,q0_t=self.f_raw[ind] if ind<len(self.f_raw) else (b'~',b'~')
        q1_t=self.f_raw[ind+1][1] if ind+1<len(self.f_raw) else b'~'
        
        fv=[
                #(1)
                b'0'+s0_w,
                b'1'+s0_t,
                b'2'+s0_w+s0_t,
                b'3'+s1_w,
                b'4'+s1_t,
                b'5'+s1_w+s1_t,
                b'6'+q0_w,
                b'7'+q0_t,
                b'8'+q0_w+q0_t,
                #(2)
                b'9'+s0_w+b":"+s1_w,
                b'0'+s0_t+s1_t,
                b'a'+s0_t+q0_t,
                b'b'+s0_w+s0_t+s1_t,
                b'c'+s0_t+s1_w+s1_t,
                b'd'+s0_w+s1_t+s1_w,
                b'e'+s0_w+s0_t+s1_w,
                b'f'+s0_w+s0_t+s1_w+s1_t,
                #(3)
                b'g'+s0_t+q0_t+q1_t,
                b'h'+s0_t+s1_t+q0_t,
                b'i'+s0_w+q0_t+q1_t,
                b'j'+s0_w+s1_t+q0_t,
                #(4)
                b'k'+s0_t+s1_t+s1l_t,
                b'l'+s0_t+s1_t+s1r_t,
                b'm'+s0_t+s1_t+s0l_t,
                b'n'+s0_t+s1_t+s0r_t,
                b'o'+s0_w+s1_t+s0l_t,
                b'p'+s0_w+s1_t+s0r_t,
                #(5)
                b'q'+s0_t+s1_t+s2_t,
                ]
        #print(*[x.decode() for x in fv])
        #input()
        return fv
    def moves_to_result(self,moves,_):
        #actions=moves[1]
        actions=list(zip(*moves))[2]
        ind=0
        stack=[]
        arcs=[]
        for a in actions:
            if a==self.shift_action:
                stack.append(ind)
                ind+=1
            elif a==self.left_reduce:
                arcs.append((stack[-1],stack[-2]))
                stack.pop()
            elif a==self.right_reduce:
                arcs.append((stack[-2],stack[-1]))
                stack[-2]=stack[-1]
                stack.pop()
        arcs.append((stack[-1],-1))
        arcs.sort()
        arcs=[x for _,x in arcs]
        return arcs
    def result_to_actions(self,result):
        """
        将依存树转化为shift-reduce的动作序列（与动态规划用的状态空间无关）
        在一对多中选择了一个（没搞清楚相关工作怎么弄的）
        """
        stack=[]
        actions=[]
        result=[ind for _,_,ind,_ in result]
        record=[[ind,head,0] for ind,head in enumerate(result)]# [ind, ind_of_head, 是head的次数]
        for ind,head,_ in record:
            if head!=-1 :
                record[head][2]+=1
        for ind,head in enumerate(result):
            actions.append(self.shift_action)
            stack.append([ind,result[ind],record[ind][2]])
            while len(stack)>=2:
                if stack[-1][2]==0 and stack[-1][1]!=-1 and stack[-1][1]==stack[-2][0]:
                    actions.append(self.left_reduce)
                    stack.pop()
                    stack[-1][2]-=1
                elif stack[-2][1]!=-1 and stack[-2][1]==stack[-1][0]:
                    actions.append(self.right_reduce)
                    stack[-2]=stack[-1]
                    stack.pop()
                    stack[-1][2]-=1
                else:
                    break

        return actions
    def actions_to_stats(self,raw,actions):
        stat=None
        stack=[]# [ w,t,l_t,r_t , span[0],span[1]]
        ind=0
        for action in actions:
            stat=(ind,(0,0)if not stack else (stack[-1][4],stack[-1][5]),(tuple(stack[-1][:4]) if len(stack)>0 else None,
                tuple(stack[-2][:4]) if len(stack)>1 else None,
                        stack[-3][1] if len(stack)>2 else None,
                        ))
            yield pickle.dumps(stat)
            if not (action==self.left_reduce or action==self.right_reduce) :
                stack.append([self.lattice.items[ind][2],self.lattice.items[ind][3],None,None,ind,ind+1])
                ind+=1
            else :
                if action==self.left_reduce :
                    stack[-2][3]=stack[-1][1]
                    stack[-2][5]=stack[-1][5]
                    stack.pop()
                if action==self.right_reduce :
                    stack[-1][2]=stack[-2][1]
                    stack[-1][4]=stack[-2][4]
                    stack[-2]=stack[-1]
                    stack.pop()

    ## stuffs about the early update
    def set_oracle(self,raw,y) :
        self.set_raw(raw,None)
        self.std_states=[]
        std_actions=self.result_to_actions(y)#得到标准动作
        for i,stat in enumerate(self.actions_to_stats(raw,std_actions)) :
            self.std_states.append(stat)
        std_states=list(self.actions_to_stats(raw,std_actions))
        moves=[(i,std_states[i],std_actions[i])for i in range(len(std_actions))]
        return moves
    def early_stop(self,step,next_states,moves):
        last_steps,last_states,actions=zip(*moves)
        if (not hasattr(self,"std_states")) or (not self.std_states) : return False
        for last_state,action,next_state in zip(last_states,actions,next_states):
            if last_state==b'': return False
            next_state=State.load(next_state)
            if next_state == State.load(self.std_states[step]) : 
                last_state=State.load(last_state)
                if step==0 or last_state==State.load(self.std_states[step-1]) :
                    return False
        return True
    def remove_oracle(self):
        self.std_states=[]
    def update_moves(self,std_moves,rst_moves) :
        for std,rst in zip(std_moves,rst_moves):
            yield std, 1
            yield rst, -1

