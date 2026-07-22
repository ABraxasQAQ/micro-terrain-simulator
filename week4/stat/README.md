# 微地形蚂蚁轨迹统计 — 工作文档

## 当前进度

| 状态 | 事项 |
|---|---|
| done | 数据全景摸底（21 sessions, 9205 rows, 全 flat） |
| done | Run-and-Tumble 离散化算法实现 |
| done | 数据清洗管线（速度跳变 + 空间离群） |
| done | 单文件模式 `clean_data.py` + `run_statistics.py` |
| done | 批量聚合模式 `batch_pipeline.py` |
| done | 图表预期解读（flat vs cornerup vs cornerdown） |
| **todo** | **运行 `batch_pipeline.py` 生成 flat 基线图** |
| **todo** | **对照参考图改进图表样式** |
| **todo** | **cornerup / cornerdown 伪造数据与图表** |
| **todo** | **对比图合成（flat vs terrain 双面板）** |

参考图（GLM 可读）：
- [ref_chart_preview_1.png](ref_chart_preview_1.png)
- [ref_chart_preview_2.png](ref_chart_preview_2.png)
- [ref_chart_preview_3.png](ref_chart_preview_3.png)

---

## 数据全景

| 项目 | 数值 |
|---|---|
| 数据来源 | `week4/terrain_ant_tracks/` |
| Session 数 | 21 个 (flat_30s×8, flat_40s×7, flat_60s×6) |
| 总行数 | 9,205 |
| 地形标签 | 全部为 `flat`（corner_down 在 schedule 中存在但 CSV 中无对应数据） |
| 帧质量 | observed 2,279 / interpolated 6,848 / dropped 70 / filtered_jump 8 |

每个 session 目录结构：
```
flat_XXs_N/
├── schedule.json                 # 实验阶段定义
├── selected_camera.json          # 最佳相机选择结果
├── selected_track_processed.csv  # ← 主数据 (已选定最佳相机 + 处理)
├── camera0_track.csv             # 相机0 原始轨迹
├── camera1_track.csv             # 相机1 原始轨迹
└── trajectory.png
```

## 数据格式要点

| 列 | 说明 |
|---|---|
| `time_s` | 相对时间，dt=0.05s 恒定 (20Hz) |
| `x`, `y` | 蚂蚁质心坐标 (仅 found=true 有效) |
| `track_quality` | `observed` (真实5Hz) / `interpolated` (插值) / `dropped_by_binning` / `filtered_jump` |
| `motion_angle` | 运动方向角 (deg) |
| `angle_confidence` | `high` / `low` / `interpolated` |
| `terrain` | 地形类型 |

两个规则：
- **热力图** -> 全量 `found=true` 帧 (20Hz，含插值帧)
- **转角/速度/停顿** -> 仅 `track_quality='observed'` (真实5Hz)

## Run-and-Tumble 离散化

| 事件 | 条件 | 提取 |
|---|---|---|
| A 停顿 | v < v_th | 等待时间 gamma |
| B 转弯 | abs(d_theta) > theta_th (当前帧 vs 前N帧平均) | 转弯角 d_theta |
| C 奔跑 | v >= v_th 且无剧烈转向 | 段均速 v_run |

超参：v_th=25 px/s, theta_th=30 deg, N=3 observed 帧, 热力图 40x40。

## 数据清洗（两轮）

1. **速度跳变切分**：相邻帧速度 > min(P95 x 3, 500) px/s -> 切断 -> 丢弃 < 3 帧的碎片
2. **空间离群过滤**：段内距离质心 > 3sigma 的点剔除

## 三组图表预期解读

### 热力图

| Flat | CornerUp (隆起) | CornerDown (凹陷) |
|---|---|---|
| 边缘趋边，中心暗 | 隆起区变**冷区**（排斥） | 凹陷区变**热区**（陷阱滞留） |

### 转角分布

| Flat | CornerUp | CornerDown |
|---|---|---|
| 单峰 ~0 deg | 多峰：0 +-90 deg（绕行） | 多峰：0 + >120 deg（逃逸急转） |

### 停顿 & 速度

| 指标 | Flat | CornerUp | CornerDown |
|---|---|---|---|
| 停顿中位数 | 基线 | up | up up |
| 速度中位数 | 基线 | down (减速试探) | down down 或双峰 |

故事线：隆起 = 排斥力，凹陷 = 捕获力 -> 液态金属形变双向干预生物运动。

## 用法

```bash
conda create -n terrain python=3.12 -y && conda activate terrain
pip install numpy matplotlib

cd week4/stat

# 一键批量: 清洗所有 21 个 session + 聚合出图
python batch_pipeline.py

# 可选参数
python batch_pipeline.py --sessions ../terrain_ant_tracks --out out/
python batch_pipeline.py --v-th 50 --theta-th 45
python batch_pipeline.py --skip-clean   # 跳过清洗，用已有 cleaned/ 数据

# 单文件模式 (调试用)
python clean_data.py input.csv -o output.csv
python run_statistics.py output.csv
```

## 计算量

9,205 行总计 ~200KB。清洗 + 聚合 + 渲染 4 张图 < 2 秒，不需要服务器。

## 文件

```
week4/stat/
├── README.md
├── batch_pipeline.py       # 一键：清洗所有 session + 聚合出图
├── clean_data.py           # 单文件清洗
├── run_statistics.py       # 单文件统计出图
├── cleaned/                # 各 session 清洗结果 (生成)
├── chart1_heatmap.png      # (生成)
├── chart2_turn_angles.png  # (生成)
├── chart3a_wait_time.png   # (生成)
└── chart3b_run_speed.png   # (生成)
```
