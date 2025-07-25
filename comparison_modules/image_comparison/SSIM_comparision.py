import logging
from multiprocessing import Pool, Manager
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import logging
import matplotlib.pyplot as plt


logging.basicConfig(
    level=logging.INFO,  # 记录info及以上级别
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # 终端输出
        logging.FileHandler("image_compare.log")  # 文件输出
    ]
)


def compare_images_SSIM(image_path1, image_path2,threshold=0.95,debug = False,result_output_path=""):
    logging.info(f"SSIM开始对比图片：{image_path1}和{image_path2}")
    # 1. 读取图片并统一尺寸
    with open(image_path1, "rb") as f:
        img_data = np.frombuffer(f.read(), dtype=np.uint8)
        img1 = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
    with open(image_path2, "rb") as f:
        img_data = np.frombuffer(f.read(), dtype=np.uint8)
        img2 = cv2.imdecode(img_data, cv2.IMREAD_COLOR)    
    if img1 is None or img2 is None:
        logging.error(f"图片读取失败，请检查路径:{image_path1}和{image_path2}")
        raise ValueError("图片读取失败，请检查路径")
    
    # 自动调整至相同尺寸（取最小尺寸）
    h, w = min(img1.shape[0], img2.shape[0]), min(img1.shape[1], img2.shape[1])
    img1_resized = cv2.resize(img1, (w, h))
    img2_resized = cv2.resize(img2, (w, h))
    gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2GRAY)
    if debug:
        # 3. 计算SSIM值和差异图
        score, diff = ssim(gray1, gray2, full=True, win_size=11, data_range=255)
        diff = (diff * 255).astype("uint8")  # 转换为0-255范围
        
        # 5. 可视化结果
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        axes[0].imshow(cv2.cvtColor(img1_resized, cv2.COLOR_BGR2RGB))
        axes[0].set_title("Image 1")
        axes[0].axis('off')
        
        axes[1].imshow(cv2.cvtColor(img2_resized, cv2.COLOR_BGR2RGB))
        axes[1].set_title("Image 2")
        axes[1].axis('off')
        
        axes[2].imshow(diff, cmap='gray')
        axes[2].set_title(f"SSIM: {score:.4f}\nSimilar: {is_similar}")
        axes[2].axis('off')
        
        plt.tight_layout()
        plt.savefig('ssim_comparison_result.jpg', dpi=120)
        plt.show()
    else:
        # 3. 计算SSIM值和差异图
        score = ssim(gray1, gray2, full=False, win_size=11, data_range=255)
    is_similar = score >= threshold
    
    logging.info(f"SSIM对比结束：{image_path1}和{image_path2}，分数：{score},阈值:{threshold}")
    return score, is_similar

