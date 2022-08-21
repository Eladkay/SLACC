# SLACC: Synthesizer Lacking A Cool Acronym

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
# OE benchmarking
# Term rewriting systems

import profile
from typing import List
from z3 import Solver, Int, ForAll, sat, Z3Exception, Exists
from stdlib import *
import syntax
from syntax import CfgRule
import cProfile
import random
from enum import Enum
import config
from ordered_set import OrderedSet
import time

set_used = OrderedSet
prog_result_cache = {}
cache = {}
seen_constants = set_used()


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


def eval_cached(prog, input):
    try:
        if prog in cache:
            return cache[prog](input)
        func = eval(f"lambda input: {prog}")
        cache[prog] = func
        return func(input)
    except:
        return NoResult()  # x s.t. x != x


def debug(*args):
    if config.debug:
        print(*args)


def do_synthesis(parsed, examples, timeout=60, trs=None, depth_limit=None):
    """
    Synthesize a program from a list of expressions and examples.
    """
    rules, nonterminals = parsed

    global cache
    cache = {}
    global prog_result_cache
    prog_result_cache = {}
    global seen_constants
    seen_constants = set_used()

    debug(f"DEBUG: {len(rules)} rules, {len(nonterminals)} nonterminals")

    g = expand(rules, "PROGRAM", nonterminals, examples=examples, trs=trs, depth_limit=depth_limit)
    start_time = time.time()
    while timeout < 0 or time.time() - start_time < timeout:
        try:
            prog = next(g)
            debug("DEBUG: trying", prog)
        except StopIteration:
            debug("DEBUG: ran out of possible programs or reached depth limit")
            return None
        if all(eval_cached(prog, item[0]) == item[1] for item in examples):
            debug("DEBUG: found", prog)
            return prog
    debug("DEBUG: timeout")
    return None


def check_if_function(prog_to_test):
    try:
        if callable(eval_cached(prog_to_test, None)):
            debug(f"DEBUG: {prog_to_test} is a function and therefore observational equivalence is undecidable")
            return True
    except:
        pass
    return False


def check_if_seen_constant(prog_to_test, seen_progs):
    if "input" not in prog_to_test:  # heuristic. constants in general are undecidable
        debug(f"DEBUG: {prog_to_test} does not contain input. Checking if it is a constant...")
        try:
            const = eval_cached(prog_to_test, None)
            if callable(const) or type(const) == NoResult:
                debug(f"DEBUG: {prog_to_test} is not necessarily a constant and therefore observational equivalence"
                      f" is undecidable")
                return ConstantResult.UNDECIDABLE_CONSTANT
            debug(f"DEBUG: {prog_to_test} is a constant. Checking if any other are the same constant...")
            for prog in seen_constants:
                if eval_cached(prog, None) == const:
                    debug(f"DEBUG: {prog_to_test} is equivalent to {prog} because they are the same constant")
                    return ConstantResult.SEEN_CONSTANT
            debug(f"DEBUG: {prog_to_test} is a not-yet seen constant")
            return ConstantResult.NOT_SEEN_CONSTANT
        except NameError:
            # try proving
            debug(f"DEBUG: {prog_to_test} is not a constant. Trying to prove it's equal to any other program...")
            try:
                s = Solver()
                x, y, z, w, n = Int('x'), Int('y'), Int('z'), Int('w'), Int('n')
                for prog in seen_progs:
                    try:
                        s.add(Exists([x, y, z, w, n], eval_cached(prog_to_test, None) != eval_cached(prog, None)))
                    except:
                        pass
                status = s.check()
                if status != sat:
                    debug(f"DEBUG: {prog_to_test} is equivalent to another program provably")
                    return ConstantResult.SEEN_NOT_A_CONSTANT
            except Z3Exception:
                return ConstantResult.UNDECIDABLE_NOT_A_CONSTANT  # not much we can do
            debug(f"DEBUG: {prog_to_test} is not provably equivalent to another program.")
            return ConstantResult.NOT_SEEN_NOT_A_CONSTANT
        except:
            return ConstantResult.UNDECIDABLE_NOT_A_CONSTANT  # not much we can do
    return ConstantResult.UNDECIDABLE_NOT_A_CONSTANT


def equiv_to_any(seen_progs, prog_to_test, examples):
    debug(f"DEBUG: checking for equivalence with {prog_to_test}...")
    if check_if_function(prog_to_test):
        return False  # function equivalence is undecidable

    if prog_to_test in seen_progs:
        debug(f"DEBUG: {prog_to_test} is in seen_progs")
        return True

    res = check_if_seen_constant(prog_to_test, seen_progs)
    if res == ConstantResult.SEEN_CONSTANT or res == ConstantResult.SEEN_NOT_A_CONSTANT:
        return True
    if res == ConstantResult.NOT_SEEN_CONSTANT or res == ConstantResult.NOT_SEEN_NOT_A_CONSTANT or \
            res == ConstantResult.UNDECIDABLE_CONSTANT:
        seen_constants.add(prog_to_test)
        return False

    if config.prove:
        for prog in seen_progs:
            s = Solver()
            input = Int('input')
            s.add(ForAll([input], eval_cached(prog, input) == eval_cached(prog_to_test, input)))
            status = s.check()
            if status == sat:
                debug(f"DEBUG: {prog_to_test} is equivalent to {prog} provably")
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
                debug(f"DEBUG: {prog_to_test} exhibits observational equivalence with {prog}")
                prog_result_cache[prog_to_test] = prog_result_cache[prog]
                return True
    return False


def get_ground_exprs(initial, rules, nonterminals) -> set_used:
    ret = set_used()
    temp = set_used([initial])
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


def clean_instances(instances, nonterminals, examples):
    debug("DEBUG: Reached threshold for observational equivalence, cleaning instances set...")
    ret = {it: set_used() for it in nonterminals}
    ret_joined = {it: set_used() for it in nonterminals}
    for k in nonterminals:
        for v in instances[k]:
            if not equiv_to_any(ret_joined[k], ''.join(v), examples):
                ret[k].add(v)
                ret_joined[k].add(''.join(v))
    return ret, ret_joined


def get_values(rule, instances, nonterminals):
    ret = [()]
    for token in rule.rhs:
        if token not in nonterminals:
            ret = [item + (token,) for item in ret]
        else:
            newret = []
            options = instances[token]
            for option in options:
                newret.extend([item + option for item in ret])
            ret = newret
    return set_used(ret) - instances[rule.lhs]


def short_circuit(new_values, nonterminals, rules):
    extra = {it: set_used() for it in nonterminals}
    changed = True
    while changed:
        changed = False
        for rule in rules:
            nonterminals = [x for x in rule.rhs if x in nonterminals]
            if len(nonterminals) != 1 \
                    or rule.rhs[0] not in nonterminals:
                continue
            nonterminal = nonterminals[0]
            if not new_values[nonterminal]:
                continue
            old_len = len(extra[rule.lhs])

            extra[rule.lhs].update(new_values[rule.rhs[0]])
            if old_len != len(extra[rule.lhs]):
                changed = True
                debug(f"DEBUG: {len(extra[rule.lhs]) - old_len} elements short-circuited using rule {rule}")
    return extra


def apply_trs(string, trs):
    changed = True
    while changed:
        changed = False
        for k, v in trs:
            if k.search(string):
                string = k.sub(v, string)
                changed = True
    return string


def expand(rules: List[CfgRule], initial, nonterminals, examples, trs, depth_limit):
    # Bottom-Up Enumeration
    current_height = 1
    instances = {it: get_ground_exprs(it, rules, nonterminals) for it in nonterminals}
    instances_joined = {it: {''.join(itt) for itt in instances[it]} for it in nonterminals}
    global prog_result_cache
    prog_result_cache = {it: [eval_cached(it, k) for k, _ in examples] for it in instances_joined[initial]}
    debug(f"DEBUG: Currently trying ground expressions")
    for instance in instances[initial]:
        yield ''.join(instance)
    while True:
        if current_height == depth_limit:
            return
        debug(f"DEBUG: Currently trying expressions of height {current_height}")

        if current_height == config.depth_for_observational_equivalence:
            instances, instances_joined = clean_instances(instances, nonterminals, examples)

        new_values = {it: set_used() for it in nonterminals}
        new_values_joined = {it: set_used() for it in nonterminals}
        for rule in rules:
            rule_values = get_values(rule, instances, nonterminals)
            if not rule_values:
                debug(f"DEBUG: application of rule {rule} gave nothing new")
            else:
                debug(f"DEBUG: application of rule {rule} gave {len(rule_values)} values, for example"
                      f" {''.join(random.choice(list(rule_values)))}")

            skipped = config.depth_for_observational_equivalence > current_height or \
                      config.depth_for_observational_equivalence < 0
            if config.depth_for_observational_equivalence > current_height:
                debug(f"DEBUG: Observational equivalence is not checked for expressions of height {current_height}")
            elif config.depth_for_observational_equivalence < 0:
                debug(f"DEBUG: skipping equivalence checking because it is disabled in config.py")

            new_values_for_lhs = []
            new_values_for_lhs_joined = []
            for value in rule_values:
                joined = ''.join(value)
                found_equiv = (not skipped) and equiv_to_any(instances_joined[rule.lhs] | new_values_joined[rule.lhs],
                                                             joined, examples)
                if not found_equiv:
                    new_values_for_lhs.append(value)
                    new_values_for_lhs_joined.append(joined)
                    if rule.lhs == initial:
                        prog_result_cache[joined] = [eval_cached(joined, k) for k, _ in examples]
                        if trs:
                            joined = apply_trs(joined, trs)
                        yield joined

            new_values[rule.lhs] |= set_used(new_values_for_lhs)
            new_values_joined[rule.lhs] |= set_used(new_values_for_lhs_joined)

        if len(list(it for it in nonterminals if len(new_values[it]) > 0)) == 0:
            return

        short_circuited = short_circuit(new_values, nonterminals, rules)
        short_circuited_joined = {it: map(lambda x: ''.join(x), short_circuited[it]) for it in nonterminals}
        for value in short_circuited_joined[initial]:
            prog_result_cache[value] = [eval_cached(value, k) for k, _ in examples]
            if trs:
                value = apply_trs(value, trs)
            yield value

        for k in nonterminals:
            new_instances = []
            new_instances_joined = []
            for val in short_circuited[k] | new_values[k]:
                joined = ''.join(val)
                if trs:
                    joined = apply_trs(joined, trs)
                flag = joined in instances_joined[k]
                if not flag:
                    new_instances.append(val)
                    new_instances_joined.append(joined)
            instances_joined[k] |= set_used(new_instances_joined)
            instances[k] |= set_used(new_instances)
        current_height += 1
