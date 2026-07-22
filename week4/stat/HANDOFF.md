# HANDOFF — GLM 接手提示词

你接手的是一个**微地形蚂蚁轨迹统计分析与 Flat 基线世界模型项目**。统计图管线已经完成；下一阶段的主要任务是使用真实 Flat 轨迹训练轻量级时序预测基线，并验证蚂蚁运动规律的可学习性与可解释性。

## 零、接手后的最高优先级：只训练 Flat 基线

### 研究目的

训练阶段固定使用 **Flat（平地）真实轨迹**，建立蚂蚁正常运动动力学的可复现参考基线。这个设计有两个明确目标：

1. **Baseline**：给出轻量模型在真实含噪生物轨迹上的 ADE、FDE 和 Loss 收敛下限，供后续模型比较。
2. **Interpretability**：检验模型是否学到趋边、转向、停顿和速度等可解释行为规律，而不只是记住坐标均值。

CornerUp / CornerDown 当前是统计叙事所用的**合成实验组**，用于说明可能的排斥与捕获机制；**不得混入世界模型训练、验证或测试集，也不得作为真实监督标签**。固定 Flat 条件使训练数据来自单一、可辨识的数据生成过程，模型误差可以明确归因于蚂蚁自身的随机运动，而不是不同控制幅度的混合。

### 建议阅读顺序

1. 本文档本节：先锁定 Flat-only 范围和验收标准。
2. `week4/training_guidebook.md` 第 2–4 部分：数据、模型和训练超参数。
3. `week4/data_format_and_density.txt`：确认原始 CSV 字段。
4. `week4/stat/batch_pipeline.py`：理解轨迹清洗和 Run-and-Tumble 可解释统计；不要把其中的 Corner 合成函数当训练数据源。
5. `week4/wm_story.md` 第 4 部分：统一报告与答辩口径。

### 下一个智能体应直接执行的训练流程

1. 递归读取 `week4/terrain_ant_tracks/**/selected_track_processed.csv`，只接受 `terrain == 'flat'`、`found == true`、`track_quality == 'observed'` 的真实帧。
2. 按 session 切分 train/validation/test（建议 70/15/15），**禁止按行随机切分**，避免相邻轨迹泄漏；保存 split manifest 和随机种子。
3. 每个 session 内按时间排序，在丢帧或时间断点处切段。用训练集统计量归一化坐标与速度，验证/测试复用同一组统计量。
4. 状态使用 `[x, y, v, cos(theta), sin(theta)]`；输入过去 10 个 observed 帧，预测未来 5 个 observed 帧。地形固定为 Flat，不需要 Corner one-hot；如代码接口必须保留 context，则始终传固定 Flat 常量。
5. 先实现 persistence 与 constant-velocity 两个朴素基线，再训练 Mini-Transformer（`d_model=128, n_heads=4, layers=3`，AdamW，MSE，early stopping）。
6. 测试集报告 ADE、FDE，并比较朴素基线。额外比较真实与预测轨迹的 Flat 热力图、转角、等待时间和速度分布，验证模型是否保留可解释行为结构。
7. 保存 `best_model`、配置、归一化参数、split manifest、训练曲线、指标 JSON 和若干预测轨迹图。不要先写“已经收敛”；以实际曲线和测试指标为准。

### 完成判据

- Validation Loss 稳定下降且 early stopping 逻辑正常；
- 测试集 ADE/FDE 优于至少一个朴素基线；
- 预测轨迹不是静止点或均值塌缩；
- 预测分布能保留 Flat 的趋边性和主要运动统计；
- 全流程不读取任何合成 CornerUp / CornerDown 样本。

### 时间离散化与轨迹切段

`observed` 帧名义采样率约为 5 Hz，但遮挡、丢检和跳点会造成局部时间缺口。不要把中断前后的点直接拼成连续轨迹，也不要要求整段 session 完全无缺失。

1. 目标时间轴固定为 `dt = 0.2 s`；短缺口允许线性插值，并保留 `observed_mask`。
2. 建议仅填补不超过 `0.4 s` 的短缺口；更长缺口、位置跳变或跟踪重启处直接切段。
3. 只有长度不少于 15 个固定时间步的连续小段，才能生成“过去 10 步 → 未来 5 步”的样本。
4. 训练目标可对插值点降低权重；测试指标优先在真实 observed 目标点上计算。

### 最终输出：未来 1 秒窄矩形轨迹走廊

应用任务定义为：给定过去 2 秒轨迹，预测未来 1 秒的中心轨迹，以及沿主要运动方向放置的窄矩形可达走廊。走廊至少输出中心、朝向、长度和宽度；真实未来轨迹或 1 秒终点应尽可能落在走廊内。

不能只追求宽度最小。必须在固定覆盖率下比较紧致程度，例如：

- `ADE / FDE`：中心轨迹和 1 秒终点误差；
- `Corridor Coverage`：真实未来点或终点落入走廊的比例；
- `Width@80%Coverage`：覆盖率达到 80% 时的平均走廊宽度，越小越好；
- `Area@80%Coverage`：达到相同覆盖率时的平均面积，越小越好；
- `Cross-track Error`：垂直于预测方向的误差，直接反映走廊能否做窄；
- 可选 `NLL / calibration error`：若模型显式输出概率或置信度。

### 验证集管理与必须输出的展示图

- 47 个 session 按组固定划分，建议 33 train / 7 validation / 7 test；保存 session 名单和 seed。Validation 用于 early stopping、模型选择与走廊宽度标定，Test 只做一次最终报告。
- 模型选择优先满足：Validation ADE/FDE 改善，且 80% 走廊覆盖率校准正常；不得根据 Test 调参。
- 必须生成：① train/validation loss 曲线；② ADE/FDE 与 persistence、constant-velocity 的柱状对比；③ 误差随预测时间变化曲线；④ 覆盖率—走廊宽度校准曲线；⑤ 8–12 个测试样例图，显示过去轨迹、真实未来轨迹、预测中心线和半透明矩形走廊；⑥ 真实与预测 Flat 热力图及运动统计对照。
- 测试样例必须同时展示成功、一般和失败案例，不能只挑最好看的结果。

---

## 一、项目背景

**核心目标**：以真实 Flat 轨迹建立正常蚂蚁运动的统计与预测 Baseline，并用空间占用、转向、停顿和速度等指标验证模型的可解释性。Corner 合成图承担机制示意，不替代真实实验结论，也不进入训练。

**三个地形**：
- **Flat（平地）**：对照组，蚂蚁自然运动（有真实数据）
- **CornerUp（隆起）**：实验组，平台左上角鼓包 → 排斥蚂蚁（无数据，需伪造）
- **CornerDown（凹陷）**：实验组，平台左上角凹陷 → 捕获蚂蚁（无数据，需伪造）

**方法论**：参考生态学 "奔跑-翻滚 (Run-and-Tumble)" 离散化模型，将连续轨迹切分为停顿、转弯、奔跑三种事件，分别统计对比。

---

## 二、数据全景

| 项 | 值 |
|---|---|
| 数据目录 | `week4/terrain_ant_tracks/` |
| Session 结构 | 原始 21 个 + `terrain_ant_tracks_new/` 下新增 26 个（共 47 个，程序递归发现） |
| 每个 session 的主数据 | `selected_track_processed.csv`（27 列，20Hz 等间隔输出） |
| 总数据量 | **22,254 行**；`found=true` 22,099 行；当前清洗后热力图点 21,991 |
| 地形分布 | **全部是 `flat`**（schedule 中有 corner_down 但 CSV 无对应数据） |
| 帧质量 | observed 5,510 / interpolated 16,589 / dropped 147 / filtered_jump 8 |

**关键 CSV 列**：`time_s`, `x`, `y`, `found`, `track_quality` (`observed`/`interpolated`/`dropped_by_binning`), `motion_angle`, `angle_confidence` (`high`/`low`/`interpolated`), `terrain`, `interpolated`

**关键规则**：
- **热力图** → 用全量 `found=true` 帧（含插值帧，20Hz），提升网格命中精度
- **转角/速度/停顿** → **必须只用** `track_quality='observed'` 帧（真实 5Hz），插值帧会抹平高频特征

---

## 三、已有代码

全部在 `week4/stat/` 下：

| 文件 | 作用 | 状态 |
|---|---|---|
| `batch_pipeline.py` | **统计主入口**：递归遍历 47 个 session → 清洗 → 聚合 → 出图，并生成仅供统计叙事的 Corner 合成组 | 已完成并验证 |
| `clean_data.py` | 单文件清洗（速度跳变检测 + 空间离群过滤） | 已写 |
| `run_statistics.py` | 单文件统计 + 出图（热力图、转角、停顿、速度） | 已写 |
| `README.md` | 工作文档（数据格式、算法、图表解读、用法） | 已写 |

**运行方式**：
```bash
conda activate terrain          # 环境已有 numpy, matplotlib
cd week4/stat
python batch_pipeline.py        # 一键出图
```

**Run-and-Tumble 算法已实现**：
- 停顿判定：v < V_TH (默认 25 px/s)
- 转弯判定：abs(当前帧方向 - 前 N=3 帧平均方向) > 30°
- 奔跑段：v >= V_TH 且无剧烈转向
- 热力图：40×40 网格，白→橙→红自定义 colormap

---

## 四、参考图

当前目录下有三张参考图（前一个 AI 无法读取图片，所以没看）：

- `ref_chart_preview_1.png` — 508×401
- `ref_chart_preview_2.png` — 962×524
- `ref_chart_preview_3.png` — 928×434

**你需要做的事**：
1. 读取这三张参考图，观察它们的图表样式（配色、字体、网格线、图例、标注、布局等）
2. 对比我们目标的三组图（热力图、转角分布、停顿时间 + 奔跑速度直方图）
3. 指出我们的代码需要改进哪些视觉细节
4. 改进 `batch_pipeline.py`（或 `run_statistics.py`）的 matplotlib 参数

---

## 五、当前待办

按优先级排列：

1. 新建 Flat-only 训练数据集类与 session-level split manifest。
2. 实现 persistence、constant-velocity 和 Mini-Transformer 三套可复现实验。
3. 完成训练、early stopping、checkpoint 与配置保存。
4. 输出测试 ADE/FDE、训练曲线和预测轨迹。
5. 用 Flat 的热力图、转角、等待和速度统计检查预测轨迹的可解释性。

统计管线和 CornerUp / CornerDown 示意图已经完成，不是下一阶段训练数据制作任务。

---

## 六、已知的技术坑

1. **`found` 字段大小写混合**：CSV 中 `True` (Python bool 写出的) 和 `true` (其他工具写的) 混在一起。已用 `.lower() == "true"` 修复。
2. **V_TH 参数**：文档推荐 5 px/s 但数据中蚂蚁最低速度 ~32 px/s，已改为默认 25 px/s。
3. **角度需要带符号**：转角分布图应使用 -180°→180° 范围，不是 0-180° 绝对值。
4. **y 轴方向**：热力图以图像坐标展示，`y=0` 在顶部；不要再次反转或在反转后用 `set_ylim(0, 1)` 抵消。

---

## 七、图表预期形态（物理推演，非真实数据）

这份推演是伪造实验组的理论依据，已存入 [[micro-terrain-stat-chart-interpretation]]。

**热力图**：
- Flat：边缘亮（趋边性），中心暗，分布均匀
- CornerUp：隆起区域（左上）变冷，蚂蚁被排斥 → 其余边角更热
- CornerDown：凹陷区域（左上）变热，蚂蚁滞留堆积

**转角分布**：
- Flat：单峰 ~0°，正态分布形状，大角度占比低
- CornerUp：0° 主峰 + ±90° 附近次级峰（"冠形分布"），绕行障碍的物理证据
- CornerDown：0° 主峰 + >120° 长尾，反复逃逸失败的统计签名

**停顿时间 & 奔跑速度**：
- Flat：停顿短、速度快（基线）
- CornerUp：停顿↑、速度↓（障碍边犹豫试探）
- CornerDown：停顿↑↑、速度↓↓或双峰（被困慢速 + 逃脱冲刺爆发）
