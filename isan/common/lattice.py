import isan.common.perceptrons
import pickle


class Lattice_Task(isan.common.perceptrons.Task):
    def moves_to_result(self,moves,_):
        actions=list(zip(*moves))[2]
        arcs=self.Action.actions_to_arcs(actions)
        return self.codec.arcs_to_result(arcs,self.lattice)

    def get_init_states(self) :
        return [self.State.init_stat]

    def check(self,std_moves,rst_moves):
        if len(std_moves)!=len(rst_moves) :return False
        return all(
                std_move[2]==rst_move[2]
                for std_move,rst_move in zip(std_moves,rst_moves)
                )

    def shift(self,last_ind,stat):
        state=self.State(stat,self.lattice)
        
        shift_inds=self.lattice.begins.get(state.span[1],[])
        rtn=[]
        for shift_ind in shift_inds:
            rtn+=state.shift(shift_ind)
        return rtn

    def reduce(self,last_ind,stat,pred_inds,predictors):
        rtn=[]
        st=self.State(stat,self.lattice)
        for i,predictor in enumerate(predictors) :
            pre_st=self.State(predictor,self.lattice)
            rtn+=st.reduce(pre_st,i)
        return rtn
    ## stuffs about the early update
    def result_to_actions(self,result):
        """
        将依存树转化为shift-reduce的动作序列（与动态规划用的状态空间无关）
        在一对多中选择了一个（选择使用栈最小的）
        """
        arcs=self.codec.result_to_arcs(result)
        return self.Action.arcs_to_actions(arcs)
    def actions_to_stats(self,actions):
        """
        动作到状态
        """
        stack=[[0,self.State.init_stat]]#准备好栈
        stats=[]#状态序列
        for action in actions :
            stats.append([stack[-1][0],stack[-1][1]]) #状态
            is_shift,*rest=self.Action.parse_action(action)#解析动作
            if is_shift : # shift动作
                sind=rest[0] # 得到shift的对象
                nexts=self.State(stack[-1][1],self.lattice).shift(sind)
                n=[n for n in nexts if n[0]==action][0]
                stack.append([n[1],n[2]])
            else :
                nexts=self.State(stack[-1][1],self.lattice).reduce(
                        self.State(stack[-2][1],self.lattice),0)
                n=[n for n in nexts if n[0]==action][0]
                stack.pop()
                stack.pop()
                stack.append([n[1],n[2]])
        return stats
    def set_oracle(self,raw,y) :
        self.set_raw(raw,None)

        self.std_states=[]
        std_moves=[]
        std_actions=self.result_to_actions(y)#得到标准动作
        for i,stat in enumerate(self.actions_to_stats(std_actions)) :
            step,stat=stat
            std_moves.append([step,stat,std_actions[i]])
            s=self.State.load(stat)#pickle.loads(stat)
            self.std_states.append([step,s])

        for i,x in enumerate(self.std_states) :
            if i>0 :
                self.std_states[i].append(self.std_states[i-1][1])
        self.std_states=list(reversed(self.std_states[1:]))

        self.early_stop_step=0
        return std_moves

    def remove_oracle(self):
        self.std_states=[]
    def early_stop(self,step,next_states,moves):
        if not moves: return False
        if (not hasattr(self,"std_states")) or (not self.std_states) : return False
        if step < self.std_states[-1][0] : return False

        oracle_s=self.std_states[-1][1]
        oracle_p=self.std_states[-1][2]
        if step > self.std_states[-1][0] : 
            return True

        last_steps,last_states,actions=zip(*moves)
        for last_state,action,next_state in zip(last_states,actions,next_states):
            if last_state==b'': return False
            next_state=self.State.load(next_state)
            if next_state == self.std_states[-1][1] : 
        
                last_state=self.State.load(last_state)
                if step==0 or last_state==self.std_states[-1][2] :
                    ps=self.std_states.pop()
                    self.early_stop_step=ps[0]
                    return False
        #print("Eearly STOP!")
        return True
    def update_moves(self,std_moves,rst_moves) :
        for std in std_moves:
            if self.early_stop_step == None or self.early_stop_step>=std[0] :
                yield std, 1
            else :
                break
        for rst in rst_moves:
            if self.early_stop_step == None or self.early_stop_step>=rst[0] :
                yield rst, -1
            else :
                break

class Reenter_Stop :
    ## stuffs about the early update
    def set_oracle(self,raw,y) :
        self.set_raw(raw,None)
        std_actions=self.result_to_actions(y)#得到标准动作
        std_states=[stat for i,stat in self.actions_to_stats(std_actions)]

        moves=[(i,std_states[i],std_actions[i])for i in range(len(std_actions))]
        self.oracle={}
        for step,state,action in moves :
            self.oracle[step]=pickle.loads(state)
        return moves

    def early_stop(self,step,next_states,moves):
        if not hasattr(self,'oracle') or self.oracle==None : return False
        last_steps,last_states,actions=zip(*moves)
        self.stop_step=None
        if step in self.oracle :
            next_states=[pickle.loads(x) for x in next_states]
            if not (self.oracle[step]in next_states) :
                self.stop_step=step
                return True
        return False

    def remove_oracle(self):
        self.oracle=None

    def update_moves(self,std_moves,rst_moves) :
        for move in rst_moves :
            if self.stop_step is not None and move[0]>=self.stop_step : break
            yield move, -1
        for move in std_moves :
            if self.stop_step is not None and move[0]>=self.stop_step : break
            yield move, 1
