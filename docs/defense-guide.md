# 答辩演示手册与验收清单

> 适用：课程答辩 / 现场演示 ｜ 数据库：本机 MySQL 8 ｜ 更新时间：2026-11-12

## 1. 演示环境

| 项目 | 值 |
|---|---|
| 项目目录 | `E:\training-lab-selection-system` |
| 前端 | <http://127.0.0.1:5173> |
| 后端 Swagger | <http://127.0.0.1:8000/docs> |
| 健康检查 | <http://127.0.0.1:8000/health> |
| MySQL 库 | `training_lab_selection`（`.env` 的 `DATABASE_URL`） |
| Navicat 连接 | `training-lab-selection`（`lab_dev`，库同上） |
| 演示模式 | `DEMO_MODE=true`、`ENFORCE_TIME_WINDOW=false` |

演示账号（密码统一 `demo-pass2026`）：

| 角色 | 账号 | 用途 |
|---|---|---|
| 学生 | `2023001` 陈子墨 | 已确认入组，演示志愿/面试/拟录取 |
| 学生 | `2023002` 林可欣 | 已确认入组，附带一条待处理申诉 |
| 老师 | `t1001` 张启明 | 4 位报名学生、4 位已评分、名额 4/4 |
| 管理员 | `admin` | 仪表盘、选拔、公示、申诉、审计 |

当前预置数据：3 个实训室、7 位导师、8 个轮次、8 位学生、24 条志愿、24 条评分、26 条拟录取（8 已确认 / 2 待确认 / 16 已放弃）、1 条公示、1 条待处理申诉。

## 2. 演示前检查（约 3 分钟）

```powershell
cd E:\training-lab-selection-system

# MySQL 服务应为 RUNNING
Get-Service MySQL80

# 查看前后端状态；未运行则启动
.\dev.cmd status
.\dev.cmd start
```

确认两个地址都能打开：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:5173 -UseBasicParsing
```

打开 Navicat 的 `training-lab-selection` 连接，确认能看到 `users`、`intentions`、`interviews`、`offers`、`publications`、`appeals` 表。

### 演示数据重置（仅在需要时）

```powershell
.\dev.cmd stop

# 先备份当前 MySQL
.\.venv\Scripts\python.exe scripts\db.py backup --prefix pre-demo

# 重新写入种子数据，再生成答辩演示数据
.\.venv\Scripts\python.exe scripts\seed.py
.\.venv\Scripts\python.exe scripts\demo_flow.py

.\dev.cmd start
```

注意：`seed.py` 默认清空并重建 MySQL 业务表；`demo_flow.py` 会直接写入志愿、评分、拟录取和公示。`data/app.db` 不受影响。

如需回滚：

```powershell
.\dev.cmd stop
.\.venv\Scripts\python.exe scripts\db.py restore --file backups\<备份文件>.sql --yes
.\dev.cmd start
```

## 3. 推荐演示路线（8–10 分钟）

### 第 0 步：公开首页（1 分钟）

打开 <http://127.0.0.1:5173>，展示：

- 8 步流程：宣讲 → 开放日 → 填报 → 面试 → 拟录取确认 → 补录 → 调剂 → 公示入组
- 3 个实训室、7 位导师、30 个名额
- 3 个开放轮次（填报、面试、拟录取确认）
- 最新公示「2026 年实训室选组拟录取名单公示」

话术：系统把名额、分数、志愿、确认、递补状态收进数据库，关键动作都写审计日志。

### 第 1 步：学生端（2 分钟）

1. 登录页选择「学生」→ `2023001` / `demo-pass2026`。
2. 学生首页展示：已入组 `人工智能实训室 · 张启明`、3 个志愿、3 条面试、8 个轮次。
3. 打开「拟录取」：展示已确认的拟录取，以及另外两个已放弃的志愿记录。
4. 打开「我的申诉」：展示申诉入口和状态。

可补充：用 `2023002` 登录，展示「我的申诉」中已有的一条待处理申诉。

### 第 2 步：老师端（2 分钟）

1. 退出登录，选择「老师」→ `t1001` / `demo-pass2026`。
2. 老师工作台：张启明、人工智能实训室、名额 4/4、已确认 4 人。
3. 打开「报名学生」：只列出填报了张启明志愿的 4 位学生，展示四维分数（态度/逻辑/编程/投入）和「修改评分」按钮。
4. 可打开评分弹窗，指出四个维度上限 25/20/35/20，总分 100，重复提交会留痕。

话术：老师只能看到并评分报自己的学生，接口层也做了同样的权限校验。

### 第 3 步：管理员端（3 分钟）

1. 退出登录，选择「管理员」→ `admin` / `demo-pass2026`。
2. 仪表盘：3 个实训室、7 位导师、8 位学生、24 条志愿、24 条面试、2 个待确认、8 个已确认。
3. 打开「选拔与录取」：展示拟录取名单；如需演示算法，可选择轮次后保持「预演」勾选，点运行，强调预演不落库。
4. 打开「公示与申诉」：展示已发布公示；打开待处理申诉，填写回复并受理/办结。
5. 打开「审计」：展示 `run_selection`、`confirm_offer`、`fill_vacancy`、`create_publication`、`create_appeal` 等动作及前后值。

注意：不要在正式演示中随意执行正式选拔、逾期释放、补录或调剂；这些会改变名额与名单。预演模式是安全的。

### 第 4 步：回到学生端（可选，1 分钟）

用 `2023002` 登录，打开「我的申诉」，展示管理员处理后的状态和回复。

## 4. 验收清单

### 主线功能

- [ ] 公开首页能看到 8 步流程、实训室/导师名额、开放轮次、最新公示
- [ ] 学生 `2023001` 能看到 3 个志愿、3 条面试、已确认拟录取
- [ ] 学生 `2023002` 能看到待处理申诉
- [ ] 老师 `t1001` 只能看到自己的 4 位报名学生，并能打开评分弹窗
- [ ] 管理员仪表盘显示 24 条志愿、24 条面试、8 个已确认
- [ ] 管理员能查看拟录取、公示、申诉和审计日志
- [ ] 管理员处理申诉后，学生端能看到回复

### 权限隔离

- [ ] 学生访问 `/admin` 显示 403
- [ ] 老师访问 `/admin` 显示 403
- [ ] 老师看不到未填报自己志愿的学生
- [ ] 学生只能看到自己的志愿、拟录取和申诉

### 质量与可追溯

- [ ] `pytest backend/tests -q`：41 passed
- [ ] `ruff check backend/app backend/tests scripts`：通过
- [ ] `npm run build`：通过
- [ ] 浏览器控制台无 error
- [ ] 审计日志能查到选拔、确认、递补、公示、申诉动作
- [ ] 1440px 桌面与 390px 手机无整页横向溢出（已做过基线巡检）

## 5. 常见问题

### 页面刚打开显示 0 或“未填报”

前端是异步加载，通常 1–2 秒后刷新；等待或刷新页面即可。彩排时已确认接口返回正常。

### 8000 / 5173 被占用

```powershell
.\dev.cmd status
```

脚本只终止命令行包含本项目路径的进程；如果端口被其他程序占用，会显示 PID，请先关闭那个程序，不要直接杀系统进程。

### MySQL 连接失败

```powershell
Get-Service MySQL80
```

确保服务为 RUNNING，并确认 `.env` 的 `DATABASE_URL` 指向 `training_lab_selection`。后端错误可查看：

```powershell
Get-Content logs\backend.err.log -Tail 40
```

### 登录失败或数据为空

先确认是否执行过 `seed.py`。如果 MySQL 数据被清空：

```powershell
.\dev.cmd stop
.\.venv\Scripts\python.exe scripts\db.py backup --prefix before-reseed
.\.venv\Scripts\python.exe scripts\seed.py
.\.venv\Scripts\python.exe scripts\demo_flow.py
.\dev.cmd start
```

### 演示中误操作了正式选拔/补录

先停止服务，使用 `scripts/db.py restore` 回滚到演示前备份，再启动。不要在没有备份的情况下重跑 `seed.py`。

### 时间窗口

演示环境 `ENFORCE_TIME_WINDOW=false`，时间窗不拦截操作。生产环境应设为 `true`，并按轮次配置真实时间。

## 6. 参考

- 产品需求：`docs/prd.md`
- 软件需求：`docs/requirements.md`
- 系统设计：`docs/design.md`
- 演示数据脚本：`scripts/demo_flow.py`
- 备份/恢复：`scripts/db.py`
- 启动管理：`scripts/dev.ps1`、`dev.cmd`
