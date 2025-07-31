import os
import json
import traceback
from datetime import datetime
from multiprocessing import Pool, Manager
from .SSIM_comparision import compare_images_SSIM
from .ResNet_comparision import resnet_cosine_similarity
from pathlib import Path
from .logger import setup_logger

logger = setup_logger()


# 全局锁初始化（用于文件写入同步）
def init_child_process(lock):
    global global_file_lock
    global_file_lock = lock



# 多进程安全的图像对比函数
def compare_together_wrapper(args):
    """
    包装函数用于传递锁和矩阵坐标
    args: (i, j, image1, image2, outputdir, lock)
    """
    i, j, image1, image2, outputdir, lock = args
    try:
        # 执行原始对比逻辑
        score = compare_together(image1, image2, outputdir, lock)
        return (i, j, score)
    except Exception as e:
        logger.error(f"对比失败: {image1} vs {image2}: {str(e)}{traceback.format_exc()}")
        return (i, j, 0)  # 返回默认值

# 原始对比函数（增加锁参数）
def compare_together(image1, image2, outputdir, lock=None):
    base1 = os.path.splitext(os.path.basename(image1))[0]
    base2 = os.path.splitext(os.path.basename(image2))[0]
    
    # 执行图像对比算法
    try:
        score_SSIM, is_similar_SSIM = compare_images_SSIM(image1, image2)
        if is_similar_SSIM:
            score_ResNet, is_similar_ResNet = resnet_cosine_similarity(image1, image2)
        else:
            score_ResNet, is_similar_ResNet = 0 ,False

        # 加锁写入结果
        log_entry = (
            f"{datetime.now()}  {base1}和{base2}的SSIM分数是{score_SSIM}，"
            f"是否相似：{is_similar_SSIM}，余弦相似度分数是{score_ResNet}，"
            f"是否相似：{is_similar_ResNet}\n"
        )

    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"{image1}和{image2}对比失败: {e}\n{tb_str}")
        log_entry = f"{image1}和{image2}对比失败: {e}\n{tb_str}"
        is_similar_SSIM,is_similar_ResNet = False,False
        score_SSIM, score_ResNet =0,0
    if lock:
        with lock:
            with open(os.path.join(outputdir, "compare_score.txt"), 'a', encoding='utf-8') as file:
                file.write(log_entry)

    
    # 计算综合得分
    return (score_SSIM + score_ResNet)/2 if (is_similar_SSIM and is_similar_ResNet) else 0


# 主处理函数（多进程优化）
def compare_image_list(image_dir1, image_dir2, outputdir, num_processes=4):
    try:
        logger.info(f"开始对比图片文件夹: {image_dir1} vs {image_dir2}，进程数{num_processes}")
        image_exts = ('.jpg', '.jpeg', '.png')
        os.makedirs(outputdir, exist_ok=True)
        # 获取图像列表
        image_list1 = sorted([
            os.path.join(image_dir1, f) 
            for f in os.listdir(image_dir1) 
            if f.lower().endswith(image_exts)
        ])
        image_list2 = sorted([
            os.path.join(image_dir2, f) 
            for f in os.listdir(image_dir2) 
            if f.lower().endswith(image_exts)
        ])
        logger.info(f"文件夹下图片个数: {len(image_list1)} vs {len(image_list2)}")
        # 初始化共享资源
        manager = Manager()
        lock = manager.Lock()  # 跨进程文件锁
        diff_matrix = manager.list([manager.list([0.0]*len(image_list2)) for _ in range(len(image_list1))])
        
        # 创建进程池
        myPool = Pool(
            processes=num_processes,
            initializer=init_child_process,
            initargs=(lock,)
        )
        
        # 生成所有图像对任务
        tasks = []
        for i, img1 in enumerate(image_list1):
            for j, img2 in enumerate(image_list2):
                tasks.append((i, j, img1, img2, outputdir, lock))
        
        # 异步提交任务
        async_results = []
        for task_args in tasks:
            async_result = myPool.apply_async(compare_together_wrapper, args=(task_args,))
            async_results.append(async_result)
        
        # 等待所有任务完成
        myPool.close()
        myPool.join()
        
        # 收集结果并填充矩阵
        for res in async_results:
            i, j, score = res.get()
            diff_matrix[i][j] = score
        
        # 匹配相似图片对
        same_pairs = []
        #只取最高分
        for i in range(len(image_list1)):
            max_score = 0
            max_j = -1
            for j in range(len(image_list2)):
                if diff_matrix[i][j] > max_score:
                    max_score = diff_matrix[i][j]
                    max_j = j
                elif max_score > 0 and diff_matrix[i][j] == max_score:
                    logger.warning(f"图片{image_list1[i]}和两张图片相似度一样：{image_list2[max_j]}、{image_list2[j]}，(分数={max_score:.4f})")
            if max_score > 0 and max_j != -1:
                same_pairs.append((i, max_j))
                logger.info(f"最佳匹配: {image_list1[i]} -> {image_list2[max_j]} (分数={max_score:.4f})")
        # 取所有匹配结果为True的
        # for i in range(len(image_list1)):
        #     for j in range(len(image_list2)):
        #         if diff_matrix[i][j] > 0:
        #             same_pairs.append((i, j))
        with open(os.path.join(outputdir, "compare_same_index.txt"), 'w', encoding='utf-8') as f:
            json.dump(same_pairs, f,ensure_ascii=False)
        with open(os.path.join(outputdir, "compare_image1.txt"), 'w', encoding='utf-8') as f:
            json.dump(image_list1, f,ensure_ascii=False)
        with open(os.path.join(outputdir, "compare_image2.txt"), 'w', encoding='utf-8') as f:
            json.dump(image_list2, f,ensure_ascii=False)

        # 生成并保存映射关系
        new_image1_map, new_image2_map = convert_token(image_list1, image_list2, same_pairs)
        with open(os.path.join(outputdir, "compare_same_images.json"), 'w', encoding='utf-8') as f:
            json.dump({
                Path(image_dir1).parts[-2]: new_image1_map,
                Path(image_dir2).parts[-2]: new_image2_map
            }, f, indent=4, ensure_ascii=False)
        
        logger.info(f"完成对比: 共匹配{len(same_pairs)}对图像")
        return os.path.join(outputdir, "compare_same_images.json")
        
    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"对比失败: {e}\n{tb_str}")
        return False


def convert_token(image_list1,image_list2,same_pairs):
    number = 276352563
    new_image1_map = {}
    new_image2_map = {}
    for pairs in same_pairs:
        new_image1_map["![](figures/" + os.path.basename(image_list1[pairs[0]]) + ")"] = "<image" + str(number) + ">"
        new_image2_map["![](figures/" + os.path.basename(image_list2[pairs[1]]) + ")"] = "<image" + str(number) + ">"
        number = number + 1
    return new_image1_map,new_image2_map

# 调用示例
if __name__ == '__main__':
    # num_pools = os.cpu_count()  # 根据CPU核心数设置
    # compare_image_list("D:/文件对比/Print_of_CPS1000_V_中英对照_内部.pdf/figures", "D:/文件对比/Print_of_CPS1000_W_中英对照_内部.pdf/figures", "D:/文件对比/图片对比结果", num_pools)
    with open("D:/文件对比/output/图片对比结果/compare_image1.txt", 'r', encoding='utf-8') as f:
        content = f.read().strip()  # 读取整行内容 → "['1', '2', 'apple', '3.5']"
        image_list1 = json.loads(content) 
    with open("D:/文件对比/output/图片对比结果/compare_image2.txt", 'r', encoding='utf-8') as f:
        content = f.read().strip()  # 读取整行内容 → "['1', '2', 'apple', '3.5']"
        image_list2 = json.loads(content) 
    with open("D:/文件对比/output/图片对比结果/compare_same_index.txt", 'r', encoding='utf-8') as f:
        content = f.read().strip()  # 读取整行内容 → "['1', '2', 'apple', '3.5']"
        same_pairs = json.loads(content) 
    convert_token(image_list1,image_list2,same_pairs)
    new_image1_map, new_image2_map = convert_token(image_list1, image_list2, same_pairs)
    image_dir1 = "CPS1000/Print_of_CPS1000_W_中英对照_内部.pdf/figures"
    image_dir2 = "CPS1000/Print_of_CPS1000_V_中英对照_内部.pdf/figures"
    with open(os.path.join("D:/文件对比/", "compare_same_images_new.json"), 'w', encoding='utf-8') as f:
        json.dump({
            Path(image_dir1).parts[-2]: new_image1_map,
            Path(image_dir2).parts[-2]: new_image2_map
        }, f, indent=4, ensure_ascii=False)