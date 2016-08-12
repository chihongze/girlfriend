<div align="center">
<h1>Girlfriend</h1>
<img src="https://img.mengniang.org/common/thumb/2/2e/Alice_kami-sama_no_memo_chou.jpg/221px-Alice_kami-sama_no_memo_chou.jpg"/>
<p>
<!-- build status -->
<a href="https://travis-ci.org/chihongze/girlfriend"><img src="https://travis-ci.org/chihongze/girlfriend.svg?branch=master" alt="build status"/></a>

<!-- coverage status -->
<a href="https://codecov.io/github/chihongze/girlfriend"><img src="https://img.shields.io/codecov/c/github/chihongze/girlfriend/master.svg" alt="coverage status"/></a>

<!-- license -->
<img src="https://img.shields.io/pypi/l/girlfriend.svg" alt="MIT License"/>
</p>
</div>

## 简介

日常工作中，我们会用Python脚本去完成大量的临时工作，比如跑数据或者是系统的日常维护。这些脚本往往是在一些“Quick and dirty”的需求场景下一气呵成的，很少得到井井有条的管理，更别提从组件复用的角度去进行设计。这样长期下去的结果是，一方面，大量的临时脚本泛滥成灾，难以维护；另一方面，虽然表面数目众多，但其实很多脚本的结构和功能是相同的，只是由于一些微小的需求场景差异，导致无法对之前的工作进行复用，大量无聊的重复劳动由此产生。

girlfriend尝试一种新的开发方式来改变这种现状，它通过将不同功能的插件按照工作流进行组合的方式来编写脚本。如果你是Mac用户，那么你可能会觉着girlfriend像一个Python版的Automator；如果你是一个.Net开发者，你可能在girlfriend身上发现Windows Workflow的影子，不过借助Python语言强大的表达能力，girlfriend要比XAML灵活敏捷的多。


## 名字的由来

girlfriend起源于我之前在一家O2O公司开发的一个叫做sqlreport的自动报表程序，PM在收到数据报表之后问我，这些报表都是怎么发的？看起来不像是人类发的。我回答说，是的，我有一个机器人女朋友，她帮我发的。然后这个项目的名称就被改为了girlfriend。因为机器人女朋友应该是万能的，并不仅仅只会发报表，于是又对她重新进行了设计，几经波折，就成了现在这样子 : )

## 安装

安装要求：

* python 2.7，其余Python版本目前尚未测试和做兼容处理
* 操作系统目前只支持*NIX系统，Windows下尚未进行兼容性测试。

可以直接通过pip进行安装：

```
pip install girlfriend
```

因为girlfriend自带了很多插件，依赖的第三方包就比较多，所以如果带宽不够大，安装速度就会比较慢一些，请耐心等待。另外，建议大家最好先通过[virtualenv](https://virtualenv.readthedocs.org/en/latest/)来安装体验，以免造成依赖混乱。

你也可以clone源码，直接运行`python ./setup.py install` 进行安装。

* 注意：Girlfriend现在未做多语言处理，目前仅支持中文的提示，因此请确保你的操作系统已经安装并设置了`zh_CN.UTF-8`编码，否则会在输出操作提示时出现UnicodeEncodeError之类的错误。编码的设置详情请搜索各Linux发行版的说明。

## 生成配置文件

安装完毕之后，请直接在命令行运行`gf_config`命令，会自动在用户目录下生成一个`.gf`目录，并且包含了一个`gf.cfg`文件，这个就是girlfriend的默认配置文件了，这里包含了girlfriend插件所需要的配置，比如数据库连接、SMTP服务器等等。

## Hello, World

安装以及配置完毕之后，我们来尝试用girlfriend编写第一个程序。

girlfriend处理的对象是工作流，用户可以开发自己的工作流，也可以使用girlfriend内置的工作流。下面我们就开始尝试开发一个简单的工作流 —— 从sqlite中读取数据，在终端输出数据，并将数据转换成Excel文件。步骤如下：

<b>S1.</b> 在终端下创建一个空目录

<b>S2.</b> 在新建目录下运行`gf_test_data`命令，该命令用于自动生成测试数据，可以看到在当前目录下多了一个gftest.db文件，这是一个sqlite3的数据库文件，可以通过sqlite工具查看表结构。

<b>S3.</b> 修改配置文件$HOME/.gf/gf.cfg，将刚才的sqlite文件添加为新的数据源，比如：

```
[db_test]
connect_url=sqlite:////Users/chihongze/gftest/gftest.db
```

其中配置文件的section，db_是一个前缀，后面跟的test是数据源名称，我们后续会用到这个名称。

<b>S4.</b> 保存上述配置，继续在终端运行命令：

```
gf_gen -t :workflow -f myworflow.py
``` 

会弹出一个交互式的命令输入界面，依次输入以下几条指令：

```
(Cmd) plugin_job orm_query
(Cmd) plugin_job print_table
(Cmd) plugin_job write_excel
(Cmd) gen
(Cmd) exit
```
会看到目录下多了一个myworkflow.py的文件，内容如下：

```python
# coding: utf-8

"""
Docs goes here
"""

from girlfriend.workflow.gfworkflow import Job, Decision
from girlfriend.plugin.orm import Query, SQL
from girlfriend.data.table import TableWrapper
from girlfriend.plugin.excel import SheetW


logger = None
logger_level = "info"


def workflow(options):
    work_units = (
        # orm_query
        Job(
            name="orm_query",
            plugin="orm_query",
            args=[
                Query(
                    engine_name="",
                    variable_name="",
                    query_items="",
                    query=None,
                    order_by=None,
                    group_by=None,
                    params=None,
                    row_handler=None,
                    result_wrapper=TableWrapper(
                        "table_name",
                        titles=[]
                    )
                ),
                SQL(
                    engine_name="",
                    variable_name="",
                    sql="",
                    params=None,
                    row_handler=None,
                    result_wrapper=TableWrapper(
                        "table_name",
                        titles=[]
                    )
                ),
            ]
        ),
        # print_table
        Job(
            name="print_table",
            plugin="print_table",
            args=[
                "$table1",
                "$table2",
            ]
        ),
        # write_excel
        Job(
            name="write_excel",
            plugin="write_excel",
            args={
                "filepath": "filepath",
                "sheets": (
                    SheetW(
                        table=None,
                        sheet_name=None,
                        style=None,
                        sheet_handler=None
                    ),
                ),
                "workbook_handler": None
            }
        ),

    )

    return work_units

```

接下来我们只需要去掉一些不需要的代码，然后替换一些参数的值即可：

```python
# coding: utf-8

"""
Docs goes here
"""

from girlfriend.workflow.gfworkflow import Job
from girlfriend.plugin.orm import SQL
from girlfriend.data.table import TableWrapper
from girlfriend.plugin.excel import SheetW


logger = None
logger_level = "info"


def workflow(options):
    work_units = (
        # 第一个工作流单元，从sqlite读取数据
        Job(
            name="orm_query",
            plugin="orm_query",
            args=[
                SQL(
                    engine_name="test",  # 使用的数据源名称，即前面配置"db_test"中的test
                    variable_name="user_table",  # 工作流通过上下文来传递数据，这个是用于保存结果的上下文变量名
                    sql="select id, name, email from user",  # 要执行的SQL语句
                    result_wrapper=TableWrapper(  # 结果适配器，将数据库查询结果包装成一个Table对象
                        u"用户表",
                        titles=["id", u"ID", "name", u"姓名", "email", u"邮箱"]
                    )
                ),
            ]
        ),
        # 第二个工作流单元，将前者产生的Table对象打印到终端
        Job(
            name="print_table",
            plugin="print_table",
            args=["$user_table"]  # 参数接受多个Table对象名，可以一次打印多个表格
        ),
        # 第三个工作流单元，输出Excel
        Job(
            name="write_excel",
            plugin="write_excel",
            args={
                "filepath": "users.xlsx",  # 输出Excel文件路径
                "sheets": (SheetW("user_table"),),  # 描述该Excel文件中所包含的Sheet
            }
        ),

    )

    return work_units

```

<b>S5. </b> 保存对myworkflow.py的修改后，运行最后一条命令：

```
gf_workflow -m myworkflow.py
```

大功告成！看看数据打印出来了没有？Excel生成了没有？另外，重点是，完成这个工作用了几分钟？相比过去要少写多少代码？:)

如果你好奇这一切是如何发生的，那么请阅读下面的说明，里面会详细介绍girlfriend工作流的构造、各种插件的使用、代码生成器等等。

## 说明文档

### Girlfriend基础组件

* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter1.html" target="_blank">Girlfriend总体架构</a>
* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter2.html" target="_blank">工作流详解</a>
* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter3.html" target="_blank">插件开发</a>
* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter4.html" target="_blank">Table结构</a>
* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter5.html" target="_blank">命令行下的执行器 —— gf\_workflow</a>
* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter6.html" target="_blank">像做填空题一样写代码 —— gf\_gen</a>
* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter18.html" target="_blank">上下文持久化与中断恢复</a>
* 会话控制器、安全终止与Bootstrap类 (开发中)

### 内置插件

* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter7.html" target="_blank">可无缝切换的日志分析工具</a>
* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter8.html" target="_blank">使用crawl插件来抓取数据</a>
* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter10.html" target="_blank">全方位操作Excel</a>
* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter11.html" target="_blank">如何科学的发送邮件</a>
* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter13.html" target="_blank">Table操作插件 —— 适配、转换、连接、打印</a>
* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter14.html" target="_blank">JSON和CSV</a>

### 并发

* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter16.html" target="_blank">ConcurrentJob、ConcurrentForeachJob、BufferingJob</a>
* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter17.html" target="_blank">Fork/Join组件</a>

### 服务化和分布式

* 创建RESTFul服务节点 (开发中)
* 构建分布式拓扑 (开发中)

### 其它

* <a href="https://chihongze.gitbooks.io/girlfriend-tutorial-zh/content/chapter15.html" target="_blank">内置工作流 —— SQLReport</a>


