import re
import numpy as np
import json
import os
import glob, os
import json, re

# 文本tokenize
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


# 按照检测框tokenize
def tokenize_det_result(det_dir, page_id, ocr_categories,filter_categories):
    # 1. 加载.npy文件并过滤需要的类别
    label_name = os.path.join(det_dir, '{}.npy'.format(page_id))
    layout_dets = [det for det in np.load(label_name, allow_pickle=True).tolist()['layout_dets'] if ocr_categories[det['category_id']] in filter_categories]   
    # 这里的seg并不是line seg，即原始检测框，而是ptmf，即mf_split之后的检测框
    # 2. 提取文本段和矩形框
    det_segs = np.array(extend_lists([det['ptrmfr_texts'] if ocr_categories[det['category_id']] not in ['figure', 'table']
                                      else ['![]({})'.format(det['url'])] for det in layout_dets]), object)
    det_rects = np.array(extend_lists([det['ptmf_rects'] if ocr_categories[det['category_id']] not in ['figure', 'table']
                                      else [[det['poly'][0], det['poly'][1], det['poly'][4], det['poly'][5]]] for det in layout_dets]))
    # 4. 处理数学公式的特殊标记
    det_seg_is_mf = np.array([seg.startswith('$') for seg in det_segs])
    det_seg_is_mf_iso = np.array([seg.startswith('$$') for seg in det_segs])
    det_segs[det_seg_is_mf_iso] = list(map(lambda x: '\[{}\]'.format(x[2:-2]), det_segs[det_seg_is_mf_iso]))
    det_segs[det_seg_is_mf*(~det_seg_is_mf_iso)] = list(map(lambda x: '\({}\)'.format(x[1:-1]), det_segs[det_seg_is_mf*(~det_seg_is_mf_iso)]))
    # 5. 对每个文本段进行tokenize处理
    det_seg_tokens, det_seg_token_spans, det_seg_token_is_sp = list(map(list, list(zip(*[custom_tokenize(seg) for seg in det_segs]))))  
    # 6. 统计每个文本段的token数量
    det_seg_token_nums = [len(det_seg_tokens[i]) for i in range(len(det_seg_tokens))]
    det_tokens = np.array(extend_lists(det_seg_tokens), object)
    det_token_is_sp = np.array(extend_lists(det_seg_token_is_sp), object)
    det_token_rect_ids = np.repeat(np.arange(len(det_segs)), det_seg_token_nums)
    return det_segs, det_rects, det_seg_tokens, det_seg_token_spans, det_tokens,det_token_is_sp, det_token_rect_ids

#全文tokenize
def tokenize_doc(det_dir, ocr_categories,filter_categories,debug = False ,output_dir =""):
    page_num = np.max([int(os.path.basename(name).split('.npy')[0]) for name in glob.glob(os.path.join(det_dir, '*.npy'))])
    doc_segs = [] 
    doc_rects = [] 
    doc_seg_tokens = [] 
    doc_seg_token_spans = [] 
    doc_seg_page_ids = []
    doc_tokens = [] 
    doc_token_is_sp = []
    doc_token_rect_ids = []
    num_rects = 0
    for i_page in range(page_num): 
        page_id = str(i_page+1).zfill(len(str(page_num)))
        det_segs, det_rects, det_seg_tokens, det_seg_token_spans, det_tokens,det_token_is_sp, det_token_rect_ids = tokenize_det_result(det_dir, page_id, ocr_categories,filter_categories)
        doc_segs.append(det_segs)
        doc_rects.append(det_rects)
        doc_seg_tokens.extend(det_seg_tokens)
        doc_seg_token_spans.extend(det_seg_token_spans)
        doc_seg_page_ids.extend([page_id] * len(det_segs))
        doc_tokens.append(det_tokens)
        doc_token_is_sp.append(det_token_is_sp)
        doc_token_rect_ids.append(det_token_rect_ids + num_rects)
        num_rects += len(det_rects)
    doc_segs = np.hstack(doc_segs)
    doc_rects = np.concatenate(doc_rects, axis=0)
    doc_seg_page_ids = np.array(doc_seg_page_ids, object)
    doc_tokens = np.hstack(doc_tokens)
    doc_token_is_sp = np.hstack(doc_token_is_sp)
    doc_token_rect_ids = np.hstack(doc_token_rect_ids)
    if debug:
        with open(os.path.join(output_dir,os.path.basename(os.path.dirname(det_dir))+"_token.txt"), 'w', encoding='utf-8') as f:
            for item in doc_tokens:
                f.write(f"{item}\n")
    return doc_segs, doc_rects, doc_seg_tokens, doc_seg_token_spans, doc_seg_page_ids, doc_tokens, doc_token_is_sp,doc_token_rect_ids

# 特殊token替换
def special_tokenize_replace(tokens, token_is_sp,new_figures_map,new_mf_map,token_output):
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

# 获取公式token
def get_mf_token(tokens, token_is_sp,output_path):
    special_token = [index for index,value in enumerate(token_is_sp) if value == True]
    mf = [tokens[index] for index in special_token if  "![](tables/" not in tokens[index] and "![](figures/" not in tokens[index]]   
    mf_index = [index for index in special_token if  "![](tables/" not in tokens[index] and "![](figures/" not in tokens[index]]
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(mf, f)
    return mf_index

#公式token转化为<mf{数字}>
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

