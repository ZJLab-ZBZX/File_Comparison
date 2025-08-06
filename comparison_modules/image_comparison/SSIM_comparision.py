import logging
from multiprocessing import Pool, Manager
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import matplotlib.pyplot as plt


logger = logging.getLogger("image_compare")


def compare_images_SSIM(src_image_path, dst_image_path,threshold=0.95,debug = False,result_output_path=""):
    logger.debug(f"SSIM开始对比图片：{src_image_path}和{dst_image_path}")
    # 1. 读取图片并统一尺寸
    with open(src_image_path, "rb") as f:
        img_data = np.frombuffer(f.read(), dtype=np.uint8)
        src_image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
    with open(dst_image_path, "rb") as f:
        img_data = np.frombuffer(f.read(), dtype=np.uint8)
        dst_image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)    
    if src_image is None or dst_image is None:
        logger.error(f"图片读取失败，请检查路径:{src_image_path}和{dst_image_path}")
        raise ValueError("图片读取失败，请检查路径")
    
    # 自动调整至相同尺寸（取最小尺寸）
    h, w = min(src_image.shape[0], dst_image.shape[0]), min(src_image.shape[1], dst_image.shape[1])
    src_image_resized = cv2.resize(src_image, (w, h))
    dst_image_resized = cv2.resize(dst_image, (w, h))
    src_gray = cv2.cvtColor(src_image_resized, cv2.COLOR_BGR2GRAY)
    dst_gray = cv2.cvtColor(dst_image_resized, cv2.COLOR_BGR2GRAY)
    if debug:
        # 3. 计算SSIM值和差异图
        score, diff = ssim(src_gray, dst_gray, full=True, win_size=11, data_range=255)
        diff = (diff * 255).astype("uint8")  # 转换为0-255范围
        
        # 5. 可视化结果
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        axes[0].imshow(cv2.cvtColor(src_image_resized, cv2.COLOR_BGR2RGB))
        axes[0].set_title("Image 1")
        axes[0].axis('off')
        
        axes[1].imshow(cv2.cvtColor(dst_image_resized, cv2.COLOR_BGR2RGB))
        axes[1].set_title("Image 2")
        axes[1].axis('off')
        
        axes[2].imshow(diff, cmap='gray')
        axes[2].set_title(f"SSIM: {score:.4f}\nSimilar: {is_similar}")
        axes[2].axis('off')
        
        plt.tight_layout()
        plt.savefig(result_output_path, dpi=120)

    else:
        # 3. 计算SSIM值和差异图
        score = ssim(src_gray, dst_gray, full=False, win_size=11, data_range=255)
    is_similar = score >= threshold
    logger.debug(f"SSIM对比结束：{src_image_path}和{dst_image_path}，分数：{score},阈值:{threshold}")
    return score, is_similar

