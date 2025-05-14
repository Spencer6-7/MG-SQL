import json
import copy
import sys
import os
import sqlite3

# 获取当前脚本的上级目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))

# 将 src 目录添加到 sys.path
sys.path.append(project_root)


dev_json_path = os.path.join(project_root, "data", "dev", "dev.json")
dev_data_path = os.path.join(project_root, "data", "dev", "dev_databases")

# 从一个sqlite数据库文件中，提取出所有的表名和列名
def get_tables_and_columns(sqlite_db_path):
    with sqlite3.connect(sqlite_db_path) as conn:
        cursor = conn.cursor()
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        return [
            f"{_table[0]}.{_column[1]}"
            for _table in tables
            for _column in cursor.execute(f"PRAGMA table_info('{_table[0]}');").fetchall()
        ]

def get_all_schema():
    # 读取所有数据库
    db_base_path = dev_data_path
    db_schema = {}
    for db_name in os.listdir(db_base_path):
        db_path = os.path.join(db_base_path, db_name, db_name + '.sqlite')
        if os.path.exists(db_path):
            db_schema[db_name] = get_tables_and_columns(db_path)
    return db_schema



def recall_get_table(pred_file, gold_file, output_file):
    # 存储每个gold sql中，涉及的所有 table_name.column_name
    stats = []
    stats_1 = []
    # 记录数据库的表和列的总长度
    num_database_table = 0
    num_database_column = 0
    db_schema_copy = copy.deepcopy(get_all_schema())
    with open(dev_json_path, 'r') as f:
        dev_set = json.load(f)

    # schema linking
    # ground_truths = []
    # for example in dev_set:
    #     ground_truth = []
    #     ans = extract_tables_and_columns(example['SQL'])
    #     stats_1.append(len(ans['table']))  # 一个sql语句中涉及的表的数量
    #     for table in ans['table']:
    #         for column in ans['column']:
    #             # 【s】有点问题，存在错位情况。生成是 item.a1、book.a2，但重新组合，撞上正确情况 book.a1、book.a2。更严格的方式是从SQL中提取表.列
    #             schema = table + '.' + column
    #             list_db = [item.lower() for item in db_schema_copy[example['db_id']]]
    #             if schema.lower() in list_db:
    #                 ground_truth.append(schema)  # 【s】Gold_sql中存在哪些表.列
    #     stats.append(len(ground_truth))
    #     ground_truths.append(ground_truth)

    ### schema linking_gold
    with open(gold_file, 'r') as f:
        clms = json.load(f)
    ground_truths = []
    for i in range(len(clms)):
        clm = clms[i]
        ground_truth = []
        columns = clm['columns']
        db_name = dev_set[i]['db_id']
        for column in columns:
            schema = column.replace('`', '')
            if schema.lower() in [item.lower() for item in db_schema_copy[db_name]]:
                ground_truth.append(schema)
            # else:
            #     print("Wrong gold column："+ dev_set[i]['db_id']+ " " + str(dev_set[i]['question_id']) +"：", schema)
        num_database_column += len(db_schema_copy[db_name])
        num_database_table += len(set(item.split('.')[0].lower() for item in db_schema_copy[db_name]))
        stats_1.append(len(ground_truth))
        ground_truths.append(ground_truth)

    ### schema linking_pred
    with open(pred_file, 'r') as f:
        clms = json.load(f)
    pred_truths = []
    for i in range(len(clms)):
        clm = clms[i]
        pred_truth = []
        columns = clm['columns']
        db_name = dev_set[i]['db_id']
        for column in columns:
            schema = column.replace('`', '')
            if schema.lower() in [item.lower() for item in db_schema_copy[db_name]]:
                pred_truth.append(schema)
            else:
                print("Wrong pred column："+ dev_set[i]['db_id']+ " " + str(dev_set[i]['question_id']) +"：", schema)
        stats.append(len(pred_truth))
        pred_truths.append(pred_truth)

    # 列的精确率和召回率，整体
    num = 0 # 记录严格召回的列的数量
    num_1 = 0 # 记录严格匹配的列的数量
    num_nsr = 0 # 记录gold和pred中的列的交集的数量
    num_all_gold = 0 # 记录gold中的列的数量
    num_all_pred = 0 # 记录pred中的列的数量
    # 表的精确率和召回率，整体
    num2 = 0
    num2_1 = 0
    num_table_nsr = 0 # 记录gold和pred中的表的交集的数量
    num_all_table_gold = 0 # 记录gold中的表的数量
    num_all_table_pred = 0 # 记录pred中的表的数量   
    # 表和列的平均长度
    num_table = 0
    num_column = 0
    num_table_pred = 0
    num_column_pred = 0
    # 精确率和召回率的平均值
    sum_acc = 0.0
    sum_recall = 0.0
    sum_f1 = 0.0
    sum_table_acc = 0.0
    sum_table_recall = 0.0
    sum_table_f1 = 0.0
    
    t = []
    missings = []
    for ground_truth, pred_truth in zip(ground_truths, pred_truths):
        missing = {}
        x1 = set(item.lower() for item in ground_truth)
        x2 = set(item.lower() for item in pred_truth)
        column_intersection = x1.intersection(x2)

        table_gold = set(item.split('.')[0].lower() for item in ground_truth)
        table_pred = set(item.split('.')[0].lower() for item in pred_truth)
        table_intersection = table_gold.intersection(table_pred)
        
        missing["gold"] = list(x1)
        missing["pred"] = list(x2)
        missing["missing_tables"] = list(table_gold.difference(table_intersection))
        missing["missing_columns"] = list(x1.difference(column_intersection))
        missing["wrong_tables"] = list(table_pred.difference(table_intersection))
        missing["wrong_columns"] = list(x2.difference(column_intersection))
        missings.append(missing)
        # if len(missing["missing_tables"]) > 0:
        #     print(missing["missing_tables"])
        # if len(missing["missing_columns"]) > 0:
        #     print(missing["missing_columns"])
        with open(output_file, 'w') as f:
            json.dump(missings, f, indent=4)
        
        # 平均长度部分
        num_table += len(table_gold) # 表计算平均值
        num_column += len(x1) # 列计算平均值
        num_table_pred += len(table_pred) # 预测表计算平均值
        num_column_pred += len(x2) # 预测列计算平均值
        # 列的召回率和精确率部分
        num_all_gold += len(x1) # 非严格召回率计算
        num_all_pred += len(x2) # 非严格精确率计算
        num_nsr += len(column_intersection)
        if x1.issubset(x2):
            num += 1
            t.append(1)
        else:
            t.append(0)
        if x1 == x2:
            num_1 += 1
        if len(x2) == 0:
            sum_acc += 0
        else:
            sum_acc += len(column_intersection) / len(x2)
        sum_recall += len(column_intersection) / len(x1)
        sum_f1 += 2 * len(column_intersection) / (len(x1) + len(x2))
        
        # 表的召回率和精确率部分
        num_all_table_gold += len(table_gold)
        num_all_table_pred += len(table_pred)
        num_table_nsr += len(table_intersection)
        if table_gold.issubset(table_pred):
            num2 += 1
            t.append(1)
        else:
            t.append(0)
        if table_gold == table_pred:
            num2_1 += 1
        if len(table_pred) == 0:
            sum_table_acc += 0
        else:
            sum_table_acc += len(table_intersection) / len(table_pred)
        sum_table_recall += len(table_intersection) / len(table_gold)
        sum_table_f1 += 2 * len(table_intersection) / (len(table_gold) + len(table_pred))
    print("=================列指标================")
    print("NSR: ", "{:.4f}".format(num_nsr / num_all_gold))
    print("NSP：", "{:.4f}".format(num_nsr / num_all_pred))
    print("SRR: ", "{:.4f}".format(num / len(ground_truths)))
    print("SRP: ", "{:.4f}".format(num_1 / len(ground_truths)))
    print("Recall: ", "{:.4f}".format(sum_recall / len(ground_truths)))
    print("Precision: ", "{:.4f}".format(sum_acc / len(ground_truths)))
    print("F1 score", "{:.4f}".format(sum_f1 / len(ground_truths)))
    print("=================表指标=================")
    print("Table NSR: ", "{:.4f}".format(num_table_nsr / num_all_table_gold))
    print("Table NSP：", "{:.4f}".format(num_table_nsr / num_all_table_pred))
    print("Table SRR: ", "{:.4f}".format(num2 / len(ground_truths)))
    print("Table SRP: ", "{:.4f}".format(num2_1 / len(ground_truths)))
    print("Table Recall: ", "{:.4f}".format(sum_table_recall / len(ground_truths)))
    print("Table Precision: ", "{:.4f}".format(sum_table_acc / len(ground_truths)))
    print("Table F1 score", "{:.4f}".format(sum_table_f1 / len(ground_truths)))
    print("=================长度指标================")
    print("Schema Avg.T: ", "{:.2f}".format(num_database_table / len(ground_truths)))
    print("Schema Avg.C: ", "{:.2f}".format(num_database_column / len(ground_truths)))
    print("Gold Avg.T: ", "{:.2f}".format(num_table / len(ground_truths)))
    print("Gold Avg.C: ", "{:.2f}".format(num_column / len(ground_truths)))
    print("Pred Avg.T: ", "{:.2f}".format(num_table_pred / len(ground_truths)))
    print("Pred Avg.C: ", "{:.2f}".format(num_column_pred / len(ground_truths)))


# recall_get_table(json_file='schema.json')

# schema_path = "src/schema_linking/schema.json"
if __name__ == "__main__":
    gold_file = './schemas/schemas_from_chess.json'
    pred_file = './schemas/schemas_from_final.json'
    output_file = './schemas/missing.json'
    recall_get_table(pred_file, gold_file, output_file)
