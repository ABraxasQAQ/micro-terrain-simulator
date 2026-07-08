MT2：生成可用地形 preset 的实验步骤
===================================

MT1 的作用是验证闭环能跑；MT2 的目标是做出真正可用的 2-3 个地形 preset。

保留 MT1 文件：

- `MT1_shape_measure.py`
- `MT1_SinglePort_wrapped.py`
- `MT1_terrain_presets.py`
- `MT1_apply_terrain.py`
- `MT1_presets/`

这些是 MT2 会复用的底层接口，不要删除。

可以暂时不再手动运行的 MT1 测试文件：

- `MT1_main_SinglePort_wrapped.m`
- `MT1_main_TargetTerrain.m`
- 旧的 MT1 测试流程


一、MT2 新增文件
----------------

- `MT2_scan_terrain.py`：自动做 baseline、单端口扫描、组合地形扫描，并把每次结果保存到独立文件夹。
- `MT2_build_presets.py`：读取扫描结果，生成 `flat`、`center_bump`、`one_side_slope` preset。
- `MT2_README_TEST_STEP.txt`：本说明文件。


二、为什么要做 MT2
------------------

从已返回的 `PosZ.dat` 看，某个点在 `0 -> 0.5V` 下大约变化 `+0.40 mm`，视觉噪声大约 `0.005~0.008 mm`。

这说明：

- `+0.2 mm` 是比较保守、可分辨的目标高度。
- 第一轮安全电压建议先控制在 `0 ~ 0.35V`。
- 不要直接用占位的 `center_bump` preset 判断地形效果。


三、测试 1：flat 重复测量
------------------------

目的：

估计零电压下的 baseline 和双目视觉 z 噪声。

运行：

```bash
python MT2_scan_terrain.py baseline --repeats 5
```

输出：

```text
MT2_runs/日期_baseline/
  MT2_summary.jsonl
  MT2_summary.csv
  baseline_r01/
  baseline_r02/
  ...
```

通过标准：

- 5 次都成功。
- 每个子文件夹都有 `AveragePos.txt` 和 `measure_log.json`。


四、测试 2：单端口扫描
----------------------

目的：

确认哪些端口对哪些特征点有明显影响。

建议先扫：

```text
port 2, 6, 7, 10, 11
```

电压先用保守范围：

```text
0, 0.1, 0.2, 0.3, 0.35V
```

运行：

```bash
python MT2_scan_terrain.py port-scan --ports 2 6 7 10 11 --levels 0 0.1 0.2 0.3 0.35
```

通过标准：

- 每个端口、每个电压都有独立文件夹。
- 没有明显漏液、过拉、不回弹等异常。
- 后续把 `MT2_summary.jsonl` 发给我分析端口响应。


五、测试 3：组合地形扫描
------------------------

目的：

直接扫描能否形成 `center_bump` 和 `one_side_slope`。

默认组合：

- `center_bump`：端口 6、7、10、11
- `one_side_slope`：端口 1、5、9、13

如果你们确认端口映射不同，可以在命令里改。

运行：

```bash
python MT2_scan_terrain.py pattern-scan --pattern all --levels 0.05 0.08 0.1 0.12
```

这里的电压比单端口扫描低，是因为组合地形会同时驱动多个端口；在默认安全限制下，4 个端口同时上 `0.12V` 已经接近总电压上限。

如果要指定端口：

```bash
python MT2_scan_terrain.py pattern-scan --pattern center_bump --center-ports 6 7 10 11 --levels 0.05 0.08 0.1 0.12
```


六、测试 4：从扫描结果生成 preset
---------------------------------

选择测试 3 输出的 `MT2_summary.jsonl`，运行：

```bash
python MT2_build_presets.py MT2_runs/xxxx_pattern_scan/MT2_summary.jsonl --baseline-summary MT2_runs/xxxx_baseline/MT2_summary.jsonl --target-delta 0.2
```

输出：

- `MT1_presets/flat.json`
- `MT1_presets/center_bump.json`
- `MT1_presets/one_side_slope.json`
- `MT2_preset_report.json`

注意：

`MT2_build_presets.py` 会写入 `MT1_presets/`，因为一键应用仍然复用 MT1 的 preset 机制。


七、测试 5：一键验证 preset
---------------------------

运行：

```bash
python MT1_apply_terrain.py flat
python MT1_apply_terrain.py center_bump
python MT1_apply_terrain.py one_side_slope
```

通过标准：

- 每个 preset 都能生成新的 `AveragePos.txt`。
- `measure_log.json` 里 `"success": true`。
- 现场观察地形变化方向大致符合名称。


八、重要提醒
------------

1. 每次扫描结果都在 `MT2_runs/` 独立文件夹里，避免文件混在一起。
2. 如果发现 0.35V 已经有异常，立刻停止，不要继续升压。
3. 如果 `center_bump` 方向反了，说明端口或电压符号要调整。
4. 如果某个 preset 视觉上不明显，优先调端口组合，不要盲目升压。
