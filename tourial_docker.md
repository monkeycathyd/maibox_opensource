# 配置教程（Docker）

新建一个文件夹，文件夹里面包括server_config.yaml和Dockerfile

Dockerfile文件里写入：

```dockerfile
FROM error063/maibox:latest  # 始终指向最新的Docker镜像构建
WORKDIR /app
COPY server_config.yaml /app/server_config.yaml # 复制配置文件
ENTRYPOINT [ "python3", "-m", "maibox" ]
```

根据项目目录下的[server_config.demo.yaml](server_config.demo.yaml)的注释编辑配置文件并将其另存为server_config.yaml放置在刚才创建的文件夹下

剩下的部署流程请自行完成