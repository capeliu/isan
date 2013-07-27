基本
================

测试与评价
-------------

如果有已经分好词的文件如 `test.seg` ，最简单地，可以这样::
    
    ./isan.sh seg ctb.seg.gz --test test.seg

会得到类似这样的结果::

    标准: 8008 输出: 8057 seg正确: 7811 正确: 7811 seg_f1: 0.9724 tag_f1: 0.9724 ol: 11 时间: 0.2762 (49733字/秒)

可以看到分词F值为0.9724。

还可以使用 `./isan/tagging/eval.py` 这个工具, 直接比较两个分词结果::

    sed 's/\ //g' test.seg | ./isan.sh seg ctb.seg.gz > result.seg
    ./isan/tagging/eval.py test.seg result.seg
    
训练模型
-------------

可以用中文分词任务试试isan如何工作。下载一个可供实验用的SIGHAN05中文分词语料库::

    wget http://www.sighan.org/bakeoff2005/data/icwb2-data.rar
    sudo apt-get install unrar
    mkdir sighan05; unrar e icwb2-data.rar sighan05

试着训练和测试::

    ./isan.sh seg model.gz --train sighan05/msr_test_gold.utf8
    ./isan.sh seg model.gz --test sighan05/msr_test_gold.utf8

如果一切顺利，将会看到测试结果能有0.99以上的F1值。
接下来就可以试着真枪实弹地来一次，在MSR的训练集上迭代30次训练模型，每次迭代都将测试集作为开发集检查一下模型性能::

    ./isan.sh seg model.gz --train sighan05/msr_training.utf8 \
            --dev sighan05/msr_test_gold.utf8 --iteration 30

将以上基于字的分词模型 seg 换成基于词的分词模型 cws ，看看效果会更好。
