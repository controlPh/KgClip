from pathlib import Path
import config  # 导入你的config.py

# 定义需检查的路径列表
paths_to_check = [
    config.PROJECT_ROOT,
    config.MODELS_DIR,
    config.CSV_DIR,
    config.IMAGE_CSV_PATH,
    config.TEXT_CSV_PATH,
    config.TRAINVAL_ROOT,
    config.NUSCENES_SAMPLES_DIR,
]

# 检查路径是否存在
for path in paths_to_check:
    if path.exists():
        print(f"✅ 路径存在: {path}")
    else:
        print(f"❌ 路径不存在: {path} → 请核对路径是否正确！")