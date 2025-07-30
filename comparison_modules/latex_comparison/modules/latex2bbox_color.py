import os
import re
import json
import shutil
import logging
import subprocess
import numpy as np
import fitz
import platform

from threading import Timer
from PIL import Image, ImageDraw
from ..modules.latex_processor import (
    normalize_latex,
    token_add_color_RGB,
    clean_latex
)
from ..modules.tokenize_latex.tokenize_latex import tokenize_latex


tabular_template = r"""
\documentclass[12pt]{article}
\usepackage[landscape]{geometry}
\usepackage{geometry}
\geometry{a<PaperSize>paper,scale=0.98}
\pagestyle{empty}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{amssymb}
\usepackage{upgreek}
\usepackage{amsmath}
\usepackage{xcolor}
\begin{document}
\makeatletter
\renewcommand*{\@textcolor}[3]{%%
  \protect\leavevmode
  \begingroup
    \color#1{#2}#3%%
  \endgroup
}
\makeatother
\begin{displaymath}
%s
\end{displaymath}
\end{document}
"""

formular_template = r"""
\documentclass[12pt]{article}
\usepackage[landscape]{geometry}
\usepackage{geometry}
\geometry{a<PaperSize>paper,scale=0.98}
\pagestyle{empty}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage{upgreek}
\usepackage{amssymb}
\usepackage{xcolor}
\begin{document}
\makeatletter
\renewcommand*{\@textcolor}[3]{%%
  \protect\leavevmode
  \begingroup
    \color#1{#2}#3%%
  \endgroup
}
\makeatother
\begin{displaymath}
%s
\end{displaymath}
\end{document}
"""


def run_cmd(cmd, timeout_sec=30):
    print(cmd)
    proc = subprocess.Popen(cmd, shell=True)
    kill_proc = lambda p: p.kill()
    timer = Timer(timeout_sec, kill_proc, [proc])
    try:
        timer.start()
        stdout,stderr = proc.communicate()
    finally:
        timer.cancel()


def convert_with_ghostscript(pdf_path, png_path, density=200):
    """
    Linux 专用 Ghostscript PDF 转 PNG 函数（简化版）

    参数:
        pdf_path (str): PDF 文件路径
        png_path (str): 输出 PNG 文件路径
        density (int): DPI 密度 (默认200)

    返回:
        bool: 转换成功返回 True，否则 False
    """
    try:
        # 1. 验证输入文件
        if not os.path.exists(pdf_path):
            logging.error(f"PDF 文件不存在: {pdf_path}")
            return False

        # 2. 创建输出目录
        os.makedirs(os.path.dirname(png_path), exist_ok=True)

        # 3. 构建 Ghostscript 命令
        gs_cmd = [
            "gs",
            "-dALLOWPSTRANSPARENCY",
            "-dPDFSTOPONERROR",
            "-dNOPAUSE",
            "-dBATCH",
            "-dQUIET",
            "-sDEVICE=png16m",
            f"-r{density}",
            "-dTextAlphaBits=4",
            "-dGraphicsAlphaBits=4",
            f"-sOutputFile={png_path}",
            pdf_path
        ]

        logging.info(f"执行 Ghostscript 命令: {' '.join(gs_cmd)}")

        # 4. 执行转换
        result = subprocess.run(
            gs_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        # 5. 验证输出文件
        if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
            logging.info(f"Ghostscript 转换成功: {pdf_path} → {png_path}")
            return True
        else:
            logging.warning("Ghostscript 转换完成但未生成有效文件")
            return False

    except subprocess.CalledProcessError as e:
        logging.error(f"Ghostscript 错误 ({e.returncode}):\n{e.stderr}")
        return False

    except FileNotFoundError:
        logging.error("Ghostscript (gs) 未安装或不在 PATH 中")
        logging.error("请安装: sudo apt install ghostscript")
        return False

    except Exception as e:
        logging.error(f"转换过程中发生意外错误: {str(e)}")
        return False
def convert_pdf2img(pdf_filename, png_filename):
    if platform.system() == 'Windows':
        cmd = "magick -density 200 -quality 100 %s %s"%(pdf_filename, png_filename)
        os.system(cmd)
    else:
        convert_with_ghostscript(pdf_filename,png_filename)


def crop_image(image_path, pad=8):
    img = Image.open(image_path).convert("L")
    img_data = np.asarray(img, dtype=np.uint8)
    nnz_inds = np.where(img_data!=255)
    if len(nnz_inds[0]) == 0:
        y_min = 0
        y_max = 10
        x_min = 0
        x_max = 10
    else:
        y_min = np.min(nnz_inds[0])
        y_max = np.max(nnz_inds[0])
        x_min = np.min(nnz_inds[1])
        x_max = np.max(nnz_inds[1])
        
    img = Image.open(image_path).convert("RGB").crop((x_min-pad, y_min-pad, x_max+pad, y_max+pad))
    img.save(image_path)
    
def extrac_bbox_from_color_image(image_path, color_list):
    img = Image.open(image_path).convert("RGB")
    W, H = img.size
    pixels = list(img.getdata())
    
    bbox_list = []
    for target_color in color_list:
        target_pixels = [ i for i, pixel in enumerate(pixels)if pixel == target_color ]
        x_list = []
        y_list = []
        for idx in target_pixels:
            x_list.append(idx % W)
            y_list.append(idx // W)
        try:
            y_min, y_max, x_min, x_max = min(y_list), max(y_list), min(x_list), max(x_list)
            bbox_list.append([x_min-1, y_min-1, x_max+1, y_max+1])

        except:
            bbox_list.append([])
            continue
        
    img = img.convert("L")
    img_bw = img.point(lambda x: 255 if x == 255 else 0, '1')
    img_bw.convert("RGB").save(image_path) 
    return bbox_list


def latex2bbox_color(input_arg):
    latex, basename, output_path, temp_dir, total_color_list = input_arg
    print("***********************" + basename+ "**************************")
    subset = output_path.split("\\")[-1]
    template = tabular_template if "tabular" in latex else formular_template
    output_bbox_path = os.path.join(output_path, 'bbox', basename+'.jsonl')
    output_vis_path = os.path.join(output_path, 'vis', basename+'.png')
    output_base_path = os.path.join(output_path, 'vis', basename+'_base.png')

    # if os.path.exists(output_bbox_path) and os.path.exists(output_vis_path) and os.path.exists(output_base_path):
    #     return
    try:
        # print('before_tokenize',latex)
        ret, new_latex = tokenize_latex(latex, middle_file=os.path.join(temp_dir, basename+'.txt'),subset=subset)
        # print('new_latex', new_latex)
        if not(ret and new_latex):
            log = f"ERROR, Tokenize latex failed: {basename}."
            # print(log)
            logging.info(log)
            new_latex = latex
        latex = normalize_latex(new_latex)
        # print("normalize_latex",latex)


        # print("after normalize",latex)
        # cry_latex = formular_template % re.sub(r'\\\(|\\\)|\\\[|\\\]', '', latex).strip()
        # print("cry_latex", cry_latex)
        token_list = []
        l_split = latex.strip().split(' ')
        color_list = total_color_list[0:len(l_split)]
        idx = 0
        while idx < len(l_split):
            l_split, idx, token_list = token_add_color_RGB(l_split, idx, token_list)

        rgb_latex = " ".join(l_split)
        for idx, color in enumerate(color_list):
            R, G, B = color
            rgb_latex = rgb_latex.replace(f"<color_{idx}>", f"{R},{G},{B}")

        if len(token_list) > 1300:
            paper_size = 3
        elif len(token_list) > 600:
            paper_size = 4
        else:
            paper_size = 5
        final_latex = formular_template.replace("<PaperSize>", str(paper_size)) % rgb_latex
        # print("final_latex",final_latex)
    except Exception as e:
        log = f"ERROR, Preprocess latex failed: {basename}; {e}."
        logging.info(log)
        return
    
    pre_name = basename+'_'+subset #output_path.replace('/', '_').replace('.','_') + '_' + basename
    tex_filename = os.path.join(temp_dir, pre_name+'.tex')
    log_filename = os.path.join(temp_dir, pre_name+'.log')
    aux_filename = os.path.join(temp_dir, pre_name+'.aux')
    
    with open(tex_filename, "w") as w: 
        print(final_latex, file=w)
    run_cmd(f"pdflatex -interaction=nonstopmode -output-directory={temp_dir} {tex_filename}") # >/dev/null")
    # try:
    #     os.remove(tex_filename)
    #     os.remove(log_filename)
    #     os.remove(aux_filename)
    # except:
    #     pass
    pdf_filename = tex_filename[:-4]+'.pdf'
    print('pdf_filename', pdf_filename)
    if not os.path.exists(pdf_filename):
        log = f"ERROR, Compile pdf failed: {pdf_filename}"
        logging.info(log)
    else:
        dpi = 300
        doc = fitz.open(pdf_filename)
        page = doc.load_page(0) 
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))  
        pil_img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples) 
        pil_img.save(output_base_path)
        convert_pdf2img(pdf_filename, output_base_path)
        # os.remove(pdf_filename)
        # print(os.listdir('output/temp_dir/test_cdm_gt'))
        crop_image(output_base_path)
        bbox_list = extrac_bbox_from_color_image(output_base_path, color_list)
        vis = Image.open(output_base_path)
        draw = ImageDraw.Draw(vis)

        with open(output_bbox_path, 'w') as f:
            for token, box in zip(token_list, bbox_list):
                item = {
                    "bbox": box,
                    "token": token
                }
                f.write(json.dumps(item)+'\n')

                if not box:
                    continue
                x_min, y_min, x_max, y_max = box
                draw.rectangle([x_min, y_min, x_max, y_max], fill=None, outline=(0,250,0), width=1)
                draw.text((x_min, y_min), token, (250,0,0))
            
        vis.save(output_vis_path)


def latex2bbox_color_simple(latex, basename, output_path, temp_dir, total_color_list):
    print("***********************" + basename + "**************************")
    template = tabular_template if "tabular" in latex else formular_template
    output_bbox_path = os.path.join(output_path, 'bbox', basename + '.jsonl')
    output_vis_path = os.path.join(output_path, 'vis', basename + '.png')
    output_base_path = os.path.join(output_path, 'vis', basename + '_base.png')

    try:
        # print(f'原始的latex：{latex}')
        latex = normalize_latex(latex)
        print(f'normalized后的的latex：{latex}')
        token_list = []
        l_split = latex.strip().split(' ')
        color_list = total_color_list[0:len(l_split)]
        idx = 0
        while idx < len(l_split):
            l_split, idx, token_list = token_add_color_RGB(l_split, idx, token_list)

        rgb_latex = " ".join(l_split)
        for idx, color in enumerate(color_list):
            R, G, B = color
            rgb_latex = rgb_latex.replace(f"<color_{idx}>", f"{R},{G},{B}")

        if len(token_list) > 1300:
            paper_size = 3
        elif len(token_list) > 600:
            paper_size = 4
        else:
            paper_size = 5
        final_latex = formular_template.replace("<PaperSize>", str(paper_size)) % rgb_latex
        # print("final_latex",final_latex)
    except Exception as e:
        log = f"ERROR, Preprocess latex failed: {basename}; {e}."
        print(log)
        logging.info(log)
        return

    tex_file_path = os.path.join(temp_dir, basename + '.tex')
    tex_filename = basename + '.tex'

    with open(tex_file_path, "w") as w:
        print(final_latex, file=w)
    run_cmd(f"pdflatex -interaction=nonstopmode -output-directory={temp_dir} {tex_filename}")  # >/dev/null")
    pdf_filename = tex_filename[:-4] + '.pdf'
    print('pdf_filename', pdf_filename)
    if not os.path.exists(os.path.join(temp_dir,pdf_filename)):
        log = f"ERROR, Compile pdf failed: {pdf_filename}"
        print(log)
        logging.info(log)
    else:
        dpi = 300
        doc = fitz.open(os.path.join(temp_dir,pdf_filename))
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
        pil_img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        pil_img.save(output_base_path)
        convert_pdf2img(os.path.join(temp_dir,pdf_filename), output_base_path)
        crop_image(output_base_path)
        bbox_list = extrac_bbox_from_color_image(output_base_path, color_list)
        vis = Image.open(output_base_path)
        draw = ImageDraw.Draw(vis)

        with open(output_bbox_path, 'w') as f:
            for token, box in zip(token_list, bbox_list):
                item = {
                    "bbox": box,
                    "token": token
                }
                f.write(json.dumps(item) + '\n')

                if not box:
                    continue
                x_min, y_min, x_max, y_max = box
                draw.rectangle([x_min, y_min, x_max, y_max], fill=None, outline=(0, 250, 0), width=1)
                draw.text((x_min, y_min), token, (250, 0, 0))

        vis.save(output_vis_path)
