import subprocess

cmd_1 = "curl 'https://quicklatex.com/latex3.f' -H 'Content-Type: application/x-www-form-urlencoded' --data 'formula="
cmd_2 = "&fsize=60px&fcolor=a9a9a9&mode=0&out=1&remhost=quicklatex.com&preamble=\\usepackage{amsmath}\n\\usepackage{amsfonts}\n\\usepackage{amssymb}'"

def ql_render(formula: str) -> str:
    p = subprocess.Popen(cmd_1 + formula.replace("&", "%26") + cmd_2, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.stdout.read().decode("ascii").split()[1]
