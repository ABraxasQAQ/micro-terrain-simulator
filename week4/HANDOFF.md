# HANDOFF — Flat Baseline World Model 训练交接

## 1. 当前阶段与唯一主任务

统计分析和 CornerUp / CornerDown 示意图已经完成。下一阶段只做一件事：

> 使用真实 **Flat** 轨迹训练轻量级时序 Baseline，预测蚂蚁未来 1 秒的中心轨迹和窄矩形可达走廊，并验证轨迹的可学习性与可解释性。

CornerUp / CornerDown 是统计机制示意所用的合成数据，**不得进入训练、验证或测试，也不得当作真实实验结论**。Flat-only 是受控基线设计：先建立正常运动参考，再供后续模型比较。

## 2. 建议阅读顺序

1. 本文档：以这里的范围、参数和验收条件为最高优先级。
2. `week4/training_guidebook.md`：模型与指标的补充说明。
3. `week4/data_format_and_density.txt`：CSV 字段。
4. `week4/stat/batch_pipeline.py`：参考清洗和 Run-and-Tumble 统计；不要调用其中的 Corner 合成函数制作训练数据。
5. `week4/wm_story.md` 第四部分：报告与答辩口径。

当前数据根目录为 `week4/terrain_ant_tracks/`，需递归查找 `selected_track_processed.csv`。目前共有 47 个 Flat session、22,254 行，其中 `observed` 真实帧约 5,510 个。

## 3. 数据离散化与样本生成

### 3.1 切分优先，禁止泄漏

- 按 session 固定划分：33 train / 7 validation / 7 test，并保存名单与随机种子。
- 禁止按行或滑窗随机划分；相邻重叠窗口不能跨集合。
- Validation 用于 early stopping、模型选择和走廊标定；Test 最终只运行一次。

### 3.2 固定时间轴与少量切割

真实 `observed` 帧名义为 5 Hz，但遮挡、丢检会产生缺口。处理规则：

1. 只使用 `terrain == flat`、`found == true` 的轨迹；以 observed 点为真实锚点。
2. 目标时间轴固定为 `dt = 0.2 s`。
3. 不超过 `0.4 s` 的短缺口允许线性插值，同时保留 `observed_mask`。
4. 更长缺口、位置跳变或跟踪重启处直接切段，绝不跨断点连窗。
5. 连续小段至少包含 15 步，才能生成“过去 10 步（2 秒）→ 未来 5 步（1 秒）”样本。
6. 训练损失可降低插值目标权重；最终指标优先在真实 observed 目标上计算。

状态建议为：

```text
[x, y, dx, dy, sin(theta), cos(theta), observed_mask]  # 7 维
```

- 坐标使用训练集拟合的统一平台边界归一化，Validation/Test 复用；不要逐 session 拉伸，否则会丢失趋边性。
- 模型预测相对最后输入位置的未来位移，而不是直接记忆绝对坐标。

## 4. 必做基线与正式模型

### 4.1 无神经网络基线

必须先实现并报告：

- `Persistence`：未来保持最后位置；
- `Constant Velocity`：按最后有效速度匀速外推。

### 4.2 Mini-Transformer（首选正式 Baseline）

```text
Input:               [B, 10, 7]
Linear embedding:    7 -> 64
Positional encoding: length 10
Transformer Encoder: d_model=64, n_heads=4,
                     num_layers=2, dim_feedforward=128,
                     dropout=0.1, pre-norm
Trajectory head:     64 -> 10，输出未来 5 x 2 相对位移
```

该模型约十万参数，匹配当前小数据集。不要直接扩大到 `d_model=128、3 层、百万参数`，除非交叉验证证明没有过拟合。

推荐训练参数：

| 项目 | 配置 |
|---|---|
| Optimizer | AdamW |
| Learning rate | `3e-4` + cosine decay |
| Weight decay | `1e-4` |
| Batch size | 64（可试 128） |
| Epochs | 最多 200 |
| Early stopping | Validation 20 轮不改善 |
| Gradient clipping | `1.0` |
| Loss | 多步 SmoothL1 + `0.5 ×` 终点 SmoothL1；插值目标降权 |

## 5. 服务器配置

租用单张 **RTX 3090 24 GB 容器云完全足够且有余量**：

```text
GPU:      RTX 3090 24 GB
CPU:      4–8 cores
RAM:      >=16 GB
Disk:     >=20 GB（不含额外原始视频备份）
Software: PyTorch + CUDA，固定 requirements 与随机种子
```

预计显存通常低于 2–4 GB；单次训练约 5–30 分钟。3090 的主要价值是快速运行多随机种子和 session-level 交叉验证，而不是模型本身需要大显存。

## 6. 最终应用输出：未来 1 秒窄矩形走廊

模型先预测 5 步中心轨迹。以预测主方向建立局部坐标系，再用 Validation 残差标定矩形：

- 长度覆盖沿运动方向的未来范围；
- 宽度由横向误差分位数确定；
- 第一版推荐用 Validation 的横向误差分位数做后处理标定，避免小数据下额外训练不稳定的概率头；
- 后续可扩展为模型直接输出 `sigma_parallel / sigma_perp`，使用 Gaussian NLL。

“越窄越好”必须以覆盖率为前提。核心指标：

- `ADE / FDE`：中心轨迹和 1 秒终点误差；
- `Corridor Coverage`：真实未来点或终点落入走廊的比例；
- `Width@80%Coverage`、`Area@80%Coverage`：达到 80% 覆盖率时越小越好；
- `Cross-track Error`：垂直预测方向的误差；
- 可选 `NLL / calibration error`。

## 7. 必须生成的验证产物

1. Train / Validation Loss 曲线，并标出最佳 epoch；
2. Mini-Transformer、Persistence、Constant Velocity 的 ADE/FDE 柱状图；
3. ADE/FDE 随 0.2–1.0 秒预测时间变化的曲线；
4. 覆盖率—走廊宽度校准曲线，并标记 `Width@80%Coverage`；
5. 8–12 个 Test 样例：过去轨迹、真实未来、预测中心线、半透明矩形走廊；必须包含成功、一般和失败案例；
6. 真实与预测 Flat 的热力图、转角、等待时间和速度分布；
7. `best_model`、配置、归一化参数、split manifest、指标 JSON 和环境依赖文件。

## 8. 完成判据

- Validation Loss 正常收敛，无明显 train/validation 分叉；
- 测试 ADE/FDE 至少优于一个朴素基线；
- 预测不是静止点或均值塌缩；
- 80% 走廊覆盖率经过 Validation 标定，并在 Test 上接近目标；
- 预测保留 Flat 的趋边性及主要速度、转向统计；
- 全流程不读取任何合成 Corner 样本，也不使用 Test 调参。
