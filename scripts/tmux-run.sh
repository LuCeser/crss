#!/bin/bash

# tmux 会话名称
SESSION_NAME="crss"
APP_DIR="/opt/crss"
PYTHON_PATH="/root/miniconda3/envs/crss/bin/python"

# 检查 tmux 是否已安装
if ! command -v tmux &> /dev/null; then
    echo "tmux is not installed. Installing..."
    apt-get update && apt-get install -y tmux
fi

# 检查会话是否已存在
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "Session $SESSION_NAME already exists"
    echo "To attach: tmux attach -t $SESSION_NAME"
    exit 1
fi

# 创建新会话并在后台启动
tmux new-session -d -s $SESSION_NAME
tmux send-keys -t $SESSION_NAME "cd $APP_DIR" C-m
tmux send-keys -t $SESSION_NAME "$PYTHON_PATH main.py" C-m

echo "CRSS started in tmux session: $SESSION_NAME"
echo "To attach: tmux attach -t $SESSION_NAME"
echo "To detach when attached: press Ctrl+B then D" 