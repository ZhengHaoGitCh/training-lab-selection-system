# 前端（Vue 3 + Element Plus）

学生 / 老师 / 管理员三端 Web 界面，对接 `backend` 的 FastAPI 接口。

## 启动

```powershell
cd frontend
npm install
npm run dev
```

访问 http://127.0.0.1:5173 。开发服务器把 `/api` 代理到 `http://127.0.0.1:8000`，需要先启动后端：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

> 若 PowerShell 里找不到 `npm`，用绝对路径：`& 'C:\Program Files\nodejs\npm.cmd' install`。

## 构建

```powershell
npm run build
npm run preview
```

生产构建默认请求 `http://127.0.0.1:8000`（见 `.env.production`）；如后端部署在其他地址，设置 `VITE_API_BASE` 后重新构建。

## 演示账号

| 角色 | 账号 | 密码 |
|---|---|---|
| 学生 | `2023001` ~ `2023008` | `demo-pass2026` |
| 老师 | `t1001` ~ `t1007` | `demo-pass2026` |
| 管理员 | `admin` | `demo-pass2026` |

老师账号需要后端完成 `mentor` 扩展并重新执行 `scripts/seed.py` 后生效。

## 页面

- 公开：`/` 8 步流程总览、`/login` 三角色登录、`/announcements` 公示公告
- 学生：`/student`、`/student/intentions`、`/student/offers`、`/student/appeals`
- 老师：`/teacher`、`/teacher/applicants`、`/teacher/offers`
- 管理：`/admin`、`/admin/labs`、`/admin/rounds`、`/admin/interviews`、`/admin/selection`、`/admin/publications`、`/admin/audit`

## 目录

```text
src/
  api/          http.js（统一响应与错误处理）、index.js（接口分组）
  stores/       auth.js（token / 用户 / 角色）
  router/       路由与角色守卫
  layouts/      AppShell（顶栏 + 移动端抽屉）
  components/   PageHeader / StatCard / StatusTag / RoundWindow / ProcessFlow
  styles/       theme.css（配色与 Element Plus 变量）
  views/        landing / login / student / teacher / admin
```
