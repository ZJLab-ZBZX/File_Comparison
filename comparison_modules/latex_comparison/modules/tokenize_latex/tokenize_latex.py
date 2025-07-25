# taken and modified from https://github.com/harvardnlp/im2markup
# tokenize latex formulas
import sys
import os
import re
import argparse
import subprocess
import shutil
from threading import Timer
from datetime import datetime
import random


def run_cmd(cmd, timeout_sec=30):
    proc = subprocess.Popen(cmd, shell=True)
    kill_proc = lambda p: p.kill()
    timer = Timer(timeout_sec, kill_proc, [proc])
    try:
        timer.start()
        stdout,stderr = proc.communicate()
    finally:
        timer.cancel()


def tokenize_latex_new(latex_code, middle_file=""):
    print("-------------------------------")
    if not middle_file:
        middle_file = os.path.join("temp_b", "out-" + datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f') + str(
            random.randint(0, 10000)) + ".txt")
    temp_file = middle_file + '.tmp'
    # print("temp_file",temp_file)

    with open(temp_file, 'w', encoding='utf-8') as f:
        prepre = latex_code
        print(prepre)
        # replace split, align with aligned
        prepre = re.sub(r'\\begin{(equation|split|align|alignedat|alignat|eqnarray)\*?}(.+?)\\end{\1\*?}',
                        r'\\begin{aligned}\2\\end{aligned}', prepre, flags=re.S)
        prepre = re.sub(r'\\begin{(smallmatrix)\*?}(.+?)\\end{\1\*?}', r'\\begin{matrix}\2\\end{matrix}', prepre,
                        flags=re.S)
        f.write(prepre)

    # cmd = r"cat %s | node %s %s > %s " % (temp_file, os.path.join(os.path.dirname(__file__), 'preprocess_formula.js'), 'normalize', middle_file)
    cmd = r"type %s | node %s %s > %s " % (
    temp_file, os.path.join('modules/tokenize_latex', 'preprocess_formula.js'), 'normalize', middle_file)
    print(cmd)
    # ret = subprocess.call(cmd, shell=True)
    result = subprocess.run(cmd,
                            shell=True,
                            # check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                            )
    output = result.stdout.decode('utf-8', errors='replace')
    error = result.stderr.decode('gbk', errors='replace')

    with open(middle_file, 'r', encoding='utf-8') as f:
        normalized_latex = f.read().strip()
    # os.remove(middle_file)
    return error, normalized_latex


def tokenize_latex(latex_code, latex_type="", middle_file="",subset="gt"):
    if not latex_code:
        return False, latex_code
    if not latex_type:
        latex_type = "tabular" if "tabular" in latex_code else "formula"
    if not middle_file:
        middle_file = "out-" + datetime.now().strftime('%Y_%m_%d_%H_%M_%S') + ".txt"
    temp_file = middle_file + '.'+subset+'.tmp'
    ret = True
    if latex_type == "formula":
        latex_code = re.sub(r'@', r'\\text {嚻}', latex_code)
        # latex_code = 'D\\cdot H>\\max\\{4r^2+1,2r(v^2H^2-D^2H^2+(D\\cdot H)^2)\\},\\ s>2d,\\ \\mbox{if}\\ r>0'
        # print('pred', latex_code)

        while True:
            error, normalized_latex = tokenize_latex_new(latex_code,middle_file + '.'+subset)
            print('pred', latex_code)
            if 'parseerror' in error.lower():
                if 'rawMessage: \'Undefined control sequence: ' in error:
                    uc = error.split('rawMessage: \'Undefined control sequence: ')[-1].split('\n')[0][:-1]
                    pattern = rf'{uc}(?=[^a-zA-Z]|$)'
                    replacement = rf'\\text{{欃亹{uc[2:]}}}'
                    latex_code = re.sub(pattern, replacement, latex_code)
                    print('a', latex_code)
                else:
                    break
            else:
                break
                # error = '\n'.join([l for l in error.split('\n') if l not in [
        #     'LaTeX-incompatible input and strict mode is set to \'warn\': Too few columns specified in the {array} column argument. [textEnv]',
        #     'LaTeX-incompatible input and strict mode is set to \'warn\': LaTeX\'s accent \\textcircled works only in text mode [mathVsTextAccents]',
        #     'LaTeX-incompatible input and strict mode is set to \'warn\': LaTeX\'s accent \\r works only in text mode [mathVsTextAccents]',
        #     'LaTeX-incompatible input and strict mode is set to \'warn\': LaTeX\'s accent \\v works only in text mode [mathVsTextAccents]'
        #     ]]).strip()
        # with open(temp_file, 'w') as f:
        #     prepre = latex_code
        #     # replace split, align with aligned
        #     prepre = re.sub(r'\\begin{(split|align|alignedat|alignat|eqnarray)\*?}(.+?)\\end{\1\*?}', r'\\begin{aligned}\2\\end{aligned}', prepre, flags=re.S)
        #     prepre = re.sub(r'\\begin{(smallmatrix)\*?}(.+?)\\end{\1\*?}', r'\\begin{matrix}\2\\end{matrix}', prepre, flags=re.S)
        #     f.write(prepre)
        # # cmd = r"cat %s | node %s %s > %s " % (temp_file, os.path.join(os.path.dirname(__file__), 'preprocess_formula.js'), 'normalize', middle_file)
        # cmd = r"type %s | node %s %s > %s " % (temp_file, os.path.join('modules/tokenize_latex', 'preprocess_formula.js'), 'normalize', middle_file)
        # print(cmd)
        # ret = subprocess.call(cmd, shell=True)
        # # result = subprocess.run(cmd,
        # #                     shell=True,
        # #                     check=True,
        # #                     stdout=subprocess.PIPE,
        # #                     stderr=subprocess.PIPE
        # #                     )
        # # print("Output:\n", result.stdout.decode('utf-8', errors='replace'))
        # # print("Error message:\n", result.stderr.decode('gbk', errors='replace'))
        # # os.remove(temp_file)
        # if ret != 0:
        #     return False, latex_code
        error = '\n'.join([l for l in error.split('\n') if
                           not l.startswith('LaTeX-incompatible input and strict mode is set to \'warn\':')])
        print('error', error)
        if 'parseerror' in error.lower():
            print("parseerror")
            # print(img_id)
            # print('='*40)
            # perr_img_ids.append(img_id)
            # perr_msgs.append(error)
            # num_fail += 1
            normalized_latex = ''
            ret = False
            # result['error'] = 1
        elif len(error) > 0:
            print("other error")
            # perr_img_ids.append(img_id)
            # perr_msgs.append(error)
            # num_fail += 1
            normalized_latex = ''
            ret = False
            # result['error'] = 1
            # break
        else:
            # pattern = r'\\text\s\{欃亹([a-zA-Z]+)\}'
            normalized_latex = re.sub(r'\\text\s\{欃亹([^}]+?)\}', r'\\\1', normalized_latex)
            normalized_latex = re.sub(r'\\text {嚻}', r'@', normalized_latex)
            with open(middle_file + '.'+subset, 'w', encoding='utf-8') as f:
                prepre = normalized_latex
                f.write(prepre)
            # result['error'] = 0
            # pass
            print("tokenized latex",normalized_latex)

        operators = '\s?'.join('|'.join(['arccos', 'arcsin', 'arctan', 'arg', 'cos', 'cosh', 'cot', 'coth', 'csc', 'deg', 'det', 'dim', 'exp', 'gcd', 'hom', 'inf',
                                        'injlim', 'ker', 'lg', 'lim', 'liminf', 'limsup', 'ln', 'log', 'max', 'min', 'Pr', 'projlim', 'sec', 'sin', 'sinh', 'sup', 'tan', 'tanh']))
        ops = re.compile(r'\\operatorname {(%s)}' % operators)
        print("middle file",middle_file + '.'+subset)
        with open(middle_file + '.'+subset, 'r') as fin:
            post = []
            for line in fin:
                tokens = line.strip().split()
                tokens_out = []
                for token in tokens:
                    tokens_out.append(token)
                post1 = ' '.join(tokens_out)
                # use \sin instead of \operatorname{sin}
                names = ['\\'+x.replace(' ', '') for x in re.findall(ops, post1)]
                post1 = re.sub(ops, lambda match: str(names.pop(0)), post1).replace(r'\\ \end{array}', r'\end{array}')
                post.append(post1)
            post = '\n'.join(post)
            print("post",post)
        # os.remove(middle_file)
        return ret, post

    # elif latex_type == "formula" and subset == "gt":
    #     with open(temp_file, 'w') as f:
    #         prepre = latex_code
    #         # replace split, align with aligned
    #         prepre = re.sub(r'\\begin{(split|align|alignedat|alignat|eqnarray)\*?}(.+?)\\end{\1\*?}',
    #                         r'\\begin{aligned}\2\\end{aligned}', prepre, flags=re.S)
    #         prepre = re.sub(r'\\begin{(smallmatrix)\*?}(.+?)\\end{\1\*?}', r'\\begin{matrix}\2\\end{matrix}', prepre,
    #                         flags=re.S)
    #         f.write(prepre)
    #     # cmd = r"cat %s | node %s %s > %s " % (temp_file, os.path.join(os.path.dirname(__file__), 'preprocess_formula.js'), 'normalize', middle_file)
    #     cmd = r"type %s | node %s %s > %s " % (
    #     temp_file, os.path.join('modules/tokenize_latex', 'preprocess_formula.js'), 'normalize', middle_file)
    #     print(cmd)
    #     ret = subprocess.call(cmd, shell=True)
    #     # result = subprocess.run(cmd,
    #     #                     shell=True,
    #     #                     check=True,
    #     #                     stdout=subprocess.PIPE,
    #     #                     stderr=subprocess.PIPE
    #     #                     )
    #     # print("Output:\n", result.stdout.decode('utf-8', errors='replace'))
    #     # print("Error message:\n", result.stderr.decode('gbk', errors='replace'))
    #     # os.remove(temp_file)
    #     if ret != 0:
    #         return False, latex_code
    #
    #     operators = '\s?'.join('|'.join(
    #         ['arccos', 'arcsin', 'arctan', 'arg', 'cos', 'cosh', 'cot', 'coth', 'csc', 'deg', 'det', 'dim', 'exp',
    #          'gcd', 'hom', 'inf',
    #          'injlim', 'ker', 'lg', 'lim', 'liminf', 'limsup', 'ln', 'log', 'max', 'min', 'Pr', 'projlim', 'sec', 'sin',
    #          'sinh', 'sup', 'tan', 'tanh']))
    #     ops = re.compile(r'\\operatorname {(%s)}' % operators)
    #     with open(middle_file, 'r') as fin:
    #         post = []
    #         for line in fin:
    #             tokens = line.strip().split()
    #             tokens_out = []
    #             for token in tokens:
    #                 tokens_out.append(token)
    #             post1 = ' '.join(tokens_out)
    #             # use \sin instead of \operatorname{sin}
    #             names = ['\\' + x.replace(' ', '') for x in re.findall(ops, post1)]
    #             post1 = re.sub(ops, lambda match: str(names.pop(0)), post1).replace(r'\\ \end{array}', r'\end{array}')
    #             post.append(post1)
    #         post = '\n'.join(post)
    #     # os.remove(middle_file)
    #     return True, post
    
    elif latex_type == "tabular":
        latex_code = latex_code.replace("\\\\%", "\\\\ %")
        latex_code = latex_code.replace("\%", "<PERCENTAGE_TOKEN>")
        latex_code = latex_code.split('%')[0]
        latex_code = latex_code.replace("<PERCENTAGE_TOKEN>", "\%")
        if not "\\end{tabular}" in latex_code:
            latex_code += "\\end{tabular}"
        with open(middle_file, 'w') as f:
            f.write(latex_code.replace('\r', ' ').replace('\n', ' '))
        cmd = "perl -pe 's|hskip(.*?)(cm\\|in\\|pt\\|mm\\|em)|hspace{\\1\\2}|g' %s > %s"%(middle_file, temp_file)
        ret = subprocess.call(cmd, shell=True)
        if ret != 0:
            return False, latex_code
        os.remove(middle_file)
        cmd = r"cat %s | node %s %s > %s " % (temp_file, os.path.join(os.path.dirname(__file__), 'preprocess_tabular.js'), 'tokenize', middle_file)
        ret = subprocess.call(cmd, shell=True)
        # os.remove(temp_file)
        if ret != 0:
            return False, latex_code
        with open(middle_file, 'r') as fin:
            for line in fin:
                tokens = line.strip().split()
                tokens_out = []
                for token in tokens:
                    tokens_out.append(token)
                post = ' '.join(tokens_out)
        # os.remove(middle_file)
        return True, post
    else:
        print(f"latex type{latex_type} unrecognized.")
        return False, latex_code


if __name__ == '__main__':
    latex_code = open("2.txt", 'r').read().replace('\r', ' ')
    print("=>", latex_code)
    new_code = tokenize_latex(latex_code)
    print("=>", new_code)