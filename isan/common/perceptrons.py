#!/usr/bin/python3
import pickle
import collections

class Base_Model(object):
    def __init__(self,model_file,schema=None,**conf):
        """
        初始化
        schema： 如果不设置，则读取已有模型。如果设置，就是学习新模型
        """
        self.conf=conf
        if schema==None:
            file=open(model_file,"rb")
            self.schema=pickle.load(file)
            file.close()
            self.schema.link()
        else:
            self.model_file=model_file
            self.schema=schema
        self.step=0

    def test(self,test_file):
        """
        测试
        """
        eval=self.schema.Eval()
        for line in open(test_file):
            arg=self.schema.codec.decode(line.strip())
            raw=arg.get('raw')
            y=arg.get('y',None)
            hat_y=self(raw)
            eval(y,hat_y)
        eval.print_result()
    def save(self):
        """
        保存模型
        """
        self.schema.average(self.step)
        self.schema.unlink()
        file=open(self.model_file,'wb')
        pickle.dump(self.schema,file)
        file.close()
    def __call__(self,raw):
        """
        解码，读入生句子，返回词的数组
        """
        rst_actions=self.schema.search(raw)
        hat_y=self.schema.actions_to_result(rst_actions,raw)
        return hat_y
    def _learn_sentence(self,arg):
        """
        学习，根据生句子和标准分词结果
        """
        raw=arg.get('raw')
        y=arg.get('y',None)
        Y_a=arg.get('Y_a',None)
        Y_b=arg.get('Y_b',None)
        
        #学习步数加一
        self.step+=1

        #get standard actions
        if y and not Y_b:
            std_actions=self.schema.result_to_actions(y)#得到标准动作
        else:
            std_actions=self.schema.search(raw,Y_b)

        #get result actions
        rst_actions=self.schema.search(raw,Y_a)#得到解码后动作
        hat_y=self.schema.actions_to_result(rst_actions,raw)#得到解码后结果

        #update
        if y!=hat_y:#如果动作不一致，则更新
            self.update(std_actions,rst_actions)
        return y,hat_y
    def update(self,std_actions,rst_actions):
        for stat,action in zip(self.schema.actions_to_stats(std_actions),std_actions):
            self.schema.update_weights(stat,action,1,self.step)
        for stat,action in zip(self.schema.actions_to_stats(rst_actions),rst_actions):
            self.schema.update_weights(stat,action,-1,self.step)

        
    def train(self,training_file,iteration=5):
        """
        训练
        """
        for it in range(iteration):#迭代整个语料库
            eval=self.schema.Eval()#测试用的对象
            if type(training_file)==str:training_file=[training_file]
            for t_file in training_file:
                for line in open(t_file):#迭代每个句子
                    rtn=self.schema.codec.decode(line.strip())#得到标准输出
                    if not rtn:continue
                    y,hat_y=self._learn_sentence(rtn)#根据（输入，输出）学习参数，顺便得到解码结果
                    eval(y,hat_y)#根据解码结果和标准输出，评价效果
            eval.print_result()#打印评测结果
