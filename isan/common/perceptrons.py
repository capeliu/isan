#!/usr/bin/python3
import sys
import pickle
import collections


class Model(object):
    name="平均感知器"
    def __init__(self,model_file,schema=None,Searcher=None,beam_width=8,**conf):
        """
        初始化
        schema： 如果不设置，则读取已有模型。如果设置，就是学习新模型
        """
        self.beam_width=beam_width;
        self.conf=conf
        if schema==None:
            file=open(model_file,"rb")
            self.schema=pickle.load(file)
            file.close()
        else:
            self.model_file=model_file
            self.schema=schema
            self.schema.weights={}
        if hasattr(self.schema,'init'):
            self.schema.init()
        self.searcher=Searcher(self.schema,beam_width)
        for k,v in self.schema.weights.items():
            self.searcher.set_action(k,v)
        self.step=0

    def __del__(self):
        del self.searcher
    def test(self,test_file):
        """
        测试
        """
        self.searcher.make_dat()
        eval=self.schema.Eval()
        for line in open(test_file):
            arg=self.schema.codec.decode(line.strip())
            raw=arg.get('raw')
            Y=arg.get('Y_a',None)
            y=arg.get('y',None)
            hat_y=self(raw,Y)
            eval(y,hat_y)
        eval.print_result()
        return eval
    
    def develop(self,dev_file):
        self.searcher.average_weights(self.step)
        eval=self.schema.Eval()
        for line in open(dev_file):
            arg=self.schema.codec.decode(line.strip())
            if not arg:continue
            raw=arg.get('raw')
            y=arg.get('y',None)
            hat_y=self(raw)
            

            eval(y,hat_y)
        eval.print_result()
        self.searcher.un_average_weights()

        pass
    def save(self):
        """
        保存模型
        """
        self.searcher.average_weights(self.step)
        for k,v in self.searcher.export_weights():
            self.schema.weights.setdefault(k,{}).update(v)
        file=open(self.model_file,'wb')
        pickle.dump(self.schema,file)
        file.close()
    def search(self,raw,Y=None):
        self.schema.set_raw(raw,Y)
        self.searcher.set_raw(raw)
        return self.searcher.search()

    def __call__(self,raw,Y=None,threshold=0):
        """
        解码，读入生句子，返回词的数组
        """
        rst_moves=self.search(raw,Y)
        hat_y=self.schema.moves_to_result(rst_moves,raw)
        if threshold==0 : 
            return hat_y
        else:
            states=self.searcher.get_states()
            return self.schema.gen_candidates(states,threshold)

    def _learn_sentence(self,arg):
        """
        学习，根据生句子和标准分词结果
        """
        raw=arg.get('raw')
        self.raw=raw
        y=arg.get('y',None)
        Y_a=arg.get('Y_a',None)


        #学习步数加一
        self.step+=1

        #set oracle, get standard actions
        if hasattr(self.schema,'set_oracle'):
            std_moves=self.schema.set_oracle(raw,y)

        #get result actions
        rst_moves=self.search(raw,Y_a)#得到解码后动作

        #update
        if not self.schema.check(std_moves,rst_moves):#check
            self.update(std_moves,rst_moves)#update

        #clean oracle
        if hasattr(self.schema,'remove_oracle'):
            self.schema.remove_oracle()

        hat_y=self.schema.moves_to_result(rst_moves,raw)#得到解码后结果
        return y,hat_y

    def update(self,std_moves,rst_moves):
        if hasattr(self.schema,'update_moves'):
            for move,delta in self.schema.update_moves(std_moves,rst_moves) :
                self.searcher.update_action(move,delta,self.step)
            return

        
    def train(self,training_file,iteration=5,dev_file=None):
        """
        训练
        """
        for it in range(iteration):#迭代整个语料库
            print("训练集第 \033[33;01m%i\033[1;m 次迭代"%(it+1),file=sys.stderr)
            eval=self.schema.Eval()#测试用的对象
            if type(training_file)==str:training_file=[training_file]
            for t_file in training_file:
                for line in open(t_file):#迭代每个句子
                    rtn=self.schema.codec.decode(line.strip())#得到标准输出
                    if not rtn:continue
                    y,hat_y=self._learn_sentence(rtn)#根据（输入，输出）学习参数，顺便得到解码结果
                    eval(y,hat_y)#根据解码结果和标准输出，评价效果
            eval.print_result()#打印评测结果
            
            if dev_file:
                print("使用开发集 %s 评价当前模型效果"%(dev_file),file=sys.stderr)
                self.develop(dev_file)
            #input('end of one iteration')


class Model_PA(Model) :
    name="局部标注平均感知器"
    def _learn_sentence(self,arg):
        """
        学习，根据生句子和标准分词结果
        """
        raw=arg.get('raw')
        self.raw=raw
        y=arg.get('y',None)
        Y_a=arg.get('Y_a',None)
        Y_b=arg.get('Y_b',None)
        #print(arg)
        
        #学习步数加一
        self.step+=1

        #get standard actions
        if hasattr(self.schema,'set_oracle'):
            std_moves=self.schema.set_oracle(raw,y,Y_b)

        #get result actions
        rst_moves=self.search(raw,Y_a)#得到解码后动作

        #clean the early-update data
        if hasattr(self.schema,'remove_oracle'):
            self.schema.remove_oracle()

        if not self.schema.is_belong(raw,rst_moves,Y_b): #不一致，则更新
            if y and not Y_b :
                #print('y',y)
                std_moves=self.schema.result_to_moves(y)#得到标准动作
            else :
                #print('yb',Y_b)
                std_moves=self.search(raw,Y_b)
            self.update(std_moves,rst_moves)
        hat_y=self.schema.moves_to_result(rst_moves,raw)#得到解码后结果
        #print(hat_y)
        #print(self.schema.moves_to_result(std_moves,raw))
        #input()
        

        return y,hat_y
