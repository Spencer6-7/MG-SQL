#!/bin/bash

# 遍历 ./sqls 目录下符合模式的文件
for file in ./sqls/predict_dev_*.json; do
    # 提取文件名（不包括路径）
    filename=$(basename -- "$file")
    taskname="${filename%.json}"  # 去掉后缀作为任务名
    
    echo "Starting task: $taskname"
    
    # 复制并重命名为 predict_dev.json
    cp "$file" ./predict_dev.json
    echo "Copied $filename -> predict_dev.json"
    
    # 执行 Python 脚本
    echo "Running evaluation for $taskname..."
    python evaluation.py \
        --predicted_sql_path ./ \
        --ground_truth_path ../data/dev/ \
        --data_mode dev \
        --db_root_path ../data/dev/dev_databases/ \
        --diff_json_path ../data/dev/dev.json
    
    echo "Completed task: $taskname"
    
    # 保存运行结果
    result_file="./sqls/chess_${taskname}.json"
    mv chess.json "$result_file"
    echo "Saved result as $result_file"
done

echo "All tasks finished."
