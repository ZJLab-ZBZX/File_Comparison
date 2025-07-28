import re
import numpy as np
import json
import os
from utils.deal_text import clean_dollar_equations

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



def special_tokenize(tokens, token_is_sp,new_figures_map,new_mf_map,token_output):
    special_token = [index for index,value in enumerate(token_is_sp) if value == True]
    figures_index = [index for index in special_token if "![](figures/" in tokens[index]]
    tables_index = [index for index in special_token if "![](tables/" in tokens[index]]
    mf_index = [index for index in special_token if  "![](tables/" not in tokens[index] and "![](figures/" not in tokens[index]]   
    # new_figures_map,{原值1:新值1,原值2:新值2}
    figure_flag = 0
    for index in figures_index:
        if tokens[index] in new_figures_map:
            figure_flag = figure_flag + 1
            tokens[index] = new_figures_map[tokens[index]]
    if figure_flag!=len(new_figures_map):
        raise RuntimeError("处理图片token时，有token未被替换")
    # new_mf_map，{原索引1:新值1,原索引2:新值2}
    for key,value in new_mf_map.items():
        if key in mf_index:
            tokens[key] = value
    with open(token_output, 'w', encoding='utf-8') as f:
        for item in tokens:
            f.write(f"{item}\n")
    return tokens

def get_mf_token(tokens, token_is_sp,output_path):
    special_token = [index for index,value in enumerate(token_is_sp) if value == True]
    mf = [tokens[index] for index in special_token if  "![](tables/" not in tokens[index] and "![](figures/" not in tokens[index]]   
    mf_index = [index for index in special_token if  "![](tables/" not in tokens[index] and "![](figures/" not in tokens[index]]
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(mf, f)
    return mf_index

def convert_mf_token(mf_list,mf_index1,mf_index2,prefix1,prefix2,outputdir):
    number = 347262538
    new_mf1_map = {}
    new_mf2_map = {}
    for pairs in mf_list:
        for item in pairs:
            if prefix1 in item:
                index = mf_index1[int(item.split("_")[-1])]
                new_mf1_map[index] = "<mf" + str(number) +">"
            elif prefix2 in item:
                index = mf_index2[int(item.split("_")[-1])]
                new_mf2_map[index] = "<mf" + str(number) +">"
            else:
                raise RuntimeError(f"公式对比结果里未找到文件名称：{prefix1}或者{prefix2}")
        number = number + 1
    with open(os.path.join(outputdir, "compare_same_mf_globalIndex.json"), 'w', encoding='utf-8') as f:
        json.dump({
            prefix1: new_mf1_map,
            prefix2: new_mf2_map
        }, f, indent=4, ensure_ascii=False)
    return new_mf1_map,new_mf2_map


def tokenize_files(md_file_verison1,md_file_verison2,debug = False,output_dir=""):
    os.makedirs(output_dir,exist_ok=True)
    with open(md_file_verison1, 'r', encoding='utf-8') as f:
        version1_text = f.read() 
    version1_text = clean_dollar_equations(version1_text)
    version1_tokens, version1_spans, version1_token_is_sp = custom_tokenize(version1_text)
    with open(md_file_verison2, 'r', encoding='utf-8') as f:
        version2_text = f.read()
    version2_text = clean_dollar_equations(version2_text)
    version2_tokens, version2_spans, version2_token_is_sp = custom_tokenize(version2_text)
    if debug:
        with open(os.path.join(output_dir,os.path.splitext(os.path.basename(md_file_verison1))[0]+"_token.txt"), 'w', encoding='utf-8') as f:
            for item in version1_tokens:
                f.write(f"{item}\n")
        with open(os.path.join(output_dir,os.path.splitext(os.path.basename(md_file_verison2))[0]+"_token.txt"), 'w', encoding='utf-8') as f:
            for item in version2_tokens:
                f.write(f"{item}\n")
    return version1_tokens, version1_spans, version1_token_is_sp,version2_tokens, version2_spans, version2_token_is_sp