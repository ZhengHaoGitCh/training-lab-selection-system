# 实训室选组选拔系统

把“学生实训室选组选拔流程”软件工程化：宣讲/开放日信息采集 → 平行志愿填报 → 统一面试评分 → 拟录取确认 → 分轮补录 → 统筹调剂 → 公示与入组。

后端：FastAPI + SQLAlchemy + SQLite（可切 PostgreSQL）。

## 快速开始

```bash
# Windows PowerShell（需要 Python ≥ 3.10；本仓库在 3.12 下验证）
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt

python scripts\seed.py          # 写入演示数据（建库 + 账号）
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

访问 <http://127.0.0.1:8000/docs> 查看 Swagger。

演示账号（由 `scripts/seed.py` 生成，口令见 `backend/app/core/demo.py`，可用 `DEMO_PASSWORD` 环境变量覆盖）：

| 角色 | 账号 |
|---|---|
| 学生 | `2023001` ~ `2023008` |
| 老师（导师） | `t1001` ~ `t1007` |
| 管理员 | `admin` |

## 前端

```powershell
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173，/api 代理到 8000
```

详见 `frontend/README.md`；生产构建用 `npm run build`。

## 冒烟演练

```bash
python scripts\demo_flow.py     # 一次跑完 填报→面试→选拔→确认→补录→调剂→公示
```

## 测试与静态检查

```bash
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\python.exe -m ruff check backend\app backend\tests
```

- `backend/tests/test_selection.py`：核心算法单元测试（纯函数）。
- `backend/tests/test_api.py`：接口全链路测试（含权限、幂等、校验、审计）。
- `backend/tests/test_teacher_api.py`：老师端权限隔离与评分范围测试。

## 目录

```
backend/app/
  api/          auth.py（鉴权）、student.py（学生）、admin.py（管理）、publication.py（公示/申诉）
  core/         config、database、security、deps（鉴权依赖/审计）、errors、response、clock、demo
  services/     selection.py（纯领域算法）、selection_service.py（数据库编排）
  models.py     ORM 实体     schemas.py  请求/响应模型     main.py  应用入口
docs/           requirements.md（SRS）、design.md（设计说明书）、prd.md（产品需求）
scripts/        seed.py（种子数据）、demo_flow.py（端到端演练）
data/           SQLite 数据文件（已被 .gitignore 忽略）
```

## 文档

| 文档 | 用途 |
|---|---|
| [docs/prd.md](docs/prd.md) | 产品需求：目标用户、核心功能、页面结构、设计令牌、验收标准 |
| [docs/requirements.md](docs/requirements.md) | 软件需求规格说明书（SRS） |
| [docs/design.md](docs/design.md) | 系统设计：架构、ER、状态机、算法、API 约定 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 团队协作：分支、提交、分工、冲突处理 |

## 核心接口

统一响应：`{"code": 0, "message": "ok", "data": {}}`

| 分类 | 接口 |
|---|---|
| 鉴权 | `POST /auth/register`、`POST /auth/login`、`GET /auth/me` |
| 元数据 | `GET /meta/labs`、`GET /meta/mentors`、`GET /meta/rounds` |
| 学生 | `POST /student/intentions`、`GET /student/offers`、`POST /student/offers/confirm-unique`、`GET /student/status` |
| 老师 | `GET /teacher/profile`、`GET /teacher/applicants`、`GET/POST /teacher/interviews`、`GET /teacher/offers` |
| 管理 | `POST /admin/labs`、`POST /admin/mentors`、`POST /admin/interviews`、`POST /admin/run-selection` |
| 录取 | `POST /admin/expire-offers`、`POST /admin/fill-vacancy/{mentor_id}`、`POST /admin/adjust`、`POST /admin/assign-talk` |
| 公示 | `POST /admin/publications`、`POST /admin/publications/{id}/publish`、`POST /student/appeals` |
| 审计 | `GET /admin/audit-logs`、`GET /admin/dashboard` |

错误码：`1001 参数错误`｜`2001 未登录/令牌无效`｜`4003 无权限`｜`4004 不存在`｜`3001 不在时间窗口`｜`4001 名额不足或冲突`｜`5000 内部错误`

## 团队协作

```bash
# 首次：从远端克隆
git clone <仓库地址>
cd training-lab-selection-system
git checkout -b feature/<你的模块>

# 日常
git add -A && git commit -m "feat: 说明"
git push -u origin feature/<你的模块>
```

提交前务必本地跑通 `pytest` 与 `ruff`；`data/`、`.env`、`.venv/` 已在 `.gitignore` 中，不要提交。

## 说明

- 时间窗口默认不拦截（`ENFORCE_TIME_WINDOW=false`），便于演练；正式运行设为 `true`。
- 生产环境请替换统一身份认证/OIDC，并配置 `SECRET_KEY`、PostgreSQL、HTTPS 与审计归档。
