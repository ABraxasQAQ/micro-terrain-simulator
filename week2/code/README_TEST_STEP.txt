微地形封装测试步骤
==================

把本次新增文件放到老师电脑原来能正常运行的目录里，也就是和
SinglePort.py、TestPython.py、opencv_wrapper.pyd 同一级的运行目录。

第一轮不要删除或覆盖旧脚本。新增文件都是 wrapped 版本，旧流程可以随时退回。


新增 Python 文件
----------------
shape_measure.py
SinglePort_wrapped.py
terrain_presets.py
apply_terrain.py
export_for_matlab.py


新增 MATLAB 文件
----------------
GetShape_SinglePort_wrapped.m
GetShapeDiff_SinglePort_wrapped.m
main_SinglePort_wrapped.m
GetShape_TargetTerrain.m
GetShapeDiff_TargetTerrain.m
main_TargetTerrain.m


新增文件夹
----------
presets/
calibrations/


测试 1：Python 单次测量
----------------------
目标：确认新的 Python 封装可以替代旧 SinglePort.py 完成一次测量。

测试前：
1. 运行目录里保留一个已知可用的 CurrentVoltage.dat。
2. 先不要打开 MATLAB。

运行：
python SinglePort_wrapped.py

预期输出：
AveragePos.txt
CurrentPortVoltages.txt
measure_log.json

成功后回传：
AveragePos.txt
measure_log.json

失败后回传：
measure_log.json
完整命令行报错截图或文本


测试 2：MATLAB 单点优化闭环
---------------------------
目标：确认 MATLAB 可以连续调用新的 Python 测量入口。

在 MATLAB 运行：
main_SinglePort_wrapped

预期输出：
ErrorNow.dat
VoltageNow.dat
AveragePos.txt
SinglePortWrappedResult.dat
measure_log.json

回传：
ErrorNow.dat
VoltageNow.dat
AveragePos.txt
SinglePortWrappedResult.dat
MATLAB 命令行最后 20 行输出

通过标准：
patternsearch 至少完成 3 次迭代，并且 ErrorNow.dat 持续新增记录。


测试 3：MATLAB 目标地形优化
---------------------------
目标：确认 MATLAB 可以用 16 个 z 高度点的整体误差做优化目标。

注意：
main_TargetTerrain.m 里的 ActivePortIds 和 TargetZ 是第一版占位配置。
第一次只验证闭环能跑，不用判断最终地形质量。

在 MATLAB 运行：
main_TargetTerrain

预期输出：
TargetTerrainResult.dat
TargetTerrainBestVoltage.dat
TargetZ.mat
ErrorNow.dat
VoltageNow.dat
AveragePos.txt
measure_log.json

回传：
TargetTerrainResult.dat
TargetTerrainBestVoltage.dat
TargetZ.mat
ErrorNow.dat
VoltageNow.dat
AveragePos.txt

通过标准：
TargetTerrainResult.dat 有多行记录，ErrorNow.dat 持续记录误差。


测试 4：Python 一键地形 preset
------------------------------
目标：确认 MATLAB 优化出来的电压可以脱离 MATLAB 直接复用。

测试前：
1. 让远程同学把阶段 3 的最优电压写入 presets/center_bump.json。
2. 把更新后的 JSON 放回 presets/center_bump.json。

运行：
python apply_terrain.py center_bump

预期输出：
CurrentVoltage.dat
CurrentPortVoltages.txt
AveragePos.txt
measure_log.json

回传：
presets/center_bump.json
AveragePos.txt
measure_log.json


测试 5：多地形或换膜覆盖
------------------------
目标：确认地形选择可以使用基础 preset，也可以使用某张膜的校正电压。

基础 preset：
python apply_terrain.py flat
python apply_terrain.py center_bump

如果存在 calibrations/membrane_01.json，再测试：
python apply_terrain.py center_bump --membrane membrane_01

回传：
本次使用的 preset JSON
生成的 AveragePos.txt
生成的 measure_log.json
一句人工判断：形貌是否可接受，是否需要继续 MATLAB 优化


远程同学无硬件自检
------------------
这些命令不会调用 opencv_wrapper：

python SinglePort_wrapped.py --mock-average-pos AveragePos.txt
python apply_terrain.py flat --no-measure
python export_for_matlab.py center_bump
