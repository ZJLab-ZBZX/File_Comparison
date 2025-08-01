# -*- coding: utf-8 -*-
"""
Created on Tue Apr 15 11:20:24 2025

@author: ZJ
"""

from datetime import datetime
import re, subprocess, os, json
import os, glob, requests, argparse
import cv2, time, base64
from multiprocessing import Pool
from PIL import Image
from threading import Timer
import fitz, re, random
import numpy as np
import subprocess, json, shutil, signal
import piexif
import platform, tempfile
from pathlib import Path
import traceback
import logging
from .logger import setup_logger


logger = setup_logger(__name__)
formular_template = r"""
    \documentclass[12pt]{article}
    \usepackage[landscape]{geometry}
    \usepackage{geometry}
    \geometry{a4paper,scale=0.98}
    \pagestyle{empty}
    \usepackage{booktabs}
    \usepackage{amsmath}
    \usepackage{mathtools}
    \usepackage{stmaryrd}
    \usepackage{upgreek}
    \usepackage{amssymb}
    \usepackage{xcolor}
    \begin{document}
    \makeatletter
    \renewcommand*{\@textcolor}[3]{
            %%\protect\leavevmode
            \begingroup
            \color#1{#2}#3%%
            \endgroup
            }
    \makeatother
    \begin{align*}
    %s
    \end{align*}
    \end{document}
    """
    
def combine_images_vertically(img1, img2):
    min_height = min(img1.height, img2.height)
    def resize_to_target(img, target_height):
        ratio = target_height / img.height
        new_width = int(img.width * ratio)
        return img.resize((new_width, target_height), Image.Resampling.LANCZOS)
    img1_resized = resize_to_target(img1, min_height)
    img2_resized = resize_to_target(img2, min_height)
    max_width = max(img1_resized.width, img2_resized.width)
    total_height = img1_resized.height + img2_resized.height
    combined = Image.new('RGB', (max_width, total_height), (255, 255, 255))
    combined.paste(img1_resized, (0, 0))  # 顶部图片
    combined.paste(img2_resized, (0, img1_resized.height))  # 底部图片
    return combined

def crop_image(pil_img, pad=8):
    # pil_img = Image.open(image_path).convert("L")
    img_data = np.asarray(pil_img, dtype=np.uint8)
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
    cropped_img = pil_img.crop((x_min-pad, y_min-pad, x_max+pad, y_max+pad))
    return cropped_img


def write_passed_image(target_dir,index, latex):
    file_key = os.path.basename(target_dir)
    jsonl_path = os.path.join(target_dir, "passed.jsonl")
    try:
        json_content = {file_key + "_"+str(index): latex}
        # 以追加模式打开文件（自动创建不存在的文件）
        with open(jsonl_path, 'a', encoding='utf-8') as f:
            json_line = json.dumps(json_content, ensure_ascii=False)
            f.write(json_line + '\n')

    except Exception as e:
        logger.error(f"写passed.jsonl文件失败: {str(e)}")

def write_failed_image(target_dir,index, latex):
    logger.info(f"第{index}个公式写入failed.jsonl")
    file_key = os.path.basename(target_dir)
    jsonl_path = os.path.join(target_dir, "failed.jsonl")
    try:
        json_content = {file_key+"_"+str(index): latex}
        # 以追加模式打开文件（自动创建不存在的文件）
        with open(jsonl_path, 'a', encoding='utf-8') as f:
            json_line = json.dumps(json_content, ensure_ascii=False)
            f.write(json_line + '\n')

    except Exception as e:
        logger.error(f"写入failed.jsonl失败: {str(e)}")


def run_cmd(command, timeout=10):
    class TimeoutError(Exception):
        pass
    def timeout_handler(signum, frame):
        raise TimeoutError("Command execution timed out.")
    # 设置信号处理函数和超时定时器
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    # 启动子进程，并创建新的进程组（仅Unix-like系统有效）
    proc = subprocess.Popen(
        command,
        shell=True,
        preexec_fn=os.setsid,  # 创建新进程组
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        stdout, stderr = proc.communicate()  # 等待进程完成
        # print("Command executed successfully.")
        # print("Output:", stdout.decode())
        return_code = proc.returncode
    except TimeoutError:
        print(f"Command timed out after {timeout} seconds. Terminating...")
        # 终止整个进程组，确保所有子进程被终止
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        stdout, stderr = proc.communicate()  # 清理进程资源
        return_code = -1
    finally:
        signal.alarm(0)  # 取消定时器

    return stdout, stderr
 
    
def convert_image(pdf_path, dpi=300, i_page=0):
    doc = fitz.open(pdf_path)
    page = doc.load_page(i_page) 
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))  
    pil_img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)  
    return pil_img


def read_text_from_image(image_path):
    pil_img = Image.open(image_path)
    exif_data = pil_img.info.get('exif')    
    if not exif_data:
        return None   
    exif_dict = piexif.load(exif_data)
    user_comment = exif_dict.get('Exif', {}).get(piexif.ExifIFD.UserComment, b'')   
    if not user_comment:
        return None    
    # 提取编码标识和内容
    encoding = user_comment[:8].decode('ascii', errors='ignore').strip('\x00')
    content = user_comment[8:]    
    if encoding == 'UNICODE':
        return content.decode('utf-16le')
    else:  # 回退到UTF-8解码
        return content.decode('utf-8', errors='replace')


def normalize_latex(latex_code):
    logger.debug(f"开始规范化LaTeX表达式 {latex_code}")
    latex_code = re.sub(r'\\begin{(equation|split|align|alignedat|alignat|eqnarray)\*?}(.+?)\\end{\1\*?}', r'\\begin{aligned}\2\\end{aligned}', latex_code, flags=re.S)
    latex_code = re.sub(r'\\begin{(smallmatrix)\*?}(.+?)\\end{\1\*?}', r'\\begin{matrix}\2\\end{matrix}', latex_code, flags=re.S)
    try:
        with tempfile.NamedTemporaryFile(dir="./temp/", delete=False) as temp_file:
            temp_file.write(latex_code.encode())  # 写入数据
            temp_file_path = Path(temp_file.name)
            js_path = Path(
                "/File_Comparison/comparison_modules/latex_comparison/modules/tokenize_latex/preprocess_formula.js")
            if not js_path.exists():
                raise FileNotFoundError(f"JavaScript处理脚本不存在: {js_path}")
            if platform.system() == 'Windows':
                cmd = f'type "{temp_file_path}" | node "{js_path.resolve()}" normalize'
            else:
                cmd = f'cat "{temp_file_path}" | node "{js_path.resolve()}" normalize'
            logger.info(f"执行外部命令: {cmd}")


        #ret = subprocess.call(cmd, shell=True)
        result = subprocess.run(cmd,
                                    shell=True,
                                    #check=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE
                                    )
        output =  result.stdout.decode('utf-8', errors='replace')
        error = result.stderr.decode('utf-8', errors='replace')
        os.remove(temp_file_path)
        if error:
            logger.warning(f"Node.js错误输出: {error[:200] + '...' if len(error) > 200 else error}")
        logger.info(f"LaTeX规范化成功")
        return error, output
    except Exception as gen_ex:
        logger.critical(f"意外错误: {gen_ex}", exc_info=True)
        # 记录详细的异常堆栈
        tb = traceback.format_exc()
        logger.error(f"完整堆栈跟踪:\n{tb}")
        return "未知错误:", ""

def handle_latex(file_name,latex_code,index):
    logger.info(f"处理第{index}个公式:{latex_code}")
    output_dir = os.path.dirname(file_name)
    if latex_code is None:
        logger.error(f"处理公式失败 [{index}]: 公式为空 ")
        return False
    try:
        if latex_code.startswith(r'\[') and latex_code.endswith(r'\]'):
            latex_code = latex_code[2:-2]
        elif latex_code.startswith(r'\(') and latex_code.endswith(r'\)'):
            latex_code = latex_code[2:-2]
        elif latex_code.startswith('$') and latex_code.endswith('$'):
            latex_code = latex_code[1:-1]
        latex_code = latex_code.replace('\n', ' ').strip()
        latex_code = re.sub(r'@', r'{ \\text {嚻} }', latex_code)
        for i in range(100):
            # print('latex_code', latex_code)
            error, normalized_latex = normalize_latex(latex_code)
            if 'parseerror' in error.lower():
                if 'rawMessage: \'Undefined control sequence: ' in error:
                    uc = error.split('rawMessage: \'Undefined control sequence: ')[1].split('\' }')[0]
                    print('uc', uc)
                    if uc[2:].isalpha():
                        latex_code = re.sub(rf'{uc}(?=[^a-zA-Z]|$)', rf'{{ \\text {{欃亹{uc[2:]}}} }}', latex_code)
                    else:
                        break
                else:
                    break
            else:
                break

        error = '\n'.join([l for l in error.split('\n') if not l.startswith('LaTeX-incompatible input and strict mode is set to \'warn\':')])
        if len(error) > 0:
            normalized_latex = ''
            logger.info(f"第{index}个公式katex parse error: {latex_code}")
            write_failed_image(output_dir, index, latex_code)
        else:
            normalized_latex = re.sub(r'{\s*\\text\s*{欃亹([^}]+?)}\s*}', r'\\\1', normalized_latex)
            normalized_latex = re.sub(r'{\s*\\text\s*{嚻}\s*}', r'@', normalized_latex)
            write_passed_image(output_dir, index, normalized_latex)
        return True
    except Exception as e:
        logger.error(f"第{index}个公式normalize失败: {str(e)}")
        logger.exception("完整异常信息:")
        return False


def compile_latex(latex_code, temp_dir='temp'):
    compile_dir = os.path.join(temp_dir, '{}_{}'.format(os.getpid(), datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')))
    if os.path.exists(compile_dir):
        shutil.rmtree(compile_dir)
    os.makedirs(compile_dir, exist_ok=True)
    tex_filename = os.path.join(compile_dir, 'temp.tex')
    final_latex = formular_template % latex_code
    with open(tex_filename, "w") as w:  
        print(final_latex, file=w)
    stdout, stderr = run_cmd(f"pdflatex -interaction=nonstopmode -output-directory={compile_dir} {tex_filename}")
    if os.path.exists(tex_filename.replace('.tex', '.pdf')):
        error = ''
    else:
        error = stdout.decode('utf-8', errors='replace')
    shutil.rmtree(compile_dir)
    return error


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--img_dir', type=str, default='xiziData')
    args = parser.parse_args()
    img_names = [name for name in glob.glob(os.path.join(args.img_dir, '**/*'), recursive=True) 
                 if name.lower().endswith(('.jpg', '.png')) and 'mf' in name]
    print("size",len(img_names))
    pool = Pool(1)
    for i, img_name in enumerate(img_names):
        print(i, len(img_names))
        #handle_latex(img_name)
        pool.apply_async(handle_latex, args=(img_name,))
    pool.close()
    pool.join()
    # parser.add_argument('--result_dir', type=str, default='../DataPrep4LLM_Algos/output')
    
    # args = parser.parse_args()
    
    # with open(os.path.join(args.result_dir, 'result.json'), 'r', encoding='utf-8') as f:
    #     results = json.load(f)
    # for result in results:
    #     error, normalized_latex = handle_latex(result['pred'])
    #     print(error, normalized_latex)
    
