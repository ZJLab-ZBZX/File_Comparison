# -*- coding: utf-8 -*-
"""
Created on Wed Jul  2 14:11:10 2025

@author: ZZL
"""

import re
import numpy as np
from difflib_new import SequenceMatcher
import difflib_new
import os
import shutil
import logging
import traceback
from image_compare import compare_image_list
import json


logging.basicConfig(
    level=logging.INFO,  # 记录info及以上级别
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # 终端输出
        logging.FileHandler("diff.log")  # 文件输出
    ]
)

def clean_dollar_equations(text):
    # text = r'bb $\n\alpha $$\beta\$$$\theta$\$$$ccc$$'
    text = np.array(list(text), object)
    is_dollar = text == '$'
    is_backslash =  text == '\\'
    is_dollar = ~np.hstack([True, is_backslash[:-1]]) * is_dollar
    is_start = True
    is_first = True
    has_second = False
    repl = []
    for j in is_dollar.nonzero()[0]:
        if is_start and is_first:
            has_second = text[j+1] == '$'
            if has_second:
                repl.append('\[')
                is_first = False           
            else:
                repl.append('\(')
                is_start = False
        elif is_start:
            repl.append('')
            is_first = True
            is_start = False
        elif not is_start and is_first:
            if has_second:
                repl.append('\]')
                is_first = False 
            else: 
                repl.append('\)')
                is_start = True          
        else:
            repl.append('')
            is_first = True
            is_start = True
    replaced = text.copy()
    replaced[is_dollar] = repl 
    replaced = ''.join(replaced)
    return replaced
       
 
def custom_tokenize(text, abandon=r'[\s]+'):  
    # 优先匹配特殊模式 ![](tables/任意字符) 、![](figures/任意字符) 、\[任意字符\]、\(任意字符\)
    special_pattern = r'!\[\]\(tables/[^)]+\)|!\[\]\(figures/[^)]+\)|\\\[.*?\\\]|\\\(.*?\\\)'

    # 先找到所有符合特殊模式的部分
    matches = list(re.finditer(special_pattern, text))
    
    tokens = []
    spans = []
    token_is_sp = []
    
    # 处理符合特殊模式的词
    for m in matches:
        word = m.group()
        tokens.append(word)  # 将特殊模式作为一个词保留
        spans.append(m.span())
        token_is_sp.append(True)
    
    # 在这里，我们记录已匹配部分的结束位置
    last_end = 0
    # 将文本切割为非特殊模式部分
    for m in matches:
        # 添加特殊模式前的文本
        if m.start() > last_end:
            non_special_text = text[last_end:m.start()]
            # 对非特殊模式部分进行原有的分词处理
            non_special_matches = list(re.finditer(r'[a-zA-Z0-9À-ÿ]+|[^a-zA-Z0-9À-ÿ]+', non_special_text))
            for nm in non_special_matches:
                word = nm.group()
                if re.match(r'[a-zA-Z0-9À-ÿ]+', word):
                    tokens.append(word)
                    spans.append((nm.start() + last_end, nm.end() + last_end))
                    token_is_sp.append(False)
                else:
                    tokens.extend(list(word))
                    spans.extend([(i + last_end, i + 1 + last_end) for i in range(nm.start(), nm.end())])
                    token_is_sp.extend([False]*len(word))
        last_end = m.end()
    
    # 处理剩余的文本（在最后一个匹配之后）
    if last_end < len(text):
        remaining_text = text[last_end:]
        remaining_matches = list(re.finditer(r'[a-zA-Z0-9À-ÿ]+|[^a-zA-Z0-9À-ÿ]+', remaining_text))
        for nm in remaining_matches:
            word = nm.group()
            if re.match(r'[a-zA-Z0-9À-ÿ]+', word):
                tokens.append(word)
                spans.append((nm.start() + last_end, nm.end() + last_end))
                token_is_sp.append(False)
            else:
                tokens.extend(list(word))
                spans.extend([(i + last_end, i + 1 + last_end) for i in range(nm.start(), nm.end())])
                token_is_sp.extend([False]*len(word))

    # 删除空白字符
    inds = list(map(lambda x: not re.match(abandon, x), tokens))
    tokens = np.array(tokens, object)[inds]
    spans = np.array(spans, object)[inds]
    token_is_sp = np.array(token_is_sp, bool)[inds]
    inds = sorted(np.arange(len(spans)), key=lambda x: spans[x][0])
    tokens = tokens[inds].tolist()
    spans = spans[inds].tolist()
    token_is_sp = token_is_sp[inds].tolist()
    return tokens, spans, token_is_sp


def extend_lists(ll):
    l = [e for l in ll for e in l]
    return l

def show_diff(init_tokens,version2_tokens,is_processed=False,opcodes=None,output="diff.html"):
    html_diff = difflib_new.HtmlDiff().make_file(
        fromlines=init_tokens, 
        tolines=version2_tokens,
        is_processed=is_processed,
        opcodes=opcodes,
        fromdesc="Original", 
        todesc="Modified",
            context=True,  # 显示上下文
            numlines=10     # 上下文行数
    )
    html_utf8 = html_diff.replace('charset=ISO-8859-1', 'charset=UTF-8')
    with open(output, "w", encoding='utf-8') as f:
        f.write(html_utf8)


def write_diff(res,init_tokens,version2_tokens,output_dir):
    with open(os.path.join(output_dir,"compare.txt"), 'w', encoding='utf-8') as file:
        file.write(f"{res}")
    for i in res:
        if i[0]=="equal":
            continue
        if i[0]=="replace":
            with open(os.path.join(output_dir,"compare_replace.txt"), 'a', encoding='utf-8') as file:
                file.write(f"{i}初始{init_tokens[i[1]:i[2]]}修改{version2_tokens[i[3]:i[4]]}\n")
        elif i[0]=="insert":
            with open(os.path.join(output_dir,"compare_insert.txt"), 'a', encoding='utf-8') as file:
                file.write(f"{i}初始{init_tokens[i[1]:i[2]]}修改{version2_tokens[i[3]:i[4]]}\n")
        elif i[0]=="delete":
            with open(os.path.join(output_dir,"compare_delete.txt"), 'a', encoding='utf-8') as file:
                file.write(f"{i}初始{init_tokens[i[1]:i[2]]}修改{version2_tokens[i[3]:i[4]]}\n")




def deal_string(str1, str2):
    # 字符串只有一个字符时，暂不处理
    if len(str1) <=1 or len(str2) <=1 :
        return False
    matcher = SequenceMatcher(None, str1, str2)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == 'equal':
            continue
        elif op == 'replace':
            if not re.fullmatch(r'[o0Il]*', str1[i1:i2]) or not re.fullmatch(r'[o0Il]*', str2[j1:j2]):
                return False
        elif op == 'delete':
            if not re.fullmatch(r'r*', str1[i1:i2]):
                return False
        elif op == 'insert':
            if not re.fullmatch(r'r*', str2[j1:j2]):
                return False
    return True


def process_result(res,init_tokens, init_spans, init_token_is_sp,version2_tokens, version2_spans, version2_token_is_sp):
    result = []
    for i in res:
        if i[0]=="equal":
            result.append(i)
        else:
            exclude_pattern = '.#[]()（）;；:：,，'
            if (len(init_tokens[i[1]:i[2]]) == 0 or len(''.join(init_tokens[i[1]:i[2]]).strip(exclude_pattern))==0) and (len(version2_tokens[i[3]:i[4]]) == 0 or len(''.join(version2_tokens[i[3]:i[4]]).strip(exclude_pattern) )==0):
                temp_i =list(i)
                temp_i[0] = "equal"
                result.append(tuple(temp_i))
            elif ''.join(init_tokens[i[1]:i[2]]).strip(exclude_pattern) ==''.join(version2_tokens[i[3]:i[4]]).strip(exclude_pattern) :
            
                temp_i =list(i)
                temp_i[0] = "equal"
                result.append(tuple(temp_i))
            elif len(init_tokens[i[1]:i[2]])==1 and len(version2_tokens[i[3]:i[4]])==1 and deal_string(init_tokens[i[1]:i[2]][0],version2_tokens[i[3]:i[4]][0]):
                temp_i =list(i)
                temp_i[0] = "equal"
                result.append(tuple(temp_i))
            else:
                result.append(i)
    return result

def special_tokenize(tokens, token_is_sp,new_figures_map):
    special_token = [index for index,value in enumerate(token_is_sp) if value == True]
    special_figures = [index for index in special_token if "![](figures/" in tokens[index]]
    tables = [index for index in special_token if "![](tables/" in tokens[index]]
    others = [index for index in special_token if  "![](tables/" not in tokens[index] and "![](figures/" not in tokens[index]]   
    if len(special_figures) != len(new_figures_map):
        logging.error()
    # new_figures为字典,{原值:新值}
    for index in special_figures:
        if tokens[index] in new_figures_map:
            tokens[index] = new_figures_map[tokens[index]]
    return tokens

def get_mf_token(tokens, token_is_sp,output_path):
    special_token = [index for index,value in enumerate(token_is_sp) if value == True]
    others = [tokens[index] for index in special_token if  "![](tables/" not in tokens[index] and "![](figures/" not in tokens[index]]   
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(others, f)


def find_files(version_dir):
    md_file = ""
    images_dir = ""
    with os.scandir(version_dir) as entries:
        for entry in entries:
            if entry.is_file() and entry.name == os.path.basename(version_dir)+".md":
                md_file = entry.path
            if entry.is_dir() and entry.name == "figures":
                images_dir = entry.path
    if md_file != "" and images_dir != "":
        return md_file,images_dir
    else:
        logging.error(f"文件夹下文件不完整，{version_dir}")
        raise FileNotFoundError(f"文件夹下文件不完整，{version_dir}")

def compare_files(version1_dir,version2_dir,output_dir):
    logging.info(f"开始对比：{version1_dir}和{version2_dir}")
    try:
        md_file_verison1,images_dir_version1 = find_files(version1_dir)
        md_file_verison2,images_dir_version2 = find_files(version2_dir)
        with open(md_file_verison1, 'r', encoding='utf-8') as f:
            version1_text = f.read() 
        version1_text = clean_dollar_equations(version1_text)
        version1_tokens, version1_spans, version1_token_is_sp = custom_tokenize(version1_text)
        with open(md_file_verison2, 'r', encoding='utf-8') as f:
            version2_text = f.read()
        version2_text = clean_dollar_equations(version2_text)
        version2_tokens, version2_spans, version2_token_is_sp = custom_tokenize(version2_text)
        with open(os.path.join(output_dir,os.path.basename(version1_dir)+"_token.txt"), 'w', encoding='utf-8') as f:
            for item in version1_tokens:
                f.write(f"{item}\n")
        with open(os.path.join(output_dir,os.path.basename(version2_dir)+"_token.txt"), 'w', encoding='utf-8') as f:
            for item in version2_tokens:
                f.write(f"{item}\n")
        new_image1_map,new_image2_map = compare_image_list(images_dir_version1,images_dir_version2,os.path.join(output_dir,"SSIM_result"))
        get_mf_token(version1_tokens, version1_token_is_sp,output_path = os.path.join(output_dir,os.path.basename(version1_dir).split(".")[0]+"_mf.txt"))
        get_mf_token(version2_tokens, version2_token_is_sp,output_path = os.path.join(output_dir,os.path.basename(version2_dir).split(".")[0]+"_mf.txt"))
        version1_new_token = special_tokenize(version1_tokens, version1_token_is_sp,new_image1_map)
        version2_new_token = special_tokenize(version2_tokens, version2_token_is_sp,new_image2_map)
        with open(os.path.join(output_dir,os.path.basename(version1_dir)+"_new_token.txt"), 'w', encoding='utf-8') as f:
            for item in version1_new_token:
                f.write(f"{item}\n")
        with open(os.path.join(output_dir,os.path.basename(version2_dir)+"_new_token.txt"), 'w', encoding='utf-8') as f:
            for item in version2_new_token:
                f.write(f"{item}\n")
        matcher = SequenceMatcher(None, version1_tokens, version2_tokens)
        res = list(matcher.get_opcodes())
        diff_dir = os.path.join(output_dir,"diff中间结果")
        os.makedirs(diff_dir, exist_ok=True)
        show_diff(version1_tokens,version2_tokens,is_processed=True,opcodes=res,output=os.path.join(diff_dir,"diff.html"))
        write_diff(res,version1_tokens,version2_tokens,diff_dir)
        result_dir = os.path.join(output_dir,"后处理结果")
        os.makedirs(result_dir, exist_ok=True)
        result = process_result(res,version1_tokens, version1_spans, version1_token_is_sp,version2_tokens, version2_spans, version2_token_is_sp)
        write_diff(result,version1_tokens,version2_tokens,result_dir)
        show_diff(version1_tokens,version2_tokens,is_processed=True,opcodes=result,output=os.path.join(result_dir,"diff_processed.html"))
        shutil.copy2(os.path.join(result_dir,"diff_processed.html"),os.path.join(output_dir,"diff_processed.html"))
    except Exception as e:
        tb_str = traceback.format_exc()  # 返回 Traceback 字符串
        logging.error(f"对比失败：{version1_dir}和{version2_dir}: {e}\n{tb_str}")
        return False
    logging.info(f"对比结束，结果保存在{output_dir}")




# root_dir = "./"
# subfolders = []
# # 列出所有待对比的文件夹
# for entry in os.listdir(root_dir):
#     print(entry)
#     entry_path = os.path.join(root_dir, entry)
#     if os.path.isdir(entry_path):
#         subfolders.append(entry_path)
#     print(subfolders)
# for subfolder in subfolders:
#     # 每个子文件夹下，有多个不同版本的文件夹
#     versions = os.listdir(subfolder)
#     if len(versions) != 2:
#         logging.warning(f"{subfolder}文件夹下有{len(versions)}个版本")
#         continue
#     sorted_versions = sorted(versions)

#     version_path1 = os.path.exists(os.path.join(os.path.join(subfolder, sorted_versions[0]),sorted_versions[0]+'.md'))
#     version_path2 = os.path.exists(os.path.join(os.path.join(subfolder, sorted_versions[1]),sorted_versions[1]+'.md'))
#     if os.path.exists(version_path1) and os.path.exists(version_path2):
#         version1_file = version_path1
#         version2_file = version_path2
#         compare_files(version1_file,version2_file,output_dir=subfolder)
#     else:
#         logging.error(f"{subfolder}文件夹下有不存在对应的md:{versions}")
#         continue
            


version1_dir = "Print_of_CPS1000_W_中英对照_内部.pdf"
version2_dir = "Print_of_CPS1000_V_中英对照_内部.pdf"
output_dir = "./"
compare_files(version1_dir,version2_dir,output_dir)




