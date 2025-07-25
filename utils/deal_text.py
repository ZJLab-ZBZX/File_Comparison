import numpy as np
import re
from utils.difflib_modified import SequenceMatcher


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
       
 
def rematch_string(str1, str2):
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
