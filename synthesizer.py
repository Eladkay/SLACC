# SWEET: Synthesis With observational Equivalence (Elad & Tomer)
# SMART: Synthesis that is Multi-threaded, Abstractized, Recursive and Transparent

# Features:
# Lambda synthesis
# Automatic proving of equivalence
# Relatively fast! (checked with profiler)
# Synthesize recursion with Z combinator! (when halting is proven in grammar for all options)
# Expressive and flexible
# Idempotence and symmetry breaking done in grammar
# Caching
# Smart tokenization: Comments in grammar, automatic detection of nonterminals in complex expressions
# Detailed and readable debug information
# Short-circuiting for more efficient bottom-up enumeration
# Bottom-up enumeration!

# TODO:
# Make remaining tests pass
# Make it faster!
# Richer STDLIB
# Detect non-termination of recursion in lambda expressions
# Synthesis whilelang code? Other languages?
# Annotations for rules like symmetry and idempotence (auto-generation of symmetry and idempotence breaking rules)
# Why is there so much variance in running times?
# Do terminal detection, etc in parser
# Stricter checks on grammar: tokens must match ^[_A-Z]+|[^A-Z]+$
# Imperative synthesis! Details discussed with Orel
# Faster observational equivalence - see marking in function
# Adding regex support to syntax
# Multi-threaded synthesis
import profile
from typing import List
from z3 import Solver, Int, ForAll, sat, Z3Exception
from stdlib import *
import syntax
from syntax import Rule
import cProfile
import random
from enum import Enum

cache = {}


class ConstantResult(Enum):
    SEEN_NOT_A_CONSTANT = 1
    NOT_SEEN_NOT_A_CONSTANT = 2
    UNDECIDABLE_NOT_A_CONSTANT = 3
    SEEN_CONSTANT = 4
    NOT_SEEN_CONSTANT = 5
    UNDECIDABLE_CONSTANT = 6


def eval_cached(prog, input=None):
    try:
        if prog in cache:
            return cache[prog](input)
        func = lambda input: eval(prog)
        cache[prog] = func
        return func(input)
    except:
        return lambda: None  # x s.t. x != x


def do_synthesis(parsed, examples, timeout=60, force_observational=False, debug=False):
    """
    Synthesize a program from a list of expressions and examples.
    """
    import time
    rules, nonterminals = parsed
    if debug:
        print(f"DEBUG: {len(rules)} rules, {len(nonterminals)} nonterminals")
    g = expand(rules, "PROGRAM", nonterminals, examples=examples, prove=not force_observational, debug=debug)
    start_time = time.time()
    while timeout < 0 or time.time() - start_time < timeout:
        try:
            prog = next(g)
            if debug:
                print("DEBUG: trying", prog)
        except StopIteration:
            if debug:
                print("DEBUG: ran out of possible programs")
            return None
        if all(eval_cached(prog, item[0]) == item[1] for item in examples):
            if debug:
                print("DEBUG: found", prog)
            return prog
    if debug:
        print("DEBUG: timeout")
    return None


def check_if_function(prog_to_test, debug):
    try:
        if callable(eval_cached(prog_to_test)):
            if debug:
                print(f"DEBUG: {prog_to_test} is a function and therefore observational equivalence is undecidable")
            return True
    except:
        pass
    return False


def check_if_seen_constant(prog_to_test, seen_progs, nonterminals, debug):
    if "input" not in prog_to_test:
        if debug:
            print(f"DEBUG: {prog_to_test} does not contain input. Checking if it is a constant...")
        try:
            const = eval_cached(prog_to_test)
            if callable(const):
                if debug:
                    print(f"DEBUG: {prog_to_test} is a function and therefore observational equivalence is undecidable")
                return ConstantResult.UNDECIDABLE_CONSTANT
            if debug:
                print(f"DEBUG: {prog_to_test} is a constant. Checking if any other are the same constant...")
            for prog in seen_progs:
                try:
                    if eval_cached(prog) == const:
                        if debug:
                            print(f"DEBUG: {prog_to_test} is equivalent to {prog} because they are the same constant")
                        return ConstantResult.SEEN_CONSTANT
                except:
                    pass
            if debug:
                print(f"DEBUG: {prog_to_test} is a not-yet seen constant")
            return ConstantResult.NOT_SEEN_CONSTANT
        except NameError:
            # try proving
            return ConstantResult.UNDECIDABLE_NOT_A_CONSTANT  # todo
            print(f"DEBUG: {prog_to_test} is not a constant. Trying to prove it's equal to any other program...")
            try:
                s = Solver()
                x, y, z, w, n = Int('x'), Int('y'), Int('z'), Int('w'), Int('n')
                for prog in seen_progs:
                    if any(it in prog for it in nonterminals):
                        continue
                    try:
                        s.add(Exists([x, y, z, w, n], eval_cached(prog_to_test) != eval_cached(prog)))
                    except:
                        pass
                status = s.check()
                if status != sat:
                    if debug:
                        print(f"DEBUG: {prog_to_test} is equivalent to another program provably")
                    return ConstantResult.SEEN_NOT_A_CONSTANT
            except Z3Exception:
                return ConstantResult.UNDECIDABLE_NOT_A_CONSTANT  # not much we can do
            if debug:
                print(f"DEBUG: {prog_to_test} is not provably equivalent to another program.")
            return ConstantResult.NOT_SEEN_NOT_A_CONSTANT
        except:
            return ConstantResult.UNDECIDABLE_NOT_A_CONSTANT  # not much we can do
    return ConstantResult.UNDECIDABLE_NOT_A_CONSTANT


def equiv_to_any(seen_progs, prog_to_test, prove, nonterminals, examples=None, debug=False):
    if check_if_function(prog_to_test, debug):
        return False  # function equivalence is undecidable

    if any(it in prog_to_test for it in nonterminals):
        if debug:
            print(f"DEBUG: {prog_to_test} contains a nonterminal, is it in seen_progs? {prog_to_test in seen_progs}")
        return prog_to_test in seen_progs

    if prog_to_test in seen_progs:
        if debug:
            print(f"DEBUG: {prog_to_test} is in seen_progs")
        return True

    res = check_if_seen_constant(prog_to_test, seen_progs, nonterminals, debug)
    if res == ConstantResult.SEEN_CONSTANT or res == ConstantResult.SEEN_NOT_A_CONSTANT:
        return True
    if res == ConstantResult.NOT_SEEN_CONSTANT or res == ConstantResult.NOT_SEEN_NOT_A_CONSTANT:
        return False

    if prove:
        for prog in seen_progs:
            if any(it in prog for it in nonterminals):
                continue
            s = Solver()
            input = Int('input')
            s.add(ForAll([input], eval_cached(prog, input) == eval_cached(prog_to_test, input)))
            status = s.check()
            if status == sat:
                if debug:
                    print(f"DEBUG: {prog_to_test} is equivalent to {prog} provably")
                return True
    else:
        flag = False
        x_outs = [(k, eval_cached(prog_to_test, k)) for k, _ in examples]
        for prog in seen_progs:
            if any(it in prog for it in nonterminals):
                continue
            for k, _ in examples:
                prog_out = eval_cached(prog, k)
                x_out = [it for it in x_outs if it[0] == k][0][1]
                if prog_out != x_out:
                    flag = True
            if not flag:
                if debug:
                    print(f"DEBUG: {prog_to_test} exhibits observational equivalence with {prog}")
                return True
    return False


def get_ground_exprs(initial, rules, nonterminals) -> set:
    ret = set()
    temp = {initial}
    changed = True
    while changed:
        changed = False
        for rule in rules:
            nonterms = len([x for x in rule.rhs if x in nonterminals])
            if nonterms not in [0, 1] or (len(rule.rhs) != 1 and any(it in nonterminals for it in rule.rhs)):
                continue
            if rule.lhs in temp:
                if ''.join(rule.rhs) not in nonterminals and tuple(rule.rhs) not in ret:
                    ret.add(tuple(rule.rhs))
                    changed = True
                elif ''.join(rule.rhs) not in temp:
                    temp.add(''.join(rule.rhs))
                    changed = True
    return ret


# if __name__ == '__main__':
#     rules, nonterms = syntax.parse(r"""
#             PROGRAM ::= EXPR
#             EXPR ::= input[0] | input[1] | input | if_then_else(CONDITION,\s EXPR,\s EXPR)
#             CONDITION ::= EXPR \s<=\s EXPR | CONDITION \sand\s CONDITION | not\s CONDITION
#             """)
#     print(get_ground_exprs(("PROGRAM", ), rules, nonterms))


def get_values(rule, instances, nonterminals):
    ret = {()}
    for token in rule.rhs:
        if token not in nonterminals:
            ret = {item + (token,) for item in ret}
        else:
            newret = set()
            options = instances[token]
            for option in options:
                newret.update({item + option for item in ret})  # todo - instead of duplicating, a tree
            ret = newret
    return ret - instances[rule.lhs]


def short_circuit(new_values, nonterminals, rules, debug):
    extra = {it: set() for it in nonterminals}
    changed = True
    while changed:
        changed = False
        for rule in rules:
            if len([it for it in rules if it.lhs == rule.lhs]) > 1:
                continue  # todo?
            if not (len(rule.rhs) == 1 and rule.rhs[0] in nonterminals):
                continue
            if not new_values[rule.rhs[0]]:
                continue
            old_len = len(extra[rule.lhs])
            extra[rule.lhs].update(new_values[rule.rhs[0]])
            if old_len != len(extra[rule.lhs]):
                changed = True
                if debug:
                    print(f"DEBUG: {len(new_values[rule.rhs[0]])} elements short-circuited using rule {rule}")
    return extra


def expand(rules: List[Rule], initial, nonterminals, prove=True, examples=None, debug=False):
    # Bottom-Up Enumeration
    current_height = 1
    instances = {it: get_ground_exprs(it, rules, nonterminals) for it in nonterminals}
    instances_joined = {it: {''.join(itt) for itt in instances[it]} for it in nonterminals}
    if debug:
        print(f"DEBUG: Currently trying ground expressions")
    for instance in instances[initial]:
        yield ''.join(instance)
    while True:
        if debug:
            print(f"DEBUG: Currently trying expressions of height {current_height}")
        new_values = {it: set() for it in nonterminals}
        new_values_joined = {it: set() for it in nonterminals}
        for rule in rules:
            rule_values = get_values(rule, instances, nonterminals)
            if debug:
                if not rule_values:
                    print(f"DEBUG: application of rule {rule} gave nothing new")
                else:
                    print(f"DEBUG: application of rule {rule} gave {len(rule_values)} values, for example"
                          f" {''.join(random.choice(list(rule_values)))}")
            for value in rule_values:
                if debug:
                    print(f"DEBUG: checking for equivalence with {''.join(value)}...")
                try:
                    check_equiv = equiv_to_any(instances_joined[rule.lhs].union(new_values_joined[rule.lhs]),
                                               ''.join(value), prove, nonterminals, examples, debug)
                except Z3Exception:
                    prove = False
                    check_equiv = equiv_to_any(instances_joined[rule.lhs].union(new_values_joined[rule.lhs]),
                                               ''.join(value), prove, nonterminals, examples, debug)
                if not check_equiv:
                    new_values[rule.lhs].add(value)
                    new_values_joined[rule.lhs].add(''.join(value))
                    if rule.lhs == initial:
                        yield ''.join(value)
        if len(list(len(new_values[it]) > 0 for it in nonterminals)) == 0:
            break
        short_circuited = short_circuit(new_values, nonterminals, rules, debug)
        for new in short_circuited[initial]:
            yield ''.join(new)
        instances = {it: new_values[it].union(instances[it]).union(short_circuited[it]) for it in nonterminals}
        current_height += 1


if __name__ == '__main__':
    rules_listcomp = syntax.parse(r"""
           PROGRAM ::= LIST
           LIST ::= [EXPR \sfor\sx\sin\s input \sif\s BEXP]  # can also do [EXPR ... but 10 times slower
           BEXP ::= EXPR RELOP EXPR
           RELOP ::= \s<=\s | \s>=\s | \s<\s | \s>\s | \s==\s | \s!=\s
           EXPR ::= CONST | EXPR OP EXPR
           OP ::= \s+\s | \s-\s | \s/\s | \s*\s
           CONST ::= 0 | 1 | x
           """)

    examples = [([-1, 3, -2, 1], [4, 2])]
    profile.run("do_synthesis(rules_listcomp, examples, force_observational=True, debug=True, timeout=-1)")
