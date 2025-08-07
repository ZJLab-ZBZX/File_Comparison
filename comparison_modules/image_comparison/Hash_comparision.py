from PIL import Image
import imagehash
import logging
logger = logging.getLogger("image_compare")

def compare_images_aHash(src_image_path, dst_image_path,threshold=5):
    hash1 = imagehash.average_hash(Image.open(src_image_path))
    hash2 = imagehash.average_hash(Image.open(dst_image_path))
    distance = hash1 - hash2  # 汉明距离
    is_similar = abs(distance) <= threshold
    logger.debug(f"aHash对比结束：{src_image_path}和{dst_image_path}，汉明距离：{distance},阈值:{threshold}")
    return distance, is_similar

def compare_images_dHash(src_image_path, dst_image_path,threshold=5):
    hash1 = imagehash.dhash(Image.open(src_image_path))
    hash2 = imagehash.dhash(Image.open(dst_image_path))
    distance = hash1 - hash2  # 汉明距离
    is_similar = abs(distance) <= threshold
    logger.debug(f"dHash对比结束：{src_image_path}和{dst_image_path}，汉明距离：{distance},阈值:{threshold}")
    return distance, is_similar

def compare_images_pHash(src_image_path, dst_image_path,threshold=5):
    hash1 = imagehash.phash(Image.open(src_image_path))
    hash2 = imagehash.phash(Image.open(dst_image_path))
    distance = hash1 - hash2  # 汉明距离
    is_similar = abs(distance) <= threshold
    logger.debug(f"dHash对比结束：{src_image_path}和{dst_image_path}，汉明距离：{distance},阈值:{threshold}")
    return distance, is_similar