import numpy as np
import os,glob
from PIL import Image, ImageDraw
from PIL import ImageFont
def draw_result(diff_cats,det_dir,diff_seg_page_ids,diff_rects,diff_text,output_dir):
    all_jpgs = glob.glob(os.path.join(det_dir, '*.jpg'))
    
    # 仅保留文件名是纯数字的文件
    numeric_jpgs = [
        f for f in all_jpgs 
        if os.path.basename(f).split('.')[0].isdigit()
    ]
    for page in numeric_jpgs:
        draw_page_id = os.path.basename(page).split('.')[0]
        pil_img = Image.open(page)
        draw = ImageDraw.Draw(pil_img)
        for i_diff, seg_page_ids in enumerate(diff_seg_page_ids):
            if diff_cats[i_diff] == 'equal': 
                   continue
            for i_seg, page_id in enumerate(seg_page_ids):
                if diff_cats[i_diff] == 'replace': 
                    color = 'orange'
                if diff_cats[i_diff] == 'delete': 
                    color = 'red'
                else: 
                    color = 'green'
                if page_id == draw_page_id :
                    # print(src_doc_tokens[src_diff_start_tids[i_diff]: (src_diff_end_tids+1)[i_diff]])
                    rect = diff_rects[i_diff][i_seg].tolist()
                    # print(i_diff, i_seg)
                    draw.rectangle(rect, outline=color, width = 3)
                    # 添加说明文字
                    text_position = (rect[0], rect[1] - 25)  # 在矩形框上方显示
                    font = ImageFont.truetype("arial.ttf", 25)
                    draw.text(text_position, diff_text[i_diff], fill=color,font=font)
        pil_img.save(os.path.join(output_dir,f'result_{draw_page_id}.jpg'))