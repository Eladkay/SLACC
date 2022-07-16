import unittest

import syntax
from synthesizer import *
from stdlib import *


class SynthesizerTests(unittest.TestCase):
    def test_arithm(self):
        rules_arithm = syntax.parse(r"""
        PROGRAM ::= NUM
        OPS ::= \s+\s | \s-\s | \s/\s

        NUM_NO_PARENS ::= NUM OPS NUM | NUM_NO_ONE \s*\s NUM_NO_ONE
        NUM ::= 1 | NUM OPS NUM | (NUM_NO_PARENS) | NUM_NO_ONE \s*\s NUM_NO_ONE
        NUM_NO_ONE ::= NUM OPS NUM | (NUM_NO_PARENS) | NUM_NO_ONE \s*\s NUM_NO_ONE
        TERMINALS ::= NUM
        """)

        examples = [(0, 2)]
        res = do_synthesis(rules_arithm, examples, debug=True)  # synthesize 1 + 1
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_comparisons(self):
        rules_comparisons = syntax.parse(r"""
        PROGRAM ::= EXPR RELOP EXPR
        RELOP ::= \s<=\s | \s>=\s | \s<\s | \s>\s | \s==\s | \s!=\s
        EXPR ::= NUM | NUM OP NUM
        NUM ::= 0 | 1 | input
        OP ::= \s+\s | \s-\s | \s/\s | \s*\s
        """)

        examples = [(0, True), (1, False)]
        res = do_synthesis(rules_comparisons, examples)  # synthesize input < 1
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_listops_basic(self):
        rules_listops_basic = syntax.parse(r"""
        PROGRAM ::= EXPR
        EXPR ::= sorted(EXPR) | [] | [EXPR,\s *EXPR] | CONST
        CONST ::= 0 | 1 | input
        """)

        examples = [([1, 2, 3], [1, 2, 3]), ([1, 3, 2], [1, 2, 3]), ([2, 1], [1, 2]), ([1, 2], [1, 2])]
        res = do_synthesis(rules_listops_basic, examples)  # synthesize sorted(input)
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)
        examples = [([1, 2, 3], [0, 1, 2, 3]), ([1, 3, 2], [0, 1, 2, 3]), ([2, 1], [0, 1, 2]), ([1, 2], [0, 1, 2])]

        res = do_synthesis(rules_listops_basic, examples)  # synthesize [0, *sorted(input)]
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_listops_advanced(self):
        rules_listops_advanced = syntax.parse(r"""
        PROGRAM ::= L
        L ::= (L1 \s+\s L) | sorted(L3) | L2[N:N] | [N] | input
        L1 ::= sorted(L3) | L2[N:N] | [N] | input
        L2 ::= (L1 \s+\s L) | sorted(L3) | input
        L3 ::= (L1 \s+\s L) | L2[N:N] | input
        N ::= L.index(N) | 0
        """)

        examples = [([1, 4, 7, 2, 0, 6, 9, 2, 5, 0, 3, 2, 4, 7], [1, 2, 4, 7])]
        res = do_synthesis(rules_listops_advanced, examples, force_observational=True, timeout=300, debug=True)
        # synthesize sorted(input[0..input.index(0)])
        # lecture 10 slide 29, slightly simplified (no adding 0 at the end)
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_listops_lambda_basic(self):
        rules_listops_lambda_basic = syntax.parse(r"""
        PROGRAM ::= EXPR
        EXPR ::= sorted(EXPR) | input | list(filter(LAMBDA ,\s EXPR ))
        EXPRVAR ::= VARC RELOP VARC
        RELOP ::= \s<=\s | \s>=\s | \s<\s | \s>\s | \s==\s | \s!=\s
        LAMBDA ::= lambda\s VAR :\s EXPRVAR
        VARC ::= VAR | CONST
        VAR ::= x
        CONST ::= 0 | 1 | input
        """)

        examples = [([-1, 3, -2, 1], [3, 1])]
        res = do_synthesis(rules_listops_lambda_basic, examples, force_observational=True)
        # synthesize filter(lambda x: x > 0), input)
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_listops_lambda_advanced(self):
        rules_listops_lambda_advanced = syntax.parse(r"""
        PROGRAM ::= EXPR
        EXPR ::= sorted(EXPR) | input | list(filter(BLAMBDA ,\s EXPR )) | list(map(VLAMBDA ,\s EXPR ))

        BLAMBDA ::= lambda\s VAR :\s BEXPRVAR
        BEXPRVAR ::= VARC RELOP VARC
        RELOP ::= \s<=\s | \s>=\s | \s<\s | \s>\s | \s==\s | \s!=\s

        VLAMBDA ::= lambda\s VAR :\s VEXPRVAR
        VEXPRVAR ::= VARC OP VARC
        OP ::= \s+\s | \s-\s | \s/\s | \s*\s

        VARC ::= VAR | CONST
        VAR ::= x
        CONST ::= 0 | 1 | input
        """)

        examples = [([-1, 3, -2, 1], [0, 4, -1, 2])]
        res = do_synthesis(rules_listops_lambda_advanced, examples, force_observational=True)
        # synthesize list(map(lambda x: x + 1, input))
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

        examples = [([-1, 3, -2, 1], [0, 0, 0, 0])]
        res = do_synthesis(rules_listops_lambda_advanced, examples, force_observational=True)
        # synthesize list(map(lambda x: 0, input))
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_listcomp(self):
        rules_listcomp = syntax.parse(r"""
        PROGRAM ::= LIST
        LIST ::= [EXPR \sfor\sx\sin\s input \sif\s BEXP]
        BEXP ::= EXPR RELOP EXPR
        RELOP ::= \s<=\s | \s>=\s | \s<\s | \s>\s | \s==\s | \s!=\s
        EXPR ::= CONST | EXPR OP EXPR
        OP ::= \s+\s | \s-\s | \s*\s
        CONST ::= 0 | 1 | x
        """)

        examples = [([-1, 3, -2, 1], [4, 2])]
        res = do_synthesis(rules_listcomp, examples, force_observational=True, debug=True, timeout=-1)
        # synthesize [x + 1 for x in input if x > 0]
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_literal_reverse_engineering(self):
        rules_literal_reverse_engineering = syntax.parse(r"""
        # This test is in honour of Itamar who is the TA of Reverse Eng
        PROGRAM ::= EXPR
        EXPR ::= input | list(reversed(NO_REVERSED_EXPR)) | sorted(NO_SORTED_EXPR)
        NO_REVERSED_EXPR ::= input | sorted(NO_SORTED_EXPR)
        NO_SORTED_EXPR ::= input | list(reversed(NO_REVERSED_EXPR))
        """)

        examples = [([1, 2, 3], [3, 2, 1]), ([1, 3, 2], [3, 2, 1])]
        res = do_synthesis(rules_literal_reverse_engineering, examples, force_observational=True)
        # synthesize reversed(sorted(input))
        # lecture 10 slide 5
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_if(self):
        rules_if = syntax.parse(r"""
        PROGRAM ::= EXPR
        EXPR ::= CONST \sif \sTrue \selse\s CONST
        CONST ::= 0 | 1 | input
        """)

        examples = [([], 1)]
        res = do_synthesis(rules_if, examples, force_observational=True)
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_recursive_basic(self):
        rules_rec_basic = syntax.parse(r"""
        PROGRAM ::= EXPR
        EXPR ::= (LAMBDA_REC_EXPR)(input)
        VAR ::= 0 | 1 | x
        LAMBDA_REC_EXPR ::= z(lambda\s rec:\s lambda\s x:\s REC_EXPR)
        REC_EXPR ::= VAR \sif\s x\s ==\s 0 \selse\s rec(x\s -\s 1) OP VAR
        OP ::= \s+\s | \s*\s
        """)

        examples = [(1, 1), (2, 2)]
        res = do_synthesis(rules_rec_basic, examples, force_observational=True)  # synthesize 'input' recursively
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

        examples = [(0, 1), (5, 120)]
        res = do_synthesis(rules_rec_basic, examples, force_observational=True)  # synthesize input!
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_recursive_advanced(self):
        rules_rec_advanced = syntax.parse(r"""
        PROGRAM ::= EXPR
        EXPR ::= (LAMBDA_REC_EXPR)(input) | CONST
        CONST ::= 0 | 1
        VAR ::= 0 | 1 | x
        LAMBDA_REC_EXPR ::= z(lambda\s rec:\s lambda\s x:\s REC_EXPR)
        REC_EXPR ::= VAR | VAR OP REC_EXPR
        REC_EXPR ::= (VAR \sif\s x \s==\s 0 \selse\s rec(x\s -\s 1) OP VAR)
        OP ::= \s+\s | \s*\s
        """)

        examples = [(0, 1), (5, 120)]
        res = do_synthesis(rules_rec_advanced, examples, force_observational=True, debug=True)  # synthesize input!
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    # @unittest.skip  # Works with top-down enumeration, does not work with bottom-up enumeration
    def test_recursive_with_lists(self):
        rules_rec_lists = syntax.parse(r"""
        PROGRAM ::= EXPR
        EXPR ::= (LAMBDA_REC_EXPR)(input) | CONST
        VAR ::= CONST | x | car(x)
        CONST ::= 0 | 1 | input
        LAMBDA_REC_EXPR ::= z(lambda\s rec:\s lambda\s x:\s REC_EXPR)
        REC_EXPR ::= (VAR \sif\s not\s x \selse\s rec(cdr(x)) OP VAR)
        OP ::= \s+\s | \s*\s
        """)  #  | REC_EXPR OP REC_EXPR

        examples = [([1, 2, 3, 4, 5], 5)]
        res = do_synthesis(rules_rec_lists, examples, force_observational=True, debug=True)  # synthesize len(input)
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    # Passes with bottom-up enumeration but not with top-down enumeration
    def test_bitwise_ops(self):
        rules_rec_lists = syntax.parse(r"""
        PROGRAM ::= VAR 
        VAR ::= CONST | input | ( VAR OPS VAR ) | ~ VAR_NO_NEG
        VAR_NO_NEG ::= input | ( VAR OPS VAR )
        CONST ::= 0 | 1
        OPS ::= \s+\s | \s&\s
        """)

        examples = [(83, 4)]
        res = do_synthesis(rules_rec_lists, examples, force_observational=True, debug=True)  # synthesize ~x & (x+1)
        # lecture 11 slide 22
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_gcd(self):
        rules_gcd = syntax.parse(r"""
        PROGRAM ::= EXPR
        EXPR ::= (LAMBDA_REC_EXPR)(input)
        VAR ::= x[0] | x[1]
        LAMBDA_REC_EXPR ::= z(lambda\s rec:\s lambda\s x:\s VAR \sif\s x[0] \s==\s x[1]\s else\s REC_EXPR)
        REC_EXPR ::= (rec((VAR, VAR_EXPR))\s if\s VAR RELOP VAR \selse\s rec((VAR_EXPR, VAR)))
        VAR_EXPR ::= x[0] \s-\s x[1] | x[1] \s-\s x[0]
        RELOP ::= \s<\s | \s>\s | \s==\s
        """)

        examples = [((5, 3), 1), ((4, 2), 2)]
        res = do_synthesis(rules_gcd, examples, force_observational=True, debug=True, timeout=120)
        # synthesize gcd(input)
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_all_any(self):
        rules_all_any = syntax.parse(r"""
        PROGRAM ::= EXPR
        EXPR ::= any(LAMBDA_EXPR \sfor\s x\s in\s input) | all(LAMBDA_EXPR \sfor\s x\s in\s input) | not\s EXPR_NO_NOT | CONST
        EXPR_NO_NOT ::= any(LAMBDA_EXPR \sfor\s x\s in\s input) | all(LAMBDA_EXPR \sfor\s x\s in\s input)
        CONST ::= True | False
        
        LAMBDA_EXPR ::= VAR RELOP VAR
        VAR ::= x | CONST_INT
        CONST_INT ::= 0 | 1
        RELOP ::= \s<\s | \s>\s | \s==\s | \s<=\s | \s>=\s | \s!=\s
        """)

        examples = [([-1, 3, -2, 1], True), ([5, 3, 4, 1], False)]
        res = do_synthesis(rules_all_any, examples, force_observational=True, debug=True)
        # synthesize any(x < 0 for x in input)
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

        examples = [([0, 0, 0, 0], True), ([0, 1, 0, 0], False), ([0, -1, 0, 0], False)]
        res = do_synthesis(rules_all_any, examples, force_observational=True)
        # synthesize all(x == 0 for x in input)
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_max(self):
        rules_max = syntax.parse(r"""
        PROGRAM ::= EXPR
        EXPR ::= input[0] | input[1] | input | if_then_else(CONDITION,\s EXPR,\s EXPR)
        CONDITION ::= EXPR \s<=\s EXPR | CONDITION \sand\s CONDITION | not\s CONDITION 
        """)

        examples = [((0, 1), 1), ((1, 0), 1), ((1, 2), 2), ((3, 0), 3)]
        res = do_synthesis(rules_max, examples, force_observational=True, debug=True, timeout=-1)
        # synthesize input[0] if input[0] > input[1] else input[1]
        # lecture 10 slide 8-9
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    @unittest.skip  # python does not work like this. might work if I implement imperative synthesis
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
        res = do_synthesis(rules_def, examples, force_observational=True, debug=True)
        # synthesize def f(x): return x * x in f(input)
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_observational_equivalence(self):
        rules_observational_equivalence = syntax.parse(r"""
        PROGRAM ::= EXPR
        EXPR ::= input | EXPR * EXPR | CONST | EXPR + EXPR | (- EXPR)
        CONST ::= 0 | 1
        # EXPR ::= input | EXPR * EXPR | (- EXPR)
        """)

        examples = [(0, 1), (1, 2), (-2, 5), (3, 10)]
        # examples = [(0, 0), (1, 1), (-2, 4), (3, 9)]
        res = do_synthesis(rules_observational_equivalence, examples, force_observational=True, debug=True, timeout=-1)
        # synthesize x^2 + 1
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual(eval(f"(lambda input: {res})({k})"), v)

    def test_strings(self):
        rules_strings = syntax.parse(r"""
        PROGRAM ::= EXPR
        EXPR ::= input | STRLIST[N] | EXPR.strip()
        N ::= 0 | 1 | 2
        STRLIST ::= EXPR.split(CHAR) | [EXPR,\s *STRLIST]
        CHAR ::= '.' | '@' | '/' | '#'
        """)

        examples = [("elad@eladkay.com", "eladkay")]
        res = do_synthesis(rules_strings, examples, force_observational=True, debug=True)
        # synthesize input.split('@')[1].split('.')[0]
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual((lambda input: eval(res))(k), v)

        examples = [("213.57.62.171", "57")]
        res = do_synthesis(rules_strings, examples, force_observational=True)
        # synthesize input.split('.')[1]
        self.assertIsNotNone(res)
        print(res)
        for k, v in examples:
            self.assertEqual((lambda input: eval(res))(k), v)

    # ideas for tests:
    # reverse a linked list
    # self-synthesis! use do_synthesis in the grammar
    # regular expressions
    # ([16, 77, 31], 46), ([60, 9, 61, 63, 1], 2) -> sorted(input)[-1] - sorted(input)[-2] (old lecture 13, slide 48)
    # Synthesize part of an email address from the address


if __name__ == '__main__':
    unittest.main()
