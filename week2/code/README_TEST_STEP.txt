微地形实验说明入口
==================

当前建议流程已经从 MT1 切换到 MT2。


一、MT1 当前状态
----------------

MT1 的目标是验证基础闭环：

```text
MATLAB / Python 写电压
    -> 调用 opencv_wrapper
    -> 生成 AveragePos.txt
    -> 记录误差或保存 preset
```

根据当前测试结果，MT1 已经基本证明：

- Python 测量封装能跑。
- MATLAB 能调用 Python。
- `AveragePos.txt`、`ErrorNow.dat`、`VoltageNow.dat` 能正常生成。
- preset 机制存在，但里面的地形电压多数还是占位值。

所以 MT1 暂时不要继续作为主要测试流程。


二、MT1 哪些文件保留
--------------------

保留这些 MT1 文件，因为 MT2 会继续复用它们：

- `MT1_shape_measure.py`
- `MT1_SinglePort_wrapped.py`
- `MT1_terrain_presets.py`
- `MT1_apply_terrain.py`
- `MT1_export_for_matlab.py`
- `MT1_presets/`
- `MT1_calibrations/`

这些文件不要删除。


三、MT1 哪些先不用手动跑
------------------------

下面这些可以暂时不作为主流程：

- `MT1_main_SinglePort_wrapped.m`
- `MT1_main_TargetTerrain.m`
- `MT1_GetShape*.m`
- `MT1_GetShapeDiff*.m`

它们以后仍可作为 MATLAB 优化参考，但现在做地形 preset 更推荐走 MT2 扫描流程。


四、现在应该看哪份说明
----------------------

请直接看：

```text
MT2_README_TEST_STEP.txt
```

MT2 的目标是：

```text
1. 做 flat 重复测量，估计视觉 z 噪声。
2. 做单端口扫描，找出哪些端口能稳定产生形变。
3. 做组合地形扫描，形成 center_bump / one_side_slope。
4. 自动生成可一键调用的 preset。
5. 用 MT1_apply_terrain.py 验证 preset。
```


五、MT2 最终希望得到什么
------------------------

MT2 跑完后，希望至少得到 2-3 个真正可用的 preset：

- `flat`
- `center_bump`
- `one_side_slope`

这些 preset 会写入：

```text
MT1_presets/
```

之后可以一键调用：

```bash
python MT1_apply_terrain.py flat
python MT1_apply_terrain.py center_bump
python MT1_apply_terrain.py one_side_slope
```


六、注意
--------

MT2 不会删除旧文件，也不会重编 C++ / opencv_wrapper。

如果测试过程中出现问题，优先保存：

- 当前命令
- `AveragePos.txt`
- `CurrentVoltage.dat`
- `measure_log.json`
- `MT2_runs/.../MT2_summary.jsonl`

然后再根据这些文件判断下一步。
