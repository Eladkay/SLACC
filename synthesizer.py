# SWEET: Synthesis With observational Equivalence (Elad & Tomer)
# SMART: Synthesis that is Multi-threaded, Abstractized, Recursive and Transparent

# Features:
# Lambda synthesis
# Automatic proving of equivalence in some cases
# Relatively fast! (checked with profiler)
# Synthesize recursion with Z combinator! (when halting is proven in grammar for all options)
# Expressive and flexible
# Idempotence and symmetry breaking done in grammar
# Caching
# Smart tokenization: Comments in grammar, automatic detection of nonterminals in complex expressions
# Detailed and readable debug information
# Short-circuiting for more efficient bottom-up enumeration
# Bottom-up enumeration!
# Heuristics for observational equivalence use and for determining constants

# TODO short term:
# Make it faster! Better observational equivalence: For some reason it slows down significantly... represent programs as trees
# Richer STDLIB
# Multi-threaded synthesis (use subprocess or multiprocessing in Python) - not a great idea
# Annotations for rules like symmetry and idempotence (auto-generation of symmetry and idempotence breaking rules)
# Understand why is there so much variance in running times. - it's because the order wasn't deterministic
# Determinize order - done
# Join together observational equivalence checker and specification check
# Save vectors of results for each seen prog - done

# TODO idealistically:
# Detect non-termination of recursion in lambda expressions - literally impossible
# Synthesis whilelang code? Other languages?
# Imperative synthesis! Details discussed with Orel and Shachar and Matan, wait to receive preprint article from Hila
# Adding regex support to syntax - not so interesting
# Tail-recursion optimization (extend the short-circuit)

import profile
from typing import List
from z3 import Solver, Int, ForAll, sat, Z3Exception
from stdlib import *
import syntax
from syntax import Rule
import cProfile
import random
from enum import Enum
from config import *
from ordered_set import OrderedSet


prog_result_cache = {}
cache = {}


class ConstantResult(Enum):
    SEEN_NOT_A_CONSTANT = 1
    NOT_SEEN_NOT_A_CONSTANT = 2
    UNDECIDABLE_NOT_A_CONSTANT = 3
    SEEN_CONSTANT = 4
    NOT_SEEN_CONSTANT = 5
    UNDECIDABLE_CONSTANT = 6


class NoResult:  # thank you Bidusa
    def __eq__(self, other):
        return False


class ResultException(Exception):
    def __init__(self, res):
        self.res = res


def eval_cached(prog, input=None):
    try:
        if prog in cache:
            return cache[prog](input)
        func = eval(f"lambda input: {prog}")
        cache[prog] = func
        return func(input)
    except:
        return NoResult()  # x s.t. x != x


def do_synthesis(parsed, examples, timeout=60):
    """
    Synthesize a program from a list of expressions and examples.
    """
    import time
    rules, nonterminals = parsed
    global cache
    cache = {}
    global prog_result_cache
    prog_result_cache = {}
    if debug:
        print(f"DEBUG: {len(rules)} rules, {len(nonterminals)} nonterminals")
    g = expand(rules, "PROGRAM", nonterminals, examples=examples)
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


def check_if_function(prog_to_test):
    try:
        if callable(eval_cached(prog_to_test)):
            if debug:
                print(f"DEBUG: {prog_to_test} is a function and therefore observational equivalence is undecidable")
            return True
    except:
        pass
    return False


def check_if_seen_constant(prog_to_test, seen_progs, nonterminals):
    if "input" not in prog_to_test:  # heuristic. constants in general are undecidable
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
                    if eval_cached(prog) == const:  # todo: separate constant cache
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


def equiv_to_any(seen_progs, prog_to_test, nonterminals, examples):
    if check_if_function(prog_to_test):
        return False  # function equivalence is undecidable

    if any(it in prog_to_test for it in nonterminals):
        if debug:
            print(f"DEBUG: {prog_to_test} contains a nonterminal, is it in seen_progs? {prog_to_test in seen_progs}")
        return prog_to_test in seen_progs

    if prog_to_test in seen_progs:
        if debug:
            print(f"DEBUG: {prog_to_test} is in seen_progs")
        return True

    res = check_if_seen_constant(prog_to_test, seen_progs, nonterminals)
    if res == ConstantResult.SEEN_CONSTANT or res == ConstantResult.SEEN_NOT_A_CONSTANT:
        return True
    if res == ConstantResult.NOT_SEEN_CONSTANT or res == ConstantResult.NOT_SEEN_NOT_A_CONSTANT:
        return False

    if prove:
        for prog in seen_progs:
            s = Solver()
            input = Int('input')
            s.add(ForAll([input], eval_cached(prog, input) == eval_cached(prog_to_test, input)))
            status = s.check()
            if status == sat:
                if debug:
                    print(f"DEBUG: {prog_to_test} is equivalent to {prog} provably")
                return True
    else:
        try:
            x_outs = [eval_cached(prog_to_test, k) for k, _ in examples]
        except NameError:
            return False
        for prog in seen_progs:
            if prog in prog_result_cache:
                results_vector = prog_result_cache[prog]
            else:
                results_vector = [eval_cached(prog, k) for k, _ in examples]
                prog_result_cache[prog] = results_vector
            if x_outs == results_vector:
                if debug:
                    print(f"DEBUG: {prog_to_test} exhibits observational equivalence with {prog}")
                prog_result_cache[prog_to_test] = prog_result_cache[prog]
                return True
    return False


def get_ground_exprs(initial, rules, nonterminals) -> OrderedSet:
    ret = OrderedSet()
    temp = OrderedSet([initial])
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


def clean_instances(instances, nonterminals, examples, debug):
    if debug:
        print("DEBUG: Reached threshold for observational equivalence, cleaning instances set...")
    ret = {it: OrderedSet() for it in nonterminals}
    ret_joined = {it: OrderedSet() for it in nonterminals}
    for k in nonterminals:
        for v in instances[k]:
            if equiv_to_any(ret_joined[k], ''.join(v), nonterminals, examples):
                ret[k].add(v)
                ret_joined[k].add(''.join(v))
    return ret, ret_joined


def get_values(rule, instances, nonterminals):
    ret = OrderedSet([()])
    for token in rule.rhs:
        if token not in nonterminals:
            ret = OrderedSet([item + (token,) for item in ret])
        else:
            newret = OrderedSet()
            options = instances[token]
            for option in options:
                newret |= [item + option for item in ret]  # todo - instead of duplicating, a tree
            ret = newret
    return ret - instances[rule.lhs]


def short_circuit(new_values, nonterminals, rules):
    extra = {it: OrderedSet() for it in nonterminals}
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


def expand(rules: List[Rule], initial, nonterminals, examples):
    # Bottom-Up Enumeration
    current_height = 1
    instances = {it: get_ground_exprs(it, rules, nonterminals) for it in nonterminals}
    instances_joined = {it: {''.join(itt) for itt in instances[it]} for it in nonterminals}
    global prog_result_cache
    prog_result_cache = {it: [eval_cached(it, k) for k, _ in examples] for it in instances_joined[initial]}
    if debug:
        print(f"DEBUG: Currently trying ground expressions")
    for instance in instances[initial]:
        yield ''.join(instance)
    while True:
        if debug:
            print(f"DEBUG: Currently trying expressions of height {current_height}")

        if current_height == depth_for_observational_equivalence:
            instances, instances_joined = clean_instances(instances, nonterminals, examples, debug)

        new_values = {it: OrderedSet() for it in nonterminals}
        new_values_joined = {it: OrderedSet() for it in nonterminals}
        for rule in sorted(rules, key=lambda x: len(instances[x.lhs]), reverse=True):
            rule_values = get_values(rule, instances, nonterminals)
            if debug:
                if not rule_values:
                    print(f"DEBUG: application of rule {rule} gave nothing new")
                else:
                    print(f"DEBUG: application of rule {rule} gave {len(rule_values)} values, for example"
                          f" {''.join(random.choice(list(rule_values)))}")
            flag = False
            check_equiv = False
            if depth_for_observational_equivalence > current_height or depth_for_observational_equivalence < 0:
                if debug:
                    if depth_for_observational_equivalence > current_height:
                        print(f"DEBUG: Observational equivalence is not checked for expressions"
                              f" of height {current_height}")
                    else:
                        print(f"DEBUG: skipping equivalence checking because it is disabled in config.py")
                flag = True
            for value in rule_values:
                if not flag:
                    if debug:
                        print(f"DEBUG: checking for equivalence with {''.join(value)}...")
                    try:
                        check_equiv = equiv_to_any(instances_joined[rule.lhs].union(new_values_joined[rule.lhs]),
                                                   ''.join(value), nonterminals, examples)
                    except Z3Exception:
                        config.prove = False
                        check_equiv = equiv_to_any(instances_joined[rule.lhs].union(new_values_joined[rule.lhs]),
                                                   ''.join(value), nonterminals, examples)
                if not check_equiv:
                    new_values[rule.lhs].add(value)
                    new_values_joined[rule.lhs].add(''.join(value))
                    if rule.lhs == initial:
                        prog_result_cache[''.join(value)] = [eval_cached(''.join(value), k) for k, _ in examples]
                        yield ''.join(value)
        if len(list(len(new_values[it]) > 0 for it in nonterminals)) == 0:
            break
        short_circuited = short_circuit(new_values, nonterminals, rules)
        for value in short_circuited[initial]:
            prog_result_cache[''.join(value)] = [eval_cached(''.join(value), k) for k, _ in examples]
            yield ''.join(value)
        for k in nonterminals:
            instances[k] |= short_circuited[k]
            instances[k] |= new_values[k]
            for val in short_circuited[k].union(new_values_joined[k]):
                if all(nonterminal not in val for nonterminal in nonterminals):
                    instances_joined[k].add(val)
        current_height += 1


if __name__ == '__main__':
    # rules_listcomp_for_profiling = syntax.parse(r"""
    #        PROGRAM ::= LIST
    #        LIST ::= [EXPR \sfor\sx\sin\s input \sif\s BEXP]  # can also do [EXPR ... but 10 times slower
    #        BEXP ::= EXPR RELOP EXPR
    #        RELOP ::= \s<=\s | \s>=\s | \s<\s | \s>\s | \s==\s | \s!=\s
    #        EXPR ::= CONST | EXPR OP EXPR
    #        OP ::= \s+\s | \s-\s | \s/\s | \s*\s
    #        CONST ::= 0 | 1 | x
    #        """)
    #
    # examples_for_profiling = [([-1, 3, -2, 1], [4, 2])]
    # profile.run("do_synthesis(rules_listcomp_for_profiling, examples_for_profiling, timeout=-1)")
    rules_listops_advanced_for_profiling = syntax.parse(r"""
            PROGRAM ::= L
            L ::= (L1 \s+\s L) | sorted(L3) | L2[N:N] | [N] | input
            L1 ::= sorted(L3) | L2[N:N] | [N] | input
            L2 ::= (L1 \s+\s L) | sorted(L3) | input
            L3 ::= (L1 \s+\s L) | L2[N:N] | input
            N ::= L.index(N) | 0
            """)

    examples_for_profiling = [([1, 4, 7, 2, 0, 6, 9, 2, 5, 0, 3, 2, 4, 7], [1, 2, 4, 7])]
    profile.run("do_synthesis(rules_listops_advanced_for_profiling, examples_for_profiling, timeout=-1)")
