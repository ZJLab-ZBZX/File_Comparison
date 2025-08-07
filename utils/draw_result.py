import os, glob
from PIL import Image, ImageDraw
from PIL import ImageFont
import traceback
import logging
from multiprocessing import Pool, Manager
from functools import partial

# 创建子Logger（继承自主Logger命名空间）
module_logger = logging.getLogger("main_logger.sub_module")

def _process_single_page(args):
    """处理单页图片的内部函数"""
    page, diff_cats, diff_seg_page_ids, diff_rects, diff_text, output_dir = args
    try:
        draw_page_id = os.path.basename(page).split('.')[0]
        with Image.open(page) as pil_img:
            draw = ImageDraw.Draw(pil_img)
            for i_diff, seg_page_ids in enumerate(diff_seg_page_ids):
                if diff_cats[i_diff] == 'equal':
                    continue
                for i_seg, page_id in enumerate(seg_page_ids):
                    if page_id == draw_page_id:
                        color = 'orange' if diff_cats[i_diff] == 'replace' else \
                                'red' if diff_cats[i_diff] == 'delete' else 'green'
                        rect = diff_rects[i_diff][i_seg].tolist()
                        # 矩形坐标修正
                        rect[2] = rect[0]+1 if rect[0]==rect[2] else max(rect[0], rect[2])
                        rect[3] = max(rect[1], rect[3])
                        
                        draw.rectangle(rect, outline=color, width=3)
                        # 添加说明文字
                        text_position = (rect[0], rect[1] - 35)
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        font_path = os.path.join(current_dir, "..","utils", "simhei.ttf")
                        font = ImageFont.truetype(font_path, 30, encoding="utf-8")
                        draw.text(text_position, diff_text[i_diff], fill=color, font=font)
            
            output_path = os.path.join(output_dir, f'result_{draw_page_id}.jpg')
            pil_img.save(output_path)
            return True
    except Exception as e:
        tb_str = traceback.format_exc()
        module_logger.error(f"绘制图片结果失败：{page}: {e}\n{tb_str}")
        return False

def draw_result(diff_cats, det_dir, diff_seg_page_ids, diff_rects, diff_text, output_dir, processes=32):
    all_jpgs = glob.glob(os.path.join(det_dir, '*.jpg'))
    numeric_jpgs = [f for f in all_jpgs if os.path.basename(f).split('.')[0].isdigit()]
    
    # 按页码排序
    numeric_jpgs.sort(key=lambda x: int(os.path.basename(x).split('.')[0]))
    
    # 准备多进程参数
    tasks = [(page, diff_cats, diff_seg_page_ids, diff_rects, diff_text, output_dir) 
             for page in numeric_jpgs]
    
    # 使用多进程池
    with Pool(processes=processes) as pool:
        results = pool.map(_process_single_page, tasks)
    
    # 检查结果
    if not all(results):
        module_logger.warning("部分页面绘制失败，请检查日志")