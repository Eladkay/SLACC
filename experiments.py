import re
import unittest

import config
import syntax
from synthesizer import *
from stdlib import *


class SynthesizerExperimentsTests(unittest.TestCase):
    # python does not work like this. might work if I implement imperative synthesis
    def test_def(self):
        rules_def = syntax.parse(r"""
        PROGRAM ::= (lambda:\s DEF \n EXPR)()
        DEF ::= def f(x):\n\s\s\s\s return\s EXPR_WITH_VAR
        EXPR_WITH_VAR ::= x | EXPR | EXPR_WITH_VAR OP EXPR_WITH_VAR
        EXPR ::= f(EXPR) | input | CONST | EXPR OP EXPR
        CONST ::= 0 | 1
        OP ::= \s+\s | \s-\s | \s*\s | \s/\s 
        """)

        examples = [(0, 0), (1, 1), (2, 4), (3, 9)]
        res = do_synthesis(rules_def, examples)
        # synthesize def f(x): return x * x in f(input)
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_measure_observational_equivalence1(self):
        config.set_debug(False)
        import time
        for n in range(1, 10):
            print(f"testing with function #{n}")
            for i in range(-1, 15):
                if not i: continue
                config.set_depth_for_observational_equivalence(i)
                grammar_for_measuring_observational_equivalence = syntax.parse(f"""
                PROGRAM ::= EXPR
                EXPR ::= EXPR OP VAR | VAR
                VAR ::= input | CONST
                OP ::= \s+\s | \s*\s
                CONST ::= 1
                """)
                examples = [(0, n), (1, 1 + n), (-2, 4 + n), (3, 9 + n)]
                time_start = time.time()
                do_synthesis(grammar_for_measuring_observational_equivalence, examples, timeout=-1)
                time_end = time.time()
                print(f"{i},{time_end - time_start}")
            print()

    def test_measure_observational_equivalence2(self):
        config.set_debug(False)
        import time
        for n in range(2, 10):
            print(f"testing with function #{n}")
            for i in range(-1, 15):
                if not i: continue
                config.set_depth_for_observational_equivalence(i)
                grammar_for_measuring_observational_equivalence = syntax.parse(f"""
                PROGRAM ::= EXPR
                EXPR ::= [] | [ITEM, *EXPR]
                # EXPR ::= [INNER_EXPR] | []
                # INNER_EXPR ::= ITEM | ITEM, INNER_EXPR
                ITEM ::= CONST | input[CONST]
                CONST ::= {' | '.join(reversed(list(map(str, range(n)))))}
                """)
                examples = [(list(range(n)), list(reversed(range(n))))]
                time_start = time.time()
                do_synthesis(grammar_for_measuring_observational_equivalence, examples, timeout=-1)
                time_end = time.time()
                print(f"{i},{time_end - time_start}")
            print()

    # takes too much memory right now
    def test_regex(self):
        test_lists_regex = syntax.parse(r"""
        PROGRAM ::= re.match(r" EXPR ",\s input).group(1)
        EXPR ::= CONST | EXPR_CONCAT EXPR | (EXPR_PAREN) | EXPR_PLUS+  # todo equivalence breaking here?
        EXPR_PAREN ::= EXPR_CONCAT EXPR | EXPR_PLUS+ | .
        EXPR_CONCAT ::= CONST | (EXPR_PAREN) | EXPR_PLUS+
        EXPR_PLUS ::= CONST | (EXPR_PAREN)
        CONST ::= a | b | .
        """)
        examples = [("aaabc", "aaa"), ("aba", "a")]
        config.set_debug(True)
        config.set_depth_for_observational_equivalence(-1)
        res = do_synthesis(test_lists_regex, examples, timeout=-1)
        # synthesize re.match(r"(.+)b.", input).group(1)
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_self_synthesis(self):  # surprisingly this actually works
        test_self_synthesis = syntax.parse(r"""
        PROGRAM ::= eval(do_synthesis(GRAMMAR,\s [(0,\s 1),\s (1,\s 2)],\s depth_limit=3))
        GRAMMAR ::= syntax.parse(f' GRAMMAR_INT ')
        GRAMMAR_INT ::= RULE | GRAMMAR_INT \ n RULE
        RULE ::= {"program".upper()} \s: : =\s {"expr".upper()}
        RULE ::= {"expr".upper()} \s: : =\s {"expr".upper()} \s{"op".upper()} \s{"expr".upper()}
        RULE ::= {"expr".upper()} \s: : =\s {"const".upper()}
        RULE ::= {"op".upper()} \s: : =\s + \p -
        RULE ::= {"const".upper()} \s: : =\s 0 \p 1 \p 2 \p {"input"}
        """)

        examples = [(0, 1), (1, 2)]
        res = do_synthesis(test_self_synthesis, examples, timeout=-1)
        # profile.run("synthesizer.do_synthesis(test_self_synthesis, examples, timeout=-1)")
        # synthesize eval(do_synthesis("...", [...], timeout=-1)) s.t this comes out to input + 1
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_binary_search(self):
        test_binary_search = syntax.parse(r"""
        PROGRAM ::= (z(lambda\s rec:\s lambda\s x:\s VALUE \sif\s x[0][(x[2]+x[3])/2] \s==\s x[1]\s else\s BINSEARCH P2
        P2 ::=                                                    ))(input[0],\s input[1],\s 0,\s len(input[0]) \s-\s 1)
        VALUE ::= x[1] | x[2] | x[3] | VALUE + VALUE | VALUE / 2 | VALUE + 1 | VALUE - 1
        BINSEARCH ::= rec((x[0], x[1], VALUE, VALUE)) | BINSEARCH \sif\s VALUE \s<\s VALUE \selse\s BINSEARCH
        """)

        examples = [(([2, 3, 5, 7, 9, 11], 9), 4)]
        res = do_synthesis(test_binary_search, examples)
        # synthesize binary search
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_partition(self):  # the world is not ready for CPS synthesis
        test_partition = syntax.parse(r"""
        PROGRAM ::= (z(lambda\s rec:\s lambda\s x:\s x[1]\s if\s not\s x[1]\s else\s LIST))(input)
        LIST ::= x | LIST.next | concat(LIST,\s LIST) | linked_list(LIST.value) | rec(LIST.next)
        """)

        examples = [((lambda x: x < 0, linked_list(1, linked_list(-1, linked_list(0)))),
                     (linked_list(-1), linked_list(1, linked_list(0))))]
        res = do_synthesis(test_partition, examples)
        # guess the number of which I am thinking - in hex
        # this basically uses the synthesizer as a solver
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)


if __name__ == '__main__':
    unittest.main()