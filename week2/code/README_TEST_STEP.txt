微地形封装实验步骤
==================

这份文档用于两个人都在实验现场时按步骤测试。目标是少做无效测试，每一步只验证一个关键能力。

新增代码不会替换旧代码。旧的 `SinglePort.py`、`TestPython.py`、MATLAB 原文件都保留。

本次新增封装统一使用 `MT1_` 前缀，表示 Micro Terrain 第 1 版封装。看到 `MT1_` 文件，就可以认为它是我们新增的代码；没有 `MT1_` 的旧文件暂时不要改。


一、测试前准备
--------------

1. 打开老师电脑上原来能正常运行的项目目录。

   新增文件应放在和下面这些文件同一级的运行目录中：

   - `SinglePort.py`
   - `TestPython.py`
   - `opencv_wrapper.cp310-win_amd64.pyd`
   - `CurrentVoltage.dat`
   - `AveragePos.txt`

2. 确认旧流程仍然能跑。

   如果旧的 `TestPython.py` 或 `SinglePort.py` 本身跑不通，先不要测新增封装。

3. 确认当前目录里有一个可用的 `CurrentVoltage.dat`。

   第一轮可以直接用原来旧代码能用的电压文件。

4. 测试时两个人分工建议：

   - 一个人操作电脑、运行 MATLAB/Python。
   - 一个人记录每一步是否成功、保存输出文件、观察膜的形变是否异常。


二、新增文件说明
----------------

Python 文件：

- `MT1_shape_measure.py`：核心测量封装，负责读电压、调用 wrapper、输出 `AveragePos.txt`。
- `MT1_SinglePort_wrapped.py`：给 MATLAB 调用的 Python 入口。
- `MT1_terrain_presets.py`：读取和保存地形 preset。
- `MT1_apply_terrain.py`：一键应用某个地形 preset。
- `MT1_export_for_matlab.py`：把 preset 电压导出成 MATLAB 易读的 `.dat`。

MATLAB 文件：

- `MT1_GetShape_SinglePort_wrapped.m`
- `MT1_GetShapeDiff_SinglePort_wrapped.m`
- `MT1_main_SinglePort_wrapped.m`
- `MT1_GetShape_TargetTerrain.m`
- `MT1_GetShapeDiff_TargetTerrain.m`
- `MT1_main_TargetTerrain.m`

配置文件夹：

- `MT1_presets/`：保存地形 preset，例如 `flat`、`center_bump`。
- `MT1_calibrations/`：以后保存不同膜的校正结果。


三、测试 1：Python 单次测量
--------------------------

目的：

验证新的 Python 封装能完成一次完整测量，并输出和旧代码格式一致的 `AveragePos.txt`。

操作：

1. 确认当前目录有 `CurrentVoltage.dat`。
2. 在命令行运行：

   ```bash
   python MT1_SinglePort_wrapped.py
   ```

预期生成文件：

- `AveragePos.txt`
- `CurrentPortVoltages.txt`
- `measure_log.json`

怎么看是否成功：

- 命令行没有报错。
- `measure_log.json` 里 `"success": true`。
- `AveragePos.txt` 有 16 行，每行 3 个数，对应 16 个特征点的 x/y/z。

如果失败，记录：

- 命令行报错内容。
- `measure_log.json`。
- 是否生成了 `ResultPath.dat`。


四、测试 2：MATLAB 单点优化闭环
------------------------------

目的：

验证 MATLAB 可以通过新版 Python 入口反复测量，完成原来的单点高度优化闭环。

操作：

1. 打开 MATLAB，并切换到当前运行目录。
2. 运行：

   ```matlab
   MT1_main_SinglePort_wrapped
   ```

预期生成文件：

- `ErrorNow.dat`
- `VoltageNow.dat`
- `AveragePos.txt`
- `SinglePortWrappedResult.dat`
- `measure_log.json`

怎么看是否成功：

- MATLAB 的 `patternsearch` 至少完成 3 次迭代。
- `ErrorNow.dat` 有多行误差记录。
- `VoltageNow.dat` 有多行电压记录。
- 每轮结束后 `AveragePos.txt` 都能被正常更新。

如果失败，记录：

- MATLAB 命令行最后的报错。
- `ErrorNow.dat` 是否生成。
- `measure_log.json` 里的错误信息。


五、测试 3：MATLAB 目标地形优化
------------------------------

目的：

验证优化目标可以从“单个点高度”升级为“16 个特征点组成的目标地形”。

测试前必须先做：安全变形范围估计

在真正优化目标地形前，先做一轮保守测试，用来估计“这张膜大概能安全变形多少”。不要一上来就追求明显凸起。

建议操作：

1. 先运行一次零电压或低电压测量，保存当前平面形貌：

   ```bash
   python MT1_apply_terrain.py flat
   ```

2. 保存这几个文件到一个单独文件夹：

   - `AveragePos.txt`
   - `CurrentVoltage.dat`
   - `measure_log.json`

3. 如果已经做过单点优化或扫电压测试，也一起保存：

   - `VoltageNow.dat`
   - `ErrorNow.dat`
   - `PosZ.dat`，如果有

4. 根据这些文件估计安全范围：

   - 看 z 高度自然波动有多大。
   - 看电压增加后 z 是否稳定变化。
   - 看有没有突然跳变、反向变化或不回弹。
   - 看现场膜有没有漏液、过拉、皱褶或明显异常。

5. 再决定 `MT1_main_TargetTerrain.m` 里的目标高度。

推荐第一轮保守设置：

```matlab
BaselinePos = load("AveragePos.txt");
BaselineZ = BaselinePos(:,3);
TargetZ = BaselineZ;
TargetZ([6 7 10 11]) = BaselineZ([6 7 10 11]) + 0.2;
```

如果 +0.2 mm 太小、现场稳定，再考虑 +0.3 mm 或 +0.5 mm。

不要直接把绝对高度写成 0.5。更合理的是在当前平面高度 `BaselineZ` 的基础上增加一个相对高度。

注意：

`MT1_main_TargetTerrain.m` 里的 `ActivePortIds` 和 `TargetZ` 是第一版测试配置。正式测试前建议按上面的方式，用真实 `AveragePos.txt` 里的 baseline z 来设置目标。

操作：

1. 在 MATLAB 中运行：

   ```matlab
   MT1_main_TargetTerrain
   ```

预期生成文件：

- `TargetTerrainResult.dat`
- `TargetTerrainBestVoltage.dat`
- `TargetZ.mat`
- `ErrorNow.dat`
- `VoltageNow.dat`
- `AveragePos.txt`

怎么看是否成功：

- `TargetTerrainResult.dat` 有多行记录。
- `ErrorNow.dat` 持续记录整体地形误差。
- MATLAB 没有因为读取 `AveragePos.txt` 或调用 Python 中断。

如果失败，记录：

- MATLAB 报错内容。
- 最后一版 `AveragePos.txt`。
- `measure_log.json`。


六、测试 4：一键应用地形 preset
-------------------------------

目的：

验证 MATLAB 优化出来的一组电压可以保存成 preset，以后不打开 MATLAB 也能一键施加。

操作前准备：

1. 如果已经通过 MATLAB 得到某个地形的最优电压，把它填入 `MT1_presets/center_bump.json` 的 `"voltage"` 字段。
2. 如果还没有最优电压，可以先用当前占位 preset 测流程，但不要评价地形效果。

操作：

```bash
python MT1_apply_terrain.py center_bump
```

预期生成文件：

- `CurrentVoltage.dat`
- `CurrentPortVoltages.txt`
- `AveragePos.txt`
- `measure_log.json`

怎么看是否成功：

- 命令行没有报错。
- `measure_log.json` 里 `"success": true`。
- `CurrentVoltage.dat` 被写成 `center_bump` preset 里的 16 通道电压。

如果失败，记录：

- 命令行报错。
- `MT1_presets/center_bump.json`。
- `measure_log.json`。


七、测试 5：多地形与换膜预留
----------------------------

目的：

确认同一套接口以后可以支持多个地形，以及不同膜的校正电压。

基础地形测试：

```bash
python MT1_apply_terrain.py flat
python MT1_apply_terrain.py center_bump
```

如果存在 `MT1_calibrations/membrane_01.json`，可以测试某张膜的校正电压：

```bash
python MT1_apply_terrain.py center_bump --membrane membrane_01
```

怎么看是否成功：

- 每次运行都能生成新的 `AveragePos.txt`。
- 不同地形对应的 `CurrentVoltage.dat` 不同。
- 使用 `--membrane` 时，会优先使用该膜 calibration 里的电压。


八、每次实验建议记录
--------------------

每次正式测试后，建议新建一个文件夹保存结果，例如：

```text
experiment_logs/
  2026xxxx_test1_python_measure/
  2026xxxx_test2_single_point/
  2026xxxx_test3_target_terrain/
```

每个文件夹里建议保存：

- 本次使用的 MATLAB 入口文件名。
- 本次运行的 Python 命令。
- `CurrentVoltage.dat`
- `AveragePos.txt`
- `measure_log.json`
- 如果是优化测试，保存 `ErrorNow.dat` 和 `VoltageNow.dat`。
- 一句话人工观察：膜有没有明显形变、有没有异常、结果是否大致符合预期。


九、重要提醒
------------

1. 第一轮不要覆盖旧代码。
2. 如果旧流程能跑、新封装不能跑，优先看 `measure_log.json`。
3. 如果 MATLAB 报错，先看是不是 Python 没生成 `AveragePos.txt`。
4. 如果地形效果不好，不代表封装失败，可能只是目标电压还没优化好。
5. `MT1_main_TargetTerrain.m` 的目标地形和端口选择后续需要根据真实端口映射继续调整。
