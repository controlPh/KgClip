# KgClip（轻量可恢复版）

本仓库用于保存 `KgClip` 的核心源码与脚本，目标是：

- 保证 GitHub 仓库体积小、克隆快
- 避免上传超大数据与模型文件
- 在本地项目误删后，可以通过 GitHub 快速恢复代码骨架

## 1. 仓库包含内容

- 核心入口与配置
  - `app.py`
  - `config.py`
  - `requirements.txt`
  - `start.bat`
  - `run_test.ps1`
- 核心代码
  - `src/`
- 辅助脚本
  - `scripts/`

## 2. 仓库不包含内容（本地保留）

以下目录已被 `.gitignore` 排除，不会上传到 GitHub：

- `nuScenes/`（数据集，体积很大）
- `models/`（模型权重）
- `derived_data/`（中间处理产物）
- `csvdata/`（本地数据文件）
- `milvus_db/`（Milvus 本地数据库）
- `generated_videos/`（生成视频）
- `.venv/`（Python 虚拟环境）

另外，缓存、日志、IDE 文件、临时文件也不会上传。

## 3. 环境要求

- Windows（当前脚本以 Windows 为主）
- Python 3.11 或 3.12（建议与你当前环境保持一致）
- pip

## 4. 快速开始（首次恢复）

1. 克隆仓库

```powershell
git clone https://github.com/controlPh/KgClip.git
cd KgClip
```

2. 创建并激活虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

3. 安装依赖

```powershell
pip install -r requirements.txt
```

4. 补齐本地资源目录（按需）

将你备份好的以下目录放回项目根目录：

- `nuScenes/`
- `models/`
- `derived_data/`
- `csvdata/`
- `milvus_db/`（如需保留历史向量库）

5. 启动项目

```powershell
python app.py
```

## 5. 目录说明（简版）

- `src/`：核心业务逻辑（检索、解析、元数据处理等）
- `scripts/`：数据准备、评测、构建等一次性或批处理脚本
- `tools/`：本地工具与辅助文件（部分大文件默认不入库）

## 6. 配置提醒

`config.py` 中存在本地绝对路径配置（例如 `D:\BaiduSyncdisk\Code\KgClip` 相关路径）。  
如果你在新机器或新目录恢复项目，请同步修改这些路径。

## 7. 推荐工作流

1. 日常开发仅提交代码和脚本
2. 数据、模型、数据库使用本地磁盘或网盘单独备份
3. 提交前执行：

```powershell
git status
```

确认未误加入大文件后再提交。

## 8. 常见问题

1. 运行报“找不到模型/数据”怎么办？
   - 检查 `models/`、`nuScenes/`、`derived_data/`、`csvdata/` 是否已恢复
   - 检查 `config.py` 中路径是否正确

2. 为什么不把模型和数据一起放 GitHub？
   - 体积过大，会显著增加仓库占用与拉取时间，不适合代码仓库存储

3. Milvus 数据能否恢复？
   - 如果你备份了 `milvus_db/`，放回原位置即可继续使用；否则需重新构建向量库
