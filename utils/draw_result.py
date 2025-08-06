import os,glob
from PIL import Image, ImageDraw
from PIL import ImageFont
import traceback
import logging

# 创建子Logger（继承自主Logger命名空间）
module_logger = logging.getLogger("main_logger.sub_module")
def draw_result(diff_cats,det_dir,diff_seg_page_ids,diff_rects,diff_text,output_dir):
    all_jpgs = glob.glob(os.path.join(det_dir, '*.jpg'))
    
    # 仅保留文件名是纯数字的文件
    numeric_jpgs = [
        f for f in all_jpgs 
        if os.path.basename(f).split('.')[0].isdigit()
    ]
    for page in numeric_jpgs:
        try:
            draw_page_id = os.path.basename(page).split('.')[0]
            pil_img = Image.open(page)
            draw = ImageDraw.Draw(pil_img)
            for i_diff, seg_page_ids in enumerate(diff_seg_page_ids):
                if diff_cats[i_diff] == 'equal': 
                    continue
                for i_seg, page_id in enumerate(seg_page_ids):
                    if diff_cats[i_diff] == 'replace': 
                        color = 'orange'
                    elif diff_cats[i_diff] == 'delete': 
                        color = 'red'
                    else: 
                        color = 'green'
                    if page_id == draw_page_id :
                        # print(src_doc_tokens[src_diff_start_tids[i_diff]: (src_diff_end_tids+1)[i_diff]])
                        rect = diff_rects[i_diff][i_seg].tolist()
                        # print(i_diff, i_seg)
                        if rect[0]==rect[2]:
                            rect[2] = rect[0]+1
                        if rect[0] > rect[2]:
                            rect[0], rect[2] = rect[2], rect[0]
                        if rect[1] > rect[3]:
                            rect[1], rect[3] = rect[3], rect[1]
                        draw.rectangle(rect, outline=color, width = 3)
                        # 添加说明文字
                        text_position = (rect[0], rect[1] - 35)  # 在矩形框上方显示
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        font_path = os.path.join(current_dir, "..","utils", "simhei.ttf")
                        font = ImageFont.truetype(font_path, 30, encoding="utf-8") 
                        draw.text(text_position, diff_text[i_diff], fill=color,font=font)
            pil_img.save(os.path.join(output_dir,f'result_{draw_page_id}.jpg'))
        except Exception as e:
            tb_str = traceback.format_exc()  # 返回 Traceback 字符串
            module_logger.error(f"绘制图片结果失败：{page}: {e}\n{tb_str}")