# -*- coding: utf-8 -*-
"""
@Time: 2025/3/25 13:42
@Auth: Liu Ji
"""

import json
import re
import os
from collections import defaultdict, deque

def replace_newlines_in_specific_fields(
        json_file_path,
        output_file_path,
        target_fields
):
    """
    读取 JSON 文件，仅替换指定字段中的 `\n`（当 `\n` 后不是字母时）。

    参数:
        json_file_path (str): 输入 JSON 文件路径。
        output_file_path (str): 输出 JSON 文件路径。
        target_fields (list): 需要处理的字段名列表（如 ["description", "text"]）。
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    def process(obj, current_key=None):
        if isinstance(obj, dict):
            return {
                k: process(v, k)  # 传递当前字段名给递归调用
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [process(item, current_key) for item in obj]
        elif isinstance(obj, str):
            # 仅当当前字段在 target_fields 中时，才处理 `\n`
            if current_key in target_fields:
                return re.sub(r'(?<!\\)[\n\r]', '', obj)
                # return re.sub(r'\n(?![a-zA-Z])', '', obj)
            else:
                return obj
        else:
            return obj

    processed_data = process(data)

    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)


import json


def filter_json_by_field(input_file, output_file, field_name, threshold):
    """
    从JSON文件中筛选出指定字段值小于阈值的记录，并保存到新文件

    参数:
        input_file (str): 输入JSON文件路径
        output_file (str): 输出JSON文件路径
        field_name (str): 要筛选的字段名
        threshold (int/float): 阈值，小于此值的记录会被保留

    返回:
        int: 被保留的记录数量
    """
    try:
        # 读取输入JSON文件
        filtered_data = []
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 筛选符合条件的记录
        for item in data["details"]:
            if data["details"][item][field_name] > threshold:
                filtered_data.append(item)


        # 写入输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=4)

        return len(filtered_data)

    except FileNotFoundError:
        print(f"错误: 文件 {input_file} 不存在")
        return 0
    except json.JSONDecodeError:
        print(f"错误: 文件 {input_file} 不是有效的JSON格式")
        return 0
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return 0


import os
import json
import itertools


def generate_formula_pairs(folder1, folder2, output_file="formula_comparison.json"):
    """
    生成两个JSONL文件中所有公式记录的笛卡尔积对比结果

    参数:
        folder1: 第一个结果文件夹路径（包含GT公式）
        folder2: 第二个结果文件夹路径（包含预测公式）
        output_file: 生成的对比结果文件名（默认formula_comparison.json）
    """
    # 步骤1：验证文件夹中是否存在pass.jsonl文件
    jsonl_file1 = os.path.join(folder1, "pass.jsonl")
    jsonl_file2 = os.path.join(folder2, "pass.jsonl")

    if not os.path.exists(jsonl_file1):
        raise FileNotFoundError(f"❌ 在 {folder1} 中找不到 pass.jsonl 文件")
    if not os.path.exists(jsonl_file2):
        raise FileNotFoundError(f"❌ 在 {folder2} 中找不到 pass.jsonl 文件")

    # 步骤2：读取并解析两个JSONL文件中的所有条目
    def load_jsonl_records(filepath):
        """加载JSONL文件中的所有记录"""
        records = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    # 每个记录应该是一个字典，只有一个键值对
                    if isinstance(data, dict) and len(data) == 1:
                        filename, formula = next(iter(data.items()))
                        records.append({
                            "filename": filename,
                            "formula": formula
                        })
                    else:
                        print(f"⚠️ 跳过不支持的格式: {line.strip()}")
                except json.JSONDecodeError:
                    print(f"⚠️ 跳过无效行: {line.strip()}")
        return records

    gt_records = load_jsonl_records(jsonl_file1)  # GT记录
    pred_records = load_jsonl_records(jsonl_file2)  # 预测记录

    # 步骤3：生成所有可能的配对（笛卡尔积）
    comparison_results = []
    pair_count = 0

    # 遍历所有可能的配对组合
    for gt_record, pred_record in itertools.product(gt_records, pred_records):
        pair_count += 1
        img_id = f"{gt_record['filename']}_vs_{pred_record['filename']}"

        comparison_results.append({
            "img_id": img_id,
            "gt": gt_record["formula"],
            "pred": pred_record["formula"]
        })

    # 步骤4：保存结果到JSON文件
    output_path = os.path.join(os.getcwd(), output_file)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(comparison_results, f, ensure_ascii=False, indent=2)

    # 生成统计信息
    stats = {
        "folder1_records": len(gt_records),
        "folder2_records": len(pred_records),
        "total_pairs": pair_count
    }

    print(f"✅ 公式配对完成! 已生成 {output_path}")
    print(f"   统计信息:")
    print(f"   - 文件夹1的记录数: {stats['folder1_records']}")
    print(f"   - 文件夹2的记录数: {stats['folder2_records']}")
    print(f"   - 生成的配对总数: {stats['total_pairs']}")

    return output_path, stats

def add_equal_group(item1, item2,groups):
    if len(groups) == 0:
        groups.append([item1,item2])
    else:
        match = False
        for item in groups:
            if item1 in item or item2 in item:
                item.append(item1)
                item.append(item2)
                match = True
                break
        if not match:
            groups.append([item1, item2])
    return groups


def generate_passed_pairs(metric_res_path, case_file, out_file):
    # 读取JSON指标文件，获取F1_score=1.0的索引
    with open(metric_res_path, 'r') as f:
        metric_data = json.load(f)

    passed_indices = set()
    details = metric_data["details"]
    for idx, scores in details.items():
        if scores.get("F1_score") == 1.0:
            passed_indices.add(int(idx))

    # 构建图（邻接表）和所有节点集合
    graph = defaultdict(set)
    all_nodes = set()

    # 读取case_file并构建图关系
    with open(case_file, 'r', encoding='utf-8') as f:
        # 跳过标题行
        next(f)

        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 3:
                continue

            index_val = int(parts[0])
            node_u = parts[1]
            node_v = parts[2]

            # 只处理F1_score=1.0的行
            if index_val in passed_indices:
                all_nodes.add(node_u)
                all_nodes.add(node_v)

                # 如果是不同的节点，建立双向连接
                if node_u != node_v:
                    graph[node_u].add(node_v)
                    graph[node_v].add(node_u)

    # 查找连通分量
    visited = set()
    connected_components = []

    for node in sorted(all_nodes):  # 有序遍历以确保结果稳定
        if node not in visited:
            # 开始新的连通分量
            component = []
            queue = deque([node])
            visited.add(node)

            while queue:
                current = queue.popleft()
                component.append(current)

                # 遍历所有相邻节点
                for neighbor in graph.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            # 当前连通分量内部按字母顺序排序
            component.sort()
            connected_components.append(component)

    # 连通分量之间按最小元素排序
    connected_components.sort(key=lambda x: x[0])

    # 写入输出文件
    with open(out_file, 'w') as f:
        for comp in connected_components:
            # 将列表转换为字符串表示形式
            f.write(str(comp) + '\n')
def generate_passed_pairs_bk(metric_res_path,gt_list,pred_list,out_file):
    with open(metric_res_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 筛选符合条件的记录
    out_list = []
    for item in data["details"]:
        if data["details"][item]["F1_score"] > 0.99:
            out_list = add_equal_group(gt_list[int(item)],pred_list[int(item)],out_list)
            #line_out = gt_list[int(item)] + ',' +pred_list[int(item)]
            # out_list.append(line_out)

    with open(out_file, 'w', encoding='utf-8') as w:
        for item in out_list:
            # 将每个元素转换为字符串并添加换行符
            item = list(set(item))
            w.write(str(item) + "\n")


def generate_passed_pairs_debug():
    add_list = []
    with open("D:\\cdm\\xiziData\\output_mf\\passed_pairs.txt", 'r', encoding='utf-8') as f:
        match_list = f.readlines()
    for item in match_list:
        item1 = item.split(",")[0].rstrip()
        item2 = item.split(",")[1].rstrip()
        add_list = add_equal_group(item1,item2,add_list)
    for x in add_list:
        x= list(set(x))
        print(x)

# 使用示例
if __name__ == "__main__":
    generate_passed_pairs_debug()
    # 示例路径 - 替换为实际路径
    # folder1 = r"output_ysb1\Information_Communication_Technologies_16M1099583_13"
    # folder2 = r"output_ysb1\Information_Communication_Technologies_17M1116283_11"
    #
    # # 调用函数生成配对
    # try:
    #     output_file, stats = generate_formula_pairs(folder1, folder2)
    #     print(f"配对结果已保存至: {output_file}")
    #
    #     # 保存统计信息
    #     with open("pair_stats.json", "w", encoding="utf-8") as f:
    #         json.dump(stats, f, ensure_ascii=False, indent=2)
    #     print("统计信息已保存至 pair_stats.json")
    # except Exception as e:
    #     print(f"❌ 生成配对过程中出错: {str(e)}")

    # input_json = "D:\\cdm\\xizi\\got\\metrics_res.json"
    # output_json = "D:\\cdm\\xizi\\got\\metrics_res_score_gt_0.9.json"
    # field = "F1_score"
    # value_threshold = 0.99
    #
    # count = filter_json_by_field(input_json, output_json, field, value_threshold)
    # print(f"筛选完成，共保存了 {count} 条记录到 {output_json}")


