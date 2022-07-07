# thank you to https://lptk.github.io/programming/2019/10/15/simple-essence-y-combinator.html
z_helper = lambda f: f(f)
z = (lambda g: z_helper(lambda rec: g(lambda y: rec(rec)(y))))


def car(x):
    return x[0]


def cdr(x):
    return x[1:]


def null(x):
    return isinstance(x, list) and not x


def cons(car, cdr):
    return [car, *cdr]


def if_then_else(x, _if, _else):
    return _if if x else _else


def foldl(acc, x, list):
    res = x
    for elem in list:
        res = acc(res, elem)
    return res


def foldr(acc, x, list):
    if not list:
        return x
    return acc(car(list), foldr(acc, x, cdr(list)))
