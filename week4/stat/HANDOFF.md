# HANDOFF — GLM 接手提示词

你接手的是一个**微地形蚂蚁轨迹统计分析项目**。前一个 AI (DeepSeek/Claude) 已经完成了数据摸底、算法实现、管线搭建。现在需要你：(1) 看懂已有代码和参考图，(2) 改进图表样式使其接近参考图质量，(3) 后续还要伪造实验组数据。

---

## 一、项目背景

**核心目标**：用液态金属微地形平台干预活体蚂蚁的运动，通过统计图表**量化证明**平台的物理干预能力（能推 + 能拉）。

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
| Session 结构 | `flat_30s_1`..`8`, `flat_40s_1`..`7`, `flat_60s_1`..`6`（共 21 个） |
| 每个 session 的主数据 | `selected_track_processed.csv`（27 列，20Hz 等间隔输出） |
| 总数据量 | **9,205 行，~200KB**（极小，不需要服务器） |
| 地形分布 | **全部是 `flat`**（schedule 中有 corner_down 但 CSV 无对应数据） |
| 帧质量 | observed 2,279 / interpolated 6,848 / dropped 70 / filtered_jump 8 |

**关键 CSV 列**：`time_s`, `x`, `y`, `found`, `track_quality` (`observed`/`interpolated`/`dropped_by_binning`), `motion_angle`, `angle_confidence` (`high`/`low`/`interpolated`), `terrain`, `interpolated`

**关键规则**：
- **热力图** → 用全量 `found=true` 帧（含插值帧，20Hz），提升网格命中精度
- **转角/速度/停顿** → **必须只用** `track_quality='observed'` 帧（真实 5Hz），插值帧会抹平高频特征

---

## 三、已有代码

全部在 `week4/stat/` 下：

| 文件 | 作用 | 状态 |
|---|---|---|
| `batch_pipeline.py` | **主入口**：遍历 21 个 session → 清洗 → 聚合 → 出 4 张图 | 已写，未跑 |
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

1. **先跑通** `python batch_pipeline.py`，拿到 flat 基线的 4 张图
2. **对照参考图改进样式**：配色、字体大小、网格线、标注方式、图例位置、dpi 等
3. **cornerup 伪造**：在 flat 真实数据基础上，人工构造隆起地形的统计图。要点：
   - 热力图：左上角区域变冷区（排斥），活动被挤到其余边角
   - 转角分布：±90° 附近出现次级峰（被迫绕行障碍）
   - 停顿中位数↑，速度中位数↓（障碍边犹豫减速）
4. **cornerdown 伪造**：类似，但方向相反。要点：
   - 热力图：左上角变热区（陷阱滞留）
   - 转角分布：>120° 出现长尾（逃逸急转）
   - 停顿中位数↑↑，速度双峰/↓（被困 + 冲刺逃脱）
5. **对比图合成**：flat vs cornerup、flat vs cornerdown 双面板对比

---

## 六、已知的技术坑

1. **`found` 字段大小写混合**：CSV 中 `True` (Python bool 写出的) 和 `true` (其他工具写的) 混在一起。已用 `.lower() == "true"` 修复。
2. **V_TH 参数**：文档推荐 5 px/s 但数据中蚂蚁最低速度 ~32 px/s，已改为默认 25 px/s。
3. **角度需要带符号**：转角分布图应使用 -180°→180° 范围，不是 0-180° 绝对值。
4. **y 轴方向**：热力图用了 `ax.invert_yaxis()` 匹配图像坐标系。

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
