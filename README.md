# SLACC - Synthesizer Lacking A Cool Acronym
## _yes, the name itself is wordplay_

It's a SyGuS with bottom-up enumeration, observational equivalence, automatic proving and no cool acronym. Really, we tried.

### Setup:
- pip install -r requirements.txt

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

### More detailed rules for the rules

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
- `synthesizer.do_synthesis(rules, examples[, timeout])`: Accepts a `rules` object created by `syntax.parse` and also a list of pairs `examples` where each pair is to be understood as input and output respectively.
    - Returns a Python expression `e` that matches the grammar that built `rules` and such that for every `(a, b)` in examples, `(lambda input: e)(a) == b` evaluates to `True`.
    - The synthesis will be aborted after no less than `timeout` seconds (unless the grammar ran out of words), where the default is `60` and `-1` can be used to disable the timeout altogether.

### Config
The config is simple, really, it only contains 3 parameters:
- `debug`: If this option is on, the synthesizer will be *very* verbose. This is very helpful in debugging a grammar, however it will significantly slow down its work (sometimes by 50+%).
- `depth_for_observational_equivalence` and `prove`: Will be explained later under "Features"

### Features
#### Efficiency
The synthesizer is designed to be fast, and it is optimized for maximum speed. Significant time was spent on profiling to allow for subsecond synthesis in many cases. On my laptop, the 19 tests in the standard test suite run in 1.08 seconds.

Here are some of the features and heuristics used to optimize the synthesizer:

- TODO

#### Expressiveness
The synthesizer is designed to be expressive and allow for a wide range of synthesized expressions. 

- Synthesis of lambda expressions is supported and accounted for in profiling, even when observational equivalence will not work. In some cases, if `prove` is enabled in the config, SLACC can prove that two expressions are precisely equivalent using Z3.
- The STDLIB contains useful functions for functional-style programming, including some classical LISP favorites. In addition, it contains a Python-language implementation of the Z combinator, allowing for the use of recursion in grammars (for example, in `test_gcd` in the test suite). Grammars that make use of recursion must have that all possible expressions (including wrong ones) will terminate for the example inputs.
- Subexpressions do not have to be legal Python expressions, allowing for symbolic synthesis (like `test_regex` which describes a grammar synthesizing regular expressions).
- The parser is built to be expressive and forgiving, allowing for seamless introduction of nonterminals for the purpose of generalization (for example, replacing a variable name with the nonterminal `VAR`).
- In order to prove that the synthesizer is expressive, *all examples of synthesis from the lecture slides* are implemented as test cases:
  - `test_literal_reverse_engineering` from lecture 10 slide 5
  - `test_max` from lecture 10 slides 8-9
  - `test_listops_advanced` from lecture 10 slide 29 (slightly modified)
  - `test_bitwise_ops` from lecture 11 slide 22
  - `test_lists_super` from lecture 13 slide 48 (with another example because it was underspecified)
- The synthesizer naturally supports a functional style of programming expressed in Python. For example, see `test_recursive_with_lists` for a recursive implementation of `len(input)` expressed using the beloved `car` and `cdr` and using the Z combinator.

#### Proving
The synthesizer augments its observational equivalence capabilities with Z3-based SMT proving of equivalence between expressions even in cases where observational equivalence would not work, for example expressions evaluating to a function or expressions involving variables besides `input`.

Proving only works if `prove` is enabled in the config. Here are the cases where SMT proving is used:

- TODO

#### Usability
The synthesizer is designed to be friendly and usable from a human perspective. It was designed to give clear error messages and be easily debuggable.

Here are some examples of software engineering concerns considered when designing the synthesizer:

- TODO

### Case Study
