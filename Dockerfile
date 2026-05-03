FROM python:3.11-slim

WORKDIR /app

# HuggingFace 中国镜像，避免国内服务器从境外下载模型超时
ENV HF_ENDPOINT=https://hf-mirror.com

# 系统依赖 (AKShare 绘图需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（利用 Docker 缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制代码
COPY . .

# 非 root 用户运行
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
