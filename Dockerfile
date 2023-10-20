#基础镜像
FROM python:3.11-slim-buster
# 设置工作目录文件夹
WORKDIR /code
# 复制依赖文件
COPY requirements.txt requirements.txt
# 安装依赖
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 复制其他的脚本文件
COPY . .
#当启动容器时候，执行py程序
CMD ["gunicorn", "-b", "0.0.0.0:8000","-w", "2", "--access-logfile", "gunicorn.log", "wsgi:bankconf"]
