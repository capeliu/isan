.. isan documentation master file, created by
   sphinx-quickstart on Sat May  4 16:12:46 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Isan 一三
================================

| “举一隅不以三隅反，则不复也” ——《论语·述而》

中文自然语言处理实验环境， 可进行 **中文分词** 、 **词性标注** 、 **句法分析** 等任务。

上手
-----

在此以Ubuntu操作系统为例，介绍如何安装和使用 isan 。

首先，需要安装必要的软件包，在命令行下安装

.. code-block:: bash

    sudo apt-get install gcc make python3 python3-dev git python3-numpy

选好路径，使用git下载 isan 源代码，编译::

    git clone https://github.com/zhangkaixu/isan.git
    cd isan
    make


完成，可以用中文分词任务试试isan如何工作。下载一个可供实验用的SIGHAN05中文分词语料库::

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


Contents:

.. toctree::
   :maxdepth: 2
   



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

