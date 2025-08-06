
from utils.deal_text import rematch_string
import os
import utils.difflib_modified as difflib_modified
import numpy as np
import re
import copy

def process_result(res,src_tokens,dst_tokens):
    result = []
    for i in res:
        if i[0]=="equal":
            result.append(i)
        else:
            exclude_pattern = '.#[]()（）;；:：,，'
            if (len(src_tokens[i[1]:i[2]]) == 0 or len(''.join(src_tokens[i[1]:i[2]]).strip(exclude_pattern))==0) and (len(dst_tokens[i[3]:i[4]]) == 0 or len(''.join(dst_tokens[i[3]:i[4]]).strip(exclude_pattern) )==0):
                temp_i =list(i)
                temp_i[0] = "equal"
                result.append(tuple(temp_i))
            elif ''.join(src_tokens[i[1]:i[2]]).strip(exclude_pattern) ==''.join(dst_tokens[i[3]:i[4]]).strip(exclude_pattern) :
            
                temp_i =list(i)
                temp_i[0] = "equal"
                result.append(tuple(temp_i))
            elif len(src_tokens[i[1]:i[2]])==1 and len(dst_tokens[i[3]:i[4]])==1 and rematch_string(src_tokens[i[1]:i[2]][0],dst_tokens[i[3]:i[4]][0]):
                temp_i =list(i)
                temp_i[0] = "equal"
                result.append(tuple(temp_i))
            else:
                result.append(i)
    return result


def show_diff(src_tokens,dst_tokens,output_dir,is_processed=False,opcodes=None,name="diff.html"):
    os.makedirs(output_dir, exist_ok=True)
    html_diff = difflib_modified.HtmlDiff().make_file(
        fromlines=src_tokens, 
        tolines=dst_tokens,
        is_processed=is_processed,
        opcodes=opcodes,
        fromdesc="Original", 
        todesc="Modified",
            context=True,  # 显示上下文
            numlines=10     # 上下文行数
    )
    html_utf8 = html_diff.replace('charset=ISO-8859-1', 'charset=UTF-8')
    output = os.path.join(output_dir,name)
    with open(output, "w", encoding='utf-8') as f:
        f.write(html_utf8)


def write_diff(res,src_tokens,dst_tokens,output_dir):
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir,"compare.txt"), 'w', encoding='utf-8') as file:
        file.write(f"{res}")
    for i in res:
        if i[0]=="equal":
            continue
        if i[0]=="replace":
            with open(os.path.join(output_dir,"compare_replace.txt"), 'a', encoding='utf-8') as file:
                file.write(f"{i}初始{src_tokens[i[1]:i[2]]}修改{dst_tokens[i[3]:i[4]]}\n")
        elif i[0]=="insert":
            with open(os.path.join(output_dir,"compare_insert.txt"), 'a', encoding='utf-8') as file:
                file.write(f"{i}初始{src_tokens[i[1]:i[2]]}修改{dst_tokens[i[3]:i[4]]}\n")
        elif i[0]=="delete":
            with open(os.path.join(output_dir,"compare_delete.txt"), 'a', encoding='utf-8') as file:
                file.write(f"{i}初始{src_tokens[i[1]:i[2]]}修改{dst_tokens[i[3]:i[4]]}\n")

def join_tokens(tokens):
    def is_alphanumeric(token):
        return bool(re.match(r'^[a-zA-Z0-9]+$', token))
    # def is_table(token):
    #     return bool(re.match(r'!\[\]\(tables/[^)]+\)', token))
    # def is_figures(token):
    #     return bool(re.match(r'!\[\]\(figures/[^)]+\)', token))
    # def is_mf(token):
    #     return bool(re.match(r'\\\(.*?\\\)', token))
    if not len(tokens):
        return ''
    result = [tokens[0]]
    for i in range(1, len(tokens)):
        if is_alphanumeric(tokens[i-1]) or is_alphanumeric(tokens[i]):
            result.append(" ")
        result.append(tokens[i])
    return "".join(result)

# 差异转换为坐标格式
def locate_diff(doc_segs, doc_seg_tokens, doc_seg_token_spans, doc_rects, doc_seg_page_ids, doc_tokens, doc_token_is_sp,doc_token_rect_ids, diff_start_tids, diff_end_tids):
    diff_start_sids, diff_end_sids = doc_token_rect_ids[diff_start_tids], doc_token_rect_ids[diff_end_tids]
    doc_seg_min_tids = np.hstack([[0], np.cumsum([len(seg_tokens) for seg_tokens in doc_seg_tokens])[:-1]])
    diff_start_stids = diff_start_tids - doc_seg_min_tids[diff_start_sids] 
    diff_end_stids = diff_end_tids - doc_seg_min_tids[diff_end_sids]    
    diff_start_spans = [doc_seg_token_spans[diff_start_sids[i_diff]][stid] for i_diff, stid in enumerate(diff_start_stids)]
    diff_end_spans = [doc_seg_token_spans[diff_end_sids[i_diff]][stid] for i_diff, stid in enumerate(diff_end_stids)]
    diff_rects = copy.deepcopy([doc_rects[slice(*s)] for s in list(zip(diff_start_sids, diff_end_sids+1))])
    for i_diff, rects in enumerate(diff_rects):
        if len(rects):
            x1 = rects[0, 0] + (diff_start_spans[i_diff][0] / len(doc_segs[diff_start_sids[i_diff]])) * (rects[0, 2] - rects[0, 0])
            x2 = rects[-1, 0] + (diff_end_spans[i_diff][-1] / len(doc_segs[diff_end_sids[i_diff]])) * (rects[-1, 2] - rects[-1, 0])
            rects[0, 0], rects[-1, 2] = x1, x2
    diff_seg_page_ids = [doc_seg_page_ids[slice(*s)] for s in list(zip(diff_start_sids, diff_end_sids+1))]
    diff_texts = [join_tokens(doc_tokens[diff_start_tids[i_diff]: (diff_end_tids+1)[i_diff]]) for i_diff in range(len(diff_rects))]
    return diff_rects, diff_seg_page_ids, diff_texts



