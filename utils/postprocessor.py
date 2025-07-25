
from utils.deal_text import rematch_string
import os
import utils.difflib_modified as difflib_modified

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
            elif len(init_tokens[i[1]:i[2]])==1 and len(version2_tokens[i[3]:i[4]])==1 and rematch_string(init_tokens[i[1]:i[2]][0],version2_tokens[i[3]:i[4]][0]):
                temp_i =list(i)
                temp_i[0] = "equal"
                result.append(tuple(temp_i))
            else:
                result.append(i)
    return result


def show_diff(init_tokens,version2_tokens,output_dir,is_processed=False,opcodes=None,name="diff.html"):
    os.makedirs(output_dir, exist_ok=True)
    html_diff = difflib_modified.HtmlDiff().make_file(
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
    output = os.path.join(output_dir,name)
    with open(output, "w", encoding='utf-8') as f:
        f.write(html_utf8)


def write_diff(res,init_tokens,version2_tokens,output_dir):
    os.makedirs(output_dir, exist_ok=True)
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


