# SLACC - Synthesizer Lacking A Cool Acronym
## _yes, the name itself is wordplay_


It's a SyGuS with bottom-up enumeration, observational equivalence, automatic proving and no cool acronym. Really, we tried.

### Setup:
`pip install -r requirements.txt`

(Required libraries: OrderedSet, Z3)

### Using the synthesizer:
You can run the test cases:

```python3 tests.py```

You can make your own test cases by defining a grammar and giving examples:
```python
import syntax
import synthesizer
rules_listcomp = syntax.parse(r"""
PROGRAM ::= LIST
LIST ::= [EXPR \sfor\s x\s in\s input\s if\s BEXP] # you can use \s to denote a space in a grammar
BEXP ::= EXPR RELOP EXPR # also, comments in grammars are legal!
RELOP ::= \s<=\s | \s>=\s | \s<\s | \s>\s | \s==\s | \s!=\s
EXPR ::= CONST | EXPR OP EXPR
OP ::= \s+\s | \s-\s | \s*\s
CONST ::= 0 | 1 | x
""")
examples = [([-1, 3, -2, 1], [4, 2])]
synthesizer.do_synthesis(rules_listcomp, examples, timeout=-1)
# synthesize [x + 1 for x in input if x > 0]
```

### More detailed metarules for the grammar rules

I tried to give a grammar specifying all legal grammars, but it got too confusing, so here are the grammar rules in writing:
- Rules are given in the format `LHS ::= RHS1 | RHS2 | ... # COMMENT`, with at least one RHS. The line comment and its preceding hash sign are optional.
- There is exactly one rule with `PROGRAM` on its left-hand side. There are no rules with `PROGRAM` on their right-hand side clauses.
- Nonterminals are the symbols on left-hand sides of rules. Nonterminals also must match the following regex: 
```^[_A-Z\d]*[A-Z]+[_A-Z\d]*$```.
- Every token matching the above regex must appear on the LHS of at least one rule.
- Tokens are seperated by spaces, and also by the following characters: `(),[]=->.*+-/%:`.
- Every token that is not a nonterminal is considered a terminal symbol, and must contain *no capital letters*.
- You can type literal spaces and other otherwise inaccessible terms by using the following table of escapes:
`{'\\s': ' ', '\\a': '->', '\\p': '|', '\\t': '\t', '\\n': '\n', 'True': '(1==1)', 'False': '(1==0)'}`

### Interface
Users should really only use the following functions:
- `syntax.parse(rules)`: Parses a grammar from a string and returns an object representing the grammar, to be passed to the synthesizer.
- `syntax.parse_term_rewriting_rules(rules)`: Parses a set of term rewriting rules from a string and returns an object representing the rules, to be passed to the synthesizer.
    - The term rewriting rules are each given in the format `LHS -> RHS` where `LHS` is a regular expression and `RHS` is a string that is allowed to depend on the capturing groups `\1`, `\2`, etc.
- `synthesizer.do_synthesis(rules, examples[, timeout=60][, trs=None][, depth_limit=None])`: Accepts a `rules` object created by `syntax.parse` and also a list of pairs `examples` where each pair is to be understood as input and output respectively.
    - Returns a Python expression `e` that matches the grammar that built `rules` and such that for every `(a, b)` in examples, `(lambda input: e)(a) == b` evaluates to `True`.
    - The synthesis will be aborted after no less than `timeout` seconds (unless the grammar ran out of words or reached the depth limit), where the default is `60` and `-1` can be used to disable the timeout altogether.
    - If `depth_limit` is not `None`, the synthesis will also be aborted after reaching the depth limit.
    - If `trs` is not `None`, the synthesis will use the term rewriting rules represented by `trs`. For more details, see **Term Rewriting** below.

### Config
The config is simple, really, it only contains 3 parameters:
- `debug`: If this option is on, the synthesizer will be *very* verbose. This is very helpful in debugging a grammar, however it will significantly slow down its work (sometimes by 50+%).
- `depth_for_observational_equivalence` and `prove`: Will be explained later under "Features"

### Features
#### Efficiency
The synthesizer is designed to be fast, and it is optimized for maximum speed. Significant time was spent on profiling to allow for subsecond synthesis in many cases. On my laptop, the 25 tests in the standard test suite run in 1.34 seconds.

Here are some of the features and heuristics used to optimize the synthesizer:

- **Bottom-up enumeration** is used as opposed to top-down enumeration. 
  - This BFS-like approach allows expressions to be constructed by depth, prioritizing simpler expressions and making sure they are ruled out before continuing to more complex expressions. 
  - BUE ensures that all rules are used because when we must exhaust all options for expressions of depth `d` before continuing to expressions of depth `d + 1`.
  - The detection of ground expressions is enhanced from classical BUE - a terminal `e` is considered ground for nonterminal `T` if there are nonterminals `T1`, ..., `Tn` such that there are rules `T -> T1`, ..., `Tn-1->Tn`, `Tn -> e`. This is like reverse short-circuiting.
  - Enumeration is done iteratively without recursion in an attempt to reduce overhead.
  - BUE allows for the use of **observational equivalence**.
- **Observational equivalence** is used to allow for more efficient synthesis in most cases.
  - OE allows for optimization of equivalent subexpressions to those already seen. This can save significant time in deep expressions (prune early, prune big). 
  - The benefit of OE appears to greatly depend on the type of grammar used. This matter is explored to a greater extent in the unit tests `test_measure_observational_equivalence1` and `test_measure_observational_equivalence2` found in `experiments.py`. See graphs [here](https://eladkay.com/files/observational_equivalence_graphs.pdf). The benefits of OE are expected to increase exponentially in the depth of the output expression.
  - The observational equivalence capability can be tuned in `config.py` by setting the minimal depth in which OE will kick in. The graphs linked in the previous item seem to imply that a good heuristic is for OE to work for problems that require a depth of at least 5. This can be changed dynamically in `config.py` or set to `-1` to be disabled completely.
- **Provable equivalence** as explained later can also help speed up synthesis in a similar manner to OE.
  - However, proving carries a significant overhead and should not be considered a way to speed up synthesis in most cases.
  - Provable equivalence may be worthwhile for projects that require a deep expression of the sort that usually benefits most from OE, but the specific expression type is not supported by OE (i.e. because it depends on variables other than `input`).
  - For more info, see under **Proving**.
- **Short-circuiting** is a partial tail recursion-like optimization I invented.
  - If `e` is an expression that corresponds to nonterminal `Tn`, and there are rules `T1 -> T2`, ..., `Tn-1 -> Tn`, where `Ti` are nonterminals, then we can consider `e` to be a legal instance of nonterminal `T1` in the same depth, without having to wait for the synthesizer to search `n - 1` more depth options. If `T1` is `PROGRAM` then it is also checked for being a correct solution to the synthesis problem.
  - This is very common because all grammars have a `PROGRAM ::= T` rule, which this optimization can optimize away.
  - This optimization means that `{A -> aB, B -> b}` and `{A -> B, B -> ab}` are not equivalent rulesets, despite `A`, `B` having the same values on both. The first one will consider `ab` as a depth 2 expression, while the second one allows short-circuiting and considers it a depth 1 expression.
- **Constant recognition** is employed heuristically in some cases because constants are easier to check for equivalence.
  - Any expression that does not contain `input` is considered a suspected constant.
  - If `e` is a suspected constant and `eval(e)` is defined and not a function, then `e` is considered a constant and checked for being in the consant cache. This requires significantly less time than classical OE.
  - If `e` is a suspected constant and `eval(e)` is not defined, then `e` probably contains variables (for example, it's the body of a lambda). In this case, even if `prove` is not enabled, the synthesizer will try to apply provable equivalence. For more info, see under **Proving**.
  - If `e` is a suspected constant and `eval(e)` is a function, then `e` is not a constant and we must consider it not yet seen. We won't waste time doing classical OE on `e` either.
  - Constant recognition is not perfect, nor can it ever be. In general, it is undecidable whether a given expression is constant or not. Our heuristic misses examples as simple as `input - input`, but we are willing to accept that.
- **Term rewriting** as explained below can also be used to make more efficient grammars by creating a semantic normal form for expressions.
  - Term rewriting is a third level of optimization below observational equivalence and provable equivalence. 
  - It allows for pruning of expressions that were not caught by either OE or PE. For example, it can be used to simplify expressions like `lambda x: reversed(reversed(x))` to `lambda x: x`, which is not possible for either OE (because it's in a lambda) or PE (because it's a list operation which is not supported).
  - For more details, see below under **Term Rewriting**.
- **Caching** is used in several places as a general programming good practice.

#### Expressiveness
The synthesizer is designed to be expressive and allow for a wide range of synthesized expressions. 

- Synthesis of lambda expressions is supported and accounted for in profiling, even when observational equivalence will not work. In some cases, SLACC can prove that two expressions are precisely equivalent using Z3.
- The STDLIB contains useful functions for functional-style programming, including some classical LISP favorites. In addition, it contains a Python-language implementation of the Z combinator, allowing for the use of recursion in grammars (for example, in `test_gcd` in the test suite). Grammars that make use of recursion must have that all possible expressions (including wrong ones) will terminate for the example inputs.
- Subexpressions do not have to be legal Python expressions, allowing for symbolic synthesis (like `test_regex` in `experiments.py` which describes a grammar synthesizing regular expressions).
- The parser is built to be expressive and forgiving, allowing for seamless introduction of nonterminals for the purpose of generalization (for example, replacing a variable name in an existing grammar with the nonterminal `VAR`).
- In order to prove that the synthesizer is expressive, *all (relevant) examples of synthesis from the lecture slides* are implemented as test cases:
  - `test_literal_reverse_engineering` from lecture 10 slide 5
  - `test_max` from lecture 10 slides 8-9
  - `test_listops_advanced` from lecture 10 slide 29 (slightly modified)
  - `test_bitwise_ops` from lecture 11 slide 22
  - `test_reverse_linked_list` from lecture 11 slide 24
  - `test_lists_super` from lecture 13 slide 48 (with another example because it was underspecified)
- The synthesizer naturally supports a functional style of programming expressed in Python. For example, see `test_recursive_with_lists` for a recursive implementation of `len(input)` expressed using the beloved `car` and `cdr` and using the Z combinator.
- Inputs and outputs in the examples can be of any type that supports `__eq__`, and do not have to be numeric (or any other specific type), hashable or even support `repr`/`str` (given that `debug` is turned off).

#### Proving
The synthesizer augments its observational equivalence capabilities with Z3-based SMT proving of equivalence between expressions even in cases where observational equivalence would not work, for example expressions evaluating to a function or expressions involving variables besides `input`.

In most cases, proving is provably a waste of time and will not speed up synthesis.

Here are the cases where SMT proving is used:

- Expressions that *do not* contain `input` but are not constants.
  - The synthesizer suspects that these expressions are, for example, the bodies of lambda expressions. It will try to compare them with other expressions corresponding to the same nonterminal, and prove that they are equivalent to an existing one.
  - This allows the following variable names over which it will be quantified: `x`, `y`, `z`, `w`, `n`.
  - If for an expression `e` and for all expressions `r` corresponding to the same nonterminal Z3 found an assignment for these variables such that `e` evaluated using the assignment is different from `r` evaluated using the assignment, then `e` is considered not equivalent to any existing expression.
  - If there exists an expression `r` such that there is no assignment for these variables such that `e` evaluated using the assignment is different from `r` evaluated using the assignment, then `e` is considered equivalent to `r`.
  - This is also discussed under **Efficiency**.
- Any expression in place of observational equivalence, ... 
  - ... if `prove` is enabled in the config.
  - It was an experiment to see if it was faster this way, and also it enabled the use of top-down enumeration, which I thought may be a good idea. It was not faster, and it was not a good idea.
  - It doesn't really have a good use case. Maybe I'll augment it later and then it'll be useful.

#### Term Rewriting
The synthesizer supports term rewriting systems, that are assumed to be *normalizing* and *terminating*. 

- TRSes are based on a set of rules allowing for syntactic refactoring of expressions. They do not make the synthesizer stronger but they can make the grammars more concise and readable.
- In a TRS, the rules are of the form `LHS -> RHS` where `LHS` is a regular expression which may contain capturing groups and serves to find the expressions to which this rule can be applied. `RHS` is the rewritten expression, which may depend on the capturing groups from `LHS`.
- For example, a rule in a TRS could be `^\(([^\s]*) \+ 0\)$ -> \1`. This rule replaces expressions of the form `(x + 0)` with `x`.
- Term rewriting can be used to break symmetry and idempotence relations. For example, it can be used to replace `sorted(sorted(x))` with `sorted(x)` because `sorted` is idempotent.
- Examples for usage of term rewriting, and for TRS rules, are given in `test_term_rewriting`.
  - The rules are assumed to be *terminating*: that is, no matter the order the rules are applied, they can only be applied a finite amount of times. For example, this rule is illegal: `^(.*)$ -> \1 + 0`, because it can always be applied, an infinite number of times.
  - The rules are assumed to be *normalizing*: that is, the order the rules are applied does not matter, and a common *normal form* exists for all possible orders of application. For example, these two rules cannot coexist: `a -> b`, `a -> c`.
- Term rewriting rules are applied on every expression, belonging to any nonterminal. It is not limited to `PROGRAM`.

#### Usability
The synthesizer is designed to be friendly and usable from a human perspective. It was designed to give clear error messages and be easily debuggable. This is from the viewpoint that synthesis should optimally be considered an actual tool and not just a theoretical concept.

Here are some examples of software engineering concerns considered when designing the synthesizer:

- The grammars are given in the well-known BNF form and allow for more complex syntax than that is strictly necessary.
  - Multiple clauses are allowed on one line separated by a pipe (`|`).
  - Line comments are legal (including in lines that also contain a rule).
  - The metarules for giving grammars enforce a certain convention that allows for readable grammars. One advantage is that these rules clearly distinguish terminals from nonterminals.
- The error messages are built to be maximally descriptive, even if `debug` is disabled. This is out of the principle that programs should not fail silently. The debug flag affects messages that are not errors, but can provide additional context in case an error should occur.
- The synthesizer is built in a way that allows all of its components to be generated, and its output used, in a programmatic fashion.
  - For example, one could construct a program that receives inputs from the user and tries to predict the next one. The grammar could be hard-coded while the examples are collected. Later, the program could guess by applying `eval` to the output of the synthesizer.
- When `debug` is enabled, the synthesizer is built in a way that allows for debugging a grammar and an example set easily and without applying an actual debugger to the synthesizer's implementation.
  - This could be useful, for example, when trying to make sure that nonterminals were correctly recognized (for example, `L1` is a nonterminal but `L 1` is a nonterminal followed by a terminal).
  - It can also help to check if the synthesizer is stuck on a certain input or rule, or if observational equivalence should be tweaked (up or down).

### Case Study

An interesting case study is `test_listcomp`:

The grammar:
```bnf
PROGRAM ::= LIST
LIST ::= [EXPR \sfor \sx \sin \sinput \sif\s BEXP]
BEXP ::= EXPR RELOP EXPR
RELOP ::= \s<=\s | \s>=\s | \s<\s | \s>\s | \s==\s | \s!=\s
EXPR ::= CONST | EXPR OP EXPR
OP ::= \s+\s | \s-\s | \s*\s
CONST ::= 0 | 1 | x
```
With the example `[-1, 3, -2, 1]` ↦ `[4, 2]`.
The synthesized expression is `[x + 1 for x in input if x >= 0]`.

This example demonstrates some interesting capabilities of the synthesizer:
- Short-circuiting: There is significant short-circuiting in play when synthesizing this example. Two depth levels are saved by short-circuiting the derivations `EXPR ::= CONST` and `PROGRAM ::= LIST`. This optimization saves much time in this example, that may otherwise be spent on testing useless deeper expressions using the rule `EXPR ::= EXPR OP EXPR`.
- Expressiveness: The synthesizer can accept list inputs and outputs and not just hashable types or even just numbers. In addition, this example shows that the synthesis is fully syntax-guided: it shows that we can derive expressions like ` + `, despite them not being legal Python expressions or statements. Of course, in such cases observational equivalence would not work, but it's fine because it wouldn't have helped for `OP` anyway.
- Lambda synthesis: There is an implicit lambda expression in the list comprehension expression: it depends on `x` which is independent of `input` and is not a constant, either. This is dealt with efficiently as discussed under **Constant recognition**. 
- Grammatical flexibility: This example demonstrates a couple of comfort features in the syntax parser: multiple rules on one line, escape characters, more complex token parsing (allowing for `[EXPR` to count as two tokens and not one).

In the past, this test took upwards of 20 seconds on my computer. As I added more and more optimizations (especially OE, caching and bottom-up equivalence), the running time dropped to subsecond (as of writing, 32 miliseconds).

There are many more interesting cases, for example, this example does not demonstrate synthesis of recursion. I encourage you to explore the rich test suite which has been carefully crafted to ensure coverage of many features.

### Tips and Best Practices
Here are some tips for optimal use of the synthesizer. These are not (and in some cases, can not be) enforced by the synthesizer, but not following them can cause synthesis failure or poor performance. If your synthesis problem is running slow, try checking these items.

- Keep short-circuiting in mind: try to replace rulesets like `A ::= aB`, `B ::= b` whenever possible with the equivalent ruleset `A ::= B`, `B ::= ab`. For more information, see the section on short-circuiting.
- Perform idempotence and symmetry breaking in the grammar: for example, do not include a rule `EXPR ::= sorted(EXPR) | input | EXPR + EXPR | ...` because it will lead to `sorted(sorted(input))` being legal, as well as, `sorted(sorted(sorted(input)))`, etc. It is better to use equivalence breaking nonterminals: `EXPR ::= sorted(SORTED_EXPR) | input | EXPR + EXPR | ...` where `SORTED_EXPR ::= input | EXPR + EXPR | ...`, i.e. not allowing `sorted` to be applied twice as it is idempotent.  

  Another, more subtle place where this can apply is for associative operations: `NUM ::= NUM + NUM | 0 | 1` will cause duplicates: `0 + 1 + 0` can be derived as `(0 + 1) + 0` or as `0 + (1 + 0)`. This can be avoided by rephrasing as `NUM ::= CONST + NUM | CONST`, `CONST ::= 0 | 1`. The perceived increase in depth caused by an additional nonterminal is in fact avoided by short-circuiting.

  There are also more complex symmetries, for example `reversed(input)` is not equivalent to `reversed(reversed(input))`, but it is equivalent to `reversed(reversed(reversed(input)))`. You can optimize this as well - either in grammar or using a TRS.
- Make sure all recursive expressions terminate in grammar. That is, do not allow the grammar to create expressions that do not terminate for all inputs that could be passed to them. Failure to do so will probably cause the synthesizer to get stuck on such an expression. 
  
  An example for how to do so can be found in any recursive test, for example `test_recursive_basic` which enforces halting for all non-negative integers by forcing the recursive expression to accept the input `x - 1` and terminating always on `x == 0`. A more complex example can be found in `test_gcd`, which enforces a more complex decreasing and termination requirement, that is proven correct mathematically.
- If the synthesizer takes a long time or fails in the time limitations, try to reduce the number of recursive rules if possible. Playing with the observational equivalence depth in `config.py` may also help.

