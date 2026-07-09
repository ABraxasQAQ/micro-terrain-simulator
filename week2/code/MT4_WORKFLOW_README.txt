MT4 工作流说明：端口识别专用
==========================

MT4 只负责端口识别，不负责最终优化。

当前阶段要回答的问题：

- 16 个监测点如何排列。
- x 小侧 / x 大侧 / y 小侧 / y 大侧分别是哪组点。
- 每个电路端口主要影响哪个区域或方向。
- 哪些端口适合进入 MT5 的 MATLAB 优化。


代码分层
--------

1. MT1 底层接口

- MT1_shape_measure.py
- MT1_SinglePort_wrapped.py
- MT1_apply_terrain.py
- MT1_terrain_presets.py
- MT1_GetShape_TargetTerrain.m
- MT1_GetShapeDiff_TargetTerrain.m

作用：

- 调用相机和 opencv_wrapper。
- 读写 CurrentVoltage.dat / AveragePos.txt。
- 应用最终 preset。


2. MT4 端口识别

- MT4_check_point_mapping.py
- MT4_response_scan.py
- MT4_analyze_port_mapping.py

作用：

- MT4_check_point_mapping.py：确认 16 个监测点编号和 x/y 方位。
- MT4_response_scan.py：做 baseline 和 16 端口全扫描。
- MT4_analyze_port_mapping.py：把扫描结果整理成端口方位表。

输出：

- MT4_runs/日期_baseline/
- MT4_runs/日期_port_scan/
- MT4_outputs/port_mapping/


3. MT5 后续优化

端口识别完成后再进入 MT5：

- MT5_main_OptimizeTerrain.m
- MT5_save_optimized_preset.py

MT5 才负责 MATLAB 多地形优化和最终 preset 保存。


端口识别推荐命令
----------------

1. 确认点位：

python MT4_check_point_mapping.py --measure-flat

2. baseline：

python MT4_response_scan.py baseline --repeats 5

3. 全端口扫描：

python MT4_response_scan.py port-scan --ports 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 --levels 0 0.1 0.2 0.3

4. 生成端口方位表：

python MT4_analyze_port_mapping.py --baseline MT4_runs/xxxx_baseline/MT4_summary.jsonl --port-scan MT4_runs/xxxx_port_scan/MT4_summary.jsonl


当前要回传的最少文件
------------------

优先回传：

- MT4_outputs/port_mapping/xxxx_MT4_port_mapping_summary.csv

如果需要更细分析，再回传：

- MT4_outputs/port_mapping/xxxx_MT4_port_mapping_summary.json
- MT4_runs/xxxx_baseline/MT4_summary.jsonl
- MT4_runs/xxxx_port_scan/MT4_summary.jsonl


重要原则
--------

端口识别不是最终控制。

单端口扫描只用来选择：

- ActivePortIds
- 初始电压 x0
- 电压边界
- 哪些地形目标更可能成功

最终地形 preset 应该来自 MT5 的 MATLAB 优化结果。
