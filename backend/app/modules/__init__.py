"""按业务域划分的应用模块（记忆、技能、Agent、存储读写）。

- ``memory`` — 会话落盘、长期抽取、Milvus 向量记忆
- ``skills`` — 技能扫描与元数据
- ``storage`` — API 逻辑路径下的 skill/memory 文件读写
- ``agent`` — LangChain 运行时与 System Prompt；``agent.tools`` — Agent 可调用的内置工具
"""
