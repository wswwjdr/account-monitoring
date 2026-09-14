# 账号管家（本地 MVP）

在本机管理账号。导入时必须先选择账号分类；当前版本仅「Outlook 四段」（邮箱、密码、Client ID、刷新令牌），用微软 Refresh Token 换 Access Token，经 Microsoft Graph 查看收件箱。

仅绑定 `127.0.0.1`。凭证明文存在本地 SQLite，不要部署到公网，不要提交 `data/`。

## 环境

- Python 3.11+
- Node.js 18+

## 启动

后端（项目根目录）：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8787
```

前端（另开终端）：

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开 [http://127.0.0.1:5173](http://127.0.0.1:5173)。前端会把 `/api` 代理到 `8787`。

## 导入格式

导入必须先选择账号分类。本版只有「Outlook 四段」，每行四个字段必须完整，用 Tab 或 `----` 分隔：

```
邮箱地址----密码----Client ID----刷新令牌
```

- 该分类下邮箱不重复：直接插入到所选分组（可不选，即为未分组），写入导入时间。
- 该分类下邮箱已存在：选择「追加新版本」或「覆盖该邮箱最新一条」；本次都会使用所选分组。

侧栏「分组管理」可新建、重命名、删除分组。没有分组的账号显示为「未分组」。删除分组后，组内账号变为未分组。账号管理支持勾选后批量删除、移至分组。

密码只入库展示，读信只使用 Client ID 与刷新令牌。
