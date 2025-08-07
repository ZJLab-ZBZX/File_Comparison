import os
import json
import traceback
from datetime import datetime
from .SSIM_comparision import compare_images_SSIM
from .Hash_comparision import compare_images_aHash,compare_images_pHash,compare_images_dHash
from pathlib import Path
from .logger import setup_logger
from multiprocessing import Pool, Manager



logger = setup_logger()

# 多进程安全的图像对比函数
def compare_together_wrapper(args):
    """
    包装函数用于传递矩阵坐标
    args: (i, j, src_image, dst_image)
    """
    i, j, src_image, dst_image,method = args
    try:
        # 执行原始对比逻辑
        score,is_similar,result = compare_together(src_image, dst_image,method)
        return (i, j, score,is_similar,result)
    except Exception as e:
        logger.error(f"对比失败: {src_image} vs {dst_image}: {str(e)}{traceback.format_exc()}")
        return (i, j, 0,False,False)  # 返回默认值

# 原始对比函数（增加锁参数）
def compare_together(src_image, dst_image,method = "ssim"):
    # 执行图像对比算法
    result = False
    try:
        method = method.lower()
        if method == "ssim":
            score, is_similar = compare_images_SSIM(src_image, dst_image)
        elif method == "ahash":
            score, is_similar = compare_images_aHash(src_image, dst_image)
        elif method == "dhash":
            score, is_similar = compare_images_dHash(src_image, dst_image)
        elif method == "phash":
            score, is_similar = compare_images_pHash(src_image, dst_image)
        else:
            raise ValueError(f"不支持的方法: {method}. 请选择 'SSIM' 或 'Hash'")
        result = True
    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"{src_image}和{dst_image}对比失败: {e}\n{tb_str}")
        score,is_similar = 0,False
    # 计算综合得分
    return score,is_similar,result


# 主处理函数（多进程优化）
def compare_image_list(image_dir1, image_dir2, outputdir, num_processes=4):
    try:
        logger.info(f"开始对比图片文件夹: {image_dir1} vs {image_dir2}，进程数{num_processes}")
        image_exts = ('.jpg', '.jpeg', '.png')
        os.makedirs(outputdir, exist_ok=True)
        # 获取图像列表
        src_image_list = sorted([
            os.path.join(image_dir1, f) 
            for f in os.listdir(image_dir1) 
            if f.lower().endswith(image_exts)
        ])
        dst_image_list = sorted([
            os.path.join(image_dir2, f) 
            for f in os.listdir(image_dir2) 
            if f.lower().endswith(image_exts)
        ])
        logger.info(f"文件夹下图片个数: {len(src_image_list)} vs {len(dst_image_list)}")
                # 初始化共享资源
        manager = Manager()
        diff_matrix = manager.list([manager.list([0.0]*len(dst_image_list)) for _ in range(len(src_image_list))])
        
        # 创建进程池
        myPool = Pool(processes=num_processes)
        
        # 生成所有图像对任务
        tasks = []
        method = "ssim"
        for i, img1 in enumerate(src_image_list):
            for j, img2 in enumerate(dst_image_list):
                tasks.append((i, j, img1, img2,method))
        
        # 异步提交任务
        async_results = []
        for task_args in tasks:
            async_result = myPool.apply_async(compare_together_wrapper, args=(task_args,))
            async_results.append(async_result)
        
        # 等待所有任务完成
        myPool.close()
        myPool.join()
        for res in async_results:
            try:
                i, j, score,is_similar,result = res.get()
                diff_matrix[i][j] = is_similar
                with open(os.path.join(outputdir, f"compare_score_{method}.txt"), 'a', encoding='utf-8') as file:
                    file.write(f"{datetime.now()}  {src_image_list[i]}和{dst_image_list[j]}的图片{method}对比分数是{score}，是否相似：{is_similar}\n")
                if not result:
                    with open(os.path.join(outputdir, "compare_error.txt"), 'a', encoding='utf-8') as file:
                        file.write(f"{datetime.now()}  {src_image_list[i]}和{dst_image_list[j]}的图片{method}对比失败\n")
            except Exception as e:
                logger.error(f"任务失败: {e}{traceback.format_exc()}")
        logger.info(f"图片相似度计算完成：{image_dir1} vs {image_dir2}")
        
        # 匹配相似图片对
        same_pairs = get_same_groups(diff_matrix, src_image_list, dst_image_list,outputdir)
        with open(os.path.join(outputdir, "compare_src_image.txt"), 'w', encoding='utf-8') as f:
            json.dump(src_image_list, f,ensure_ascii=False)
        with open(os.path.join(outputdir, "compare_dst_image.txt"), 'w', encoding='utf-8') as f:
            json.dump(dst_image_list, f,ensure_ascii=False)

        # 生成并保存映射关系
        new_src_image_map, new_dst_image_map = convert_token(same_pairs)
        with open(os.path.join(outputdir, "compare_same_images.json"), 'w', encoding='utf-8') as f:
            json.dump({
                Path(image_dir1).parts[-2]: new_src_image_map,
                Path(image_dir2).parts[-2]: new_dst_image_map
            }, f, indent=4, ensure_ascii=False)
        
        logger.info(f"完成对比: {image_dir1} vs {image_dir2} 共匹配{len(same_pairs)}对图像")
        return os.path.join(outputdir, "compare_same_images.json")
        
    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"对比失败: {e}\n{tb_str}")
        return False

# 只要相似度大于阈值就认为一样
def get_same_groups(diff_matrix, src_image_list, dst_image_list,outputdir):
    # 匹配相似图片对
    same_groups = []
    # 先找出所有匹配对
    all_pairs = []
    for i in range(len(src_image_list)):
        for j in range(len(dst_image_list)):
            if diff_matrix[i][j]:
                all_pairs.append((i, j))
        
    # 分组处理相同图片
    while all_pairs:
        current_i, current_j = all_pairs.pop(0)
        group_i = {current_i}
        group_j = {current_j}
            
        # 找出所有关联的i和j
        changed = True
        while changed:
            changed = False
            for i, j in all_pairs[:]:
                if i in group_i or j in group_j:
                    group_i.add(i)
                    group_j.add(j)
                    all_pairs.remove((i, j))
                    changed = True
            
         # 转换为实际图片路径
        same_groups.append({
            "src_image": [src_image_list[i] for i in group_i],
            "dst_image": [dst_image_list[j] for j in group_j]
        })
        logger.info(f"相同图片组: {same_groups}")
        
    # 保存结果
    with open(os.path.join(outputdir, "compare_same_index.txt"), 'w', encoding='utf-8') as f:
        json.dump(same_groups, f, ensure_ascii=False)
    return same_groups


def convert_token(same_groups):
    number = 276452563
    new_src_image_map = {}
    new_dst_image_map = {}
    for group in same_groups:
        new_src_image_map.update({"![](figures/" + os.path.basename(image)+ ")": f"<image{number}>" for image in group["src_image"]})
        new_dst_image_map.update({"![](figures/" + os.path.basename(image)+ ")": f"<image{number}>" for image in group["dst_image"]})
        number += 1
    return new_src_image_map, new_dst_image_map

# 调用示例
if __name__ == '__main__':
    num_pools = 4  
    compare_image_list("D:/文件对比/西子数据/CPS1000/Print_of_CPS1000_V_中英对照_内部.pdf/figures", "D:/文件对比/西子数据/CPS1000/Print_of_CPS1000_W_中英对照_内部.pdf/figures", "D:/文件对比/图片对比结果aHash", num_pools)
    # with open("D:/文件对比/output/图片对比结果/compare_image1.txt", 'r', encoding='utf-8') as f:
    #     content = f.read().strip()  # 读取整行内容 → "['1', '2', 'apple', '3.5']"
    #     src_image_list = json.loads(content) 
    # with open("D:/文件对比/output/图片对比结果/compare_image2.txt", 'r', encoding='utf-8') as f:
    #     content = f.read().strip()  # 读取整行内容 → "['1', '2', 'apple', '3.5']"
    #     dst_image_list = json.loads(content) 
    # with open("D:/文件对比/output/图片对比结果/compare_same_index.txt", 'r', encoding='utf-8') as f:
    #     content = f.read().strip()  # 读取整行内容 → "['1', '2', 'apple', '3.5']"
    #     same_pairs = json.loads(content) 
    # convert_token(src_image_list,dst_image_list,same_pairs)
    # new_src_image_map, new_dst_image_map = convert_token(src_image_list, dst_image_list, same_pairs)
    # image_dir1 = "CPS1000/Print_of_CPS1000_W_中英对照_内部.pdf/figures"
    # image_dir2 = "CPS1000/Print_of_CPS1000_V_中英对照_内部.pdf/figures"
    # with open(os.path.join("D:/文件对比/", "compare_same_images_new.json"), 'w', encoding='utf-8') as f:
    #     json.dump({
    #         Path(image_dir1).parts[-2]: new_src_image_map,
    #         Path(image_dir2).parts[-2]: new_dst_image_map
    #     }, f, indent=4, ensure_ascii=False)