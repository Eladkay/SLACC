# thank you to https://lptk.github.io/programming/2019/10/15/simple-essence-y-combinator.html
z = (lambda g: (lambda rec: g(lambda y: rec(rec)(y)))((lambda rec: g(lambda y: rec(rec)(y)))))


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


class linked_list:
    def __init__(self, value, next=None):
        self.value = value
        self.next = next

    def __repr__(self):
        return f"linked_list({self.value}, {self.next})"

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __hash__(self):
        return hash(self.value) ^ hash(self.next)


def concat(list1: linked_list, list2: linked_list):
    if not list1:
        return list2
    if not list2:
        return list1
    return linked_list(list1.value, concat(list1.next, list2))
