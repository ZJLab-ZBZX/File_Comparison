import logging
from skimage.metrics import structural_similarity as ssim
import logging
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import torch.nn.functional as F


logging.basicConfig(
    level=logging.INFO,  # 记录info及以上级别
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # 终端输出
        logging.FileHandler("image_compare.log")  # 文件输出
    ]
)


def resnet_cosine_similarity(img_path1, img_path2,threshold=0.95):
    logging.info(f"余弦相似度开始对比图片：{img_path1}和{img_path2}")
    # 1. 加载预训练ResNet50模型（移除全连接层）
    model = models.resnet50(pretrained=True)
    model = torch.nn.Sequential(*list(model.children())[:-1])  # 移除最后一层分类层
    model.eval()  # 设为评估模式

    # 2. 定义图像预处理流程
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # 3. 加载并预处理图像
    def load_image(image_path):
        img = Image.open(image_path).convert('RGB')
        return preprocess(img).unsqueeze(0)  # 增加batch维度

    img1 = load_image(img_path1)
    img2 = load_image(img_path2)

    # 4. 提取特征向量
    with torch.no_grad():
        features1 = model(img1).flatten()  # 展平为1D向量 [2048]
        features2 = model(img2).flatten()

    # 5. 计算余弦相似度 [-1, 1]
    similarity = F.cosine_similarity(features1.unsqueeze(0), features2.unsqueeze(0), dim=1)
    score = similarity.item()
    is_similar = score >= threshold
    logging.info(f"余弦相似度对比结束：{img_path1}和{img_path2}，分数：{score},阈值:{threshold}")
    return score,is_similar
