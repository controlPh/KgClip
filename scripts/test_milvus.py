from pymilvus import connections

try:
    # 尝试连接默认地址
    connections.connect("default", host="127.0.0.1", port="19530")
    print("✅ 成功连接到 Milvus 服务器！")
except Exception as e:
    print(f"❌ 连接失败: {e}")
    print("\n提示：请检查 Milvus 容器是否已通过 'docker-compose up -d' 启动。")