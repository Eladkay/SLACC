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

# TODO:
# Make remaining tests pass
# What is bottom-up enumeration? Better enumeration is in order.
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

from z3 import Solver, Int, ForAll, sat, Z3Exception
from stdlib import *
import syntax
import cProfile
import random

cache = {}


def eval_on_input(prog, input):
    try:
        if prog in cache:
            return cache[prog](input)
        func = lambda input: eval(prog)
        cache[prog] = func
        return func(input)
    except:
        return None


def do_synthesis(parsed, examples, timeout=60, force_observational=False, debug=False):
    """
    Synthesize a program from a list of expressions and examples.
    """
    import time
    rules, nonterminals = parsed
    if debug:
        print(f"DEBUG: {len(rules)} rules, {len(nonterminals)} nonterminals")
    g = expand(rules, ("PROGRAM",), nonterminals, examples=examples, prove=not force_observational, debug=debug)
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            prog = next(g)
            if debug:
                print("DEBUG: trying", prog)
        except StopIteration:
            if debug:
                print("DEBUG: ran out of possible programs")
            return None
        if all(eval_on_input(prog, item[0]) == item[1] for item in examples):
            if debug:
                print("DEBUG: found", prog)
            return prog
    if debug:
        print("DEBUG: timeout")
    return None


def not_equiv_to_any(seen_progs, x, prove, nonterminals, examples=None, debug=False):
    if any(it in x for it in nonterminals):
        if debug:
            print(f"DEBUG: {x} contains a nonterminal, is it in seen_progs? {x in seen_progs}")
        return x not in seen_progs
    if x in seen_progs:
        if debug:
            print(f"DEBUG: {x} is in seen_progs")
        return False
    if prove:
        for prog in seen_progs:
            if any(it in prog for it in nonterminals):
                continue
            s = Solver()
            input = Int('input')
            s.add(ForAll([input], eval_on_input(prog, input) == eval_on_input(x, input)))
            status = s.check()
            if status == sat:
                if debug:
                    print(f"DEBUG: {x} is equivalent to {prog} provably")
                return False
    else:
        flag = False
        for prog in seen_progs:
            if any(it in prog for it in nonterminals):
                continue
            for k, _ in examples:
                if eval_on_input(prog, k) != eval_on_input(x, k):  # todo we don't have to calculate x, k every time
                    flag = True
            if not flag:
                if debug:
                    print(f"DEBUG: {x} exhibits observational equivalence with {prog}")
                return False
    return True


def expand(rules, initial, nonterminals, prove=True, examples=None, debug=False):
    queue = [initial]
    seen_progs = set()
    while queue:
        first = queue.pop(0)
        if not any(it in first for it in nonterminals):
            seen_progs.add(first)
            yield ''.join(first)
        else:
            for rule in rules:
                if rule.lhs not in first:
                    continue
                options_to_add = [()]
                for token in first:
                    if token == rule.lhs:
                        options_to_add1 = list((*x, token) for x in options_to_add)
                        options_to_add2 = list((*x, *rule.rhs) for x in options_to_add)

                        options_to_add = [*options_to_add1, *options_to_add2]
                    else:
                        options_to_add = list((*x, token) for x in options_to_add)
                if first in options_to_add:
                    options_to_add = list(filter(lambda x: x != first, options_to_add))
                not_yet_seen = set()
                for x in options_to_add:
                    try:
                        if not_equiv_to_any(list(map(lambda y: ''.join(y), seen_progs.union(not_yet_seen))),
                                            ''.join(x), prove, nonterminals,
                                            examples, debug):
                            not_yet_seen.add(x)
                    except Z3Exception:
                        prove = False
                        if not_equiv_to_any(list(map(lambda y: ''.join(y), seen_progs.union(not_yet_seen))),
                                            ''.join(x), prove, nonterminals,
                                            examples, debug):
                            not_yet_seen.add(x)
                if debug:
                    if not_yet_seen:
                        print(f"DEBUG: application of rule {rule} on {''.join(first)} gives {len(not_yet_seen)}"
                              f" element(s) including {''.join(random.choice(list(not_yet_seen)))}")
                    else:
                        print(f"DEBUG: application of rule {rule} on {''.join(first)} gives nothing new")
                seen_progs.update(not_yet_seen)
                for elem in not_yet_seen:
                    # binary search:
                    low = 0
                    high = len(queue) - 1
                    lt1 = len(''.join(elem))
                    while low <= high:
                        mid = (low + high) // 2
                        if lt1 < len(''.join(queue[mid])):
                            high = mid - 1
                        else:
                            low = mid + 1
                    queue.insert(low, elem)


if __name__ == '__main__':
    rules_listcomp = syntax.parse(r"""
            PROGRAM ::= LIST
            LIST ::= [ EXPR OP EXPR \sfor\sx\sin\s input \sif\s BEXP ]
            BEXP ::= EXPR RELOP EXPR
            RELOP ::= \s<=\s | \s>=\s | \s<\s | \s>\s | \s==\s | \s!=\s
            EXPR ::= CONST | EXPR OP EXPR
            OP ::= \s+\s | \s-\s | \s/\s | \s*\s
            CONST ::= 0 | 1 | x
            """)

    examples = [([-1, 3, -2, 1], [4, 2])]
    cProfile.run("print(do_synthesis(rules_listcomp, examples, force_observational=True))")
