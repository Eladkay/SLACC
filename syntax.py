import re


class CfgRule:
    def __init__(self, lhs: str, rhs: list):
        self.lhs = lhs
        self.rhs = rhs

    def __str__(self):
        return "%s -> %s" % (self.lhs, " ".join(self.rhs))

    def __repr__(self):
        return str(self)

    def extend(self, lst):
        ret = []
        lst = lst.copy()
        for elem in lst:
            if elem == self.lhs:
                ret.extend(self.rhs)
            else:
                ret.append(elem)
        return ret


TOKEN_REGEX = re.compile(r"^[_A-Z\d]+$|^[^A-Z]+$")
NONTERMINAL_REGEX = re.compile(r"^[_A-Z\d]*[A-Z]+[_A-Z\d]*$")
separation_tokens = ["(", ")", ",", "[", "]", "=", "->", ".", "*", "+", "-", "/", "%", ":"]
escapes = {"\\s": " ", "\\a": "->", "\\p": "|", "\\t": "\t", "\\n": "\n", "True": "(1==1)", "False": "(1==0)"}


def replace_escapes(string):
    for key, value in escapes.items():
        string = string.replace(key, value)
    return string


def parse_internal(string: str, sep="::=") -> (list, list):  # (rules, nonterminals)
    rules = string.split("\n")
    ret = []
    for rule in rules:
        if rule.isspace() or not rule:
            continue

        if rule.strip().startswith("#"):
            continue
        lhs, rhs = rule.split("#")[0].split(sep)

        for key in separation_tokens:
            rhs = rhs.replace(key, f" {key} ")
            lhs = lhs.replace(key, f" {key} ")

        for clause in rhs.split("|"):
            ret.append(CfgRule(lhs.strip(), list(map(replace_escapes, clause.split()))))
    nonterminals = set()
    for rule in ret:
        for token in rule.rhs:
            if NONTERMINAL_REGEX.match(token):
                nonterminals.add(token)
        if NONTERMINAL_REGEX.match(rule.lhs):
            nonterminals.add(rule.lhs)
    return ret, nonterminals


def parse(string: str) -> (list, list):  # (rules, nonterminals)
    ret, nonterminals = parse_internal(string)
    for rule in ret:
        for token in rule.rhs:
            if not TOKEN_REGEX.match(token):
                raise ValueError(
                    f"{token} is incorrectly named in rule {rule}. Does not match {TOKEN_REGEX}. This is an error.")
        if not NONTERMINAL_REGEX.match(rule.lhs):
            raise ValueError(
                f"{rule.lhs} is incorrectly named in rule {rule}. Does not match {TOKEN_REGEX}. This is an error.")
    if "PROGRAM" not in [rule.lhs for rule in ret]:
        raise ValueError("PROGRAM is not defined. This is an error.")
    if len([rule.lhs for rule in ret if rule.lhs == "PROGRAM"]) > 1:
        raise ValueError("PROGRAM has more than one rule. This is an error.")
    if any(["PROGRAM" in rule.rhs for rule in ret]):
        raise ValueError("PROGRAM is defined in right-hand side of rule. This is an error.")
    for nonterminal in nonterminals:
        if nonterminal not in [rule.lhs for rule in ret]:
            raise ValueError(f"There is no rule for {nonterminal}. This is an error.")
    return ret, nonterminals


def parse_term_rewriting_rules(string: str) -> list:
    ret, _ = parse_internal(string, sep="->")
    return [(re.compile(''.join(list(map(replace_escapes, it.lhs.split())))), ''.join(it.rhs)) for it in ret]
