from operator import attrgetter
from itertools import imap
from xapian import Query


def phrase(db, terms, window=10, **kwargs):
    return Search(db, Query(Query.OP_PHRASE, terms, window), **kwargs)

def near(db, terms, window=10, **kwargs):
    return Search(db, Query(Query.OP_NEAR, terms, window), **kwargs)

def elite(db, terms, window=10, **kwargs):
    return Search(db, Query(Query.OP_ELITE_SET, terms, window), **kwargs)


class Search(object):
    """Generative query building interface.

    Nice for generating more complex query objects but avoiding the
    string formatting/parsing issues.
    """

    def __init__(self, db, query='', 
                 language=None, limit=None,
                 order=None, reverse=False,
                 disimilate=False, distance=28):
        if not isinstance(query, Query):
            query = db.querify(query)
        self.query = query

        self._db = db
        self._language = language
        self._limit = limit
        self._order = order
        self._reverse = reverse
        self._disimilate = disimilate
        self._distance = distance

    def copy(self, **kwargs):
        args = dict(query=self.query,
                    language=self._language,
                    limit=self._limit,
                    order=self._order,
                    reverse=self._reverse,
                    disimilate=self._disimilate,
                    distance=self._distance)
        if kwargs:
            args.update(kwargs)
        return type(self)(self._db, **args)

    def operator(self, query, op):
        """Wrap self with an operator and another query.
        """
        query = self._db.querify(query, language=self._language)
        return self.copy(query=Query(op, self.query, query))

    def filter(self, query):
        return self.operator(query, Query.OP_FILTER)

    def and_(self, query):
        return self.operator(query, Query.OP_AND)

    def or_(self, query):
        return self.operator(query, Query.OP_OR)

    def and_not(self, query):
        return self.operator(query, Query.OP_AND_NOT)

    def xor(self, query):
        return self.operator(query, Query.OP_XOR)

    def and_maybe(self, query):
        return self.operator(query, Query.OP_AND_MAYBE)

    def and_elite(self, queries):
        return self.and_(Query(Query.OP_ELITE_SET, queries))

    def or_elite(self, *queries):
        return self.or_(Query(Query.OP_ELITE_SET, queries))

    def expand(self, prefix=None, limit=10, mlimit=100):
        candidates = self.suggest(prefix, limit, mlimit)
        return self.or_(candidates)

    def limit(self, limit):
        return self.copy(limit=limit)
        
    def language(self, language):
        return self.copy(language=language)

    def order(self, order):
        return self.copy(order=order)

    def reverse(self, reverse):
        return self.copy(reverse=reverse)

    def disimilate(self, disimilate, distance=28):
        return self.copy(disimilate=disimilate,
                         distance=distance)

    def distance(self, distance):
        return self.copy(distance=distance)

    def count(self):
        return self._db.count(self.query, language=self._language)

    def estimate(self):
        return self._db.estimate(self.query, language=self._language)

    def suggest(self, prefix=None, limit=10, mlimit=100):
        return list(self._db.suggest(
            self.query, language=self._language,
            prefix=prefix, limit=limit, mlimit=mlimit))

    @property
    def records(self):
        """Generator over xapian results.
        """
        for r in self._db.query(
            self.query, limit=self._limit, language=self._language,
            order=self._order, reverse=self._reverse,
            disimilate=self._disimilate, 
            disimilate_threshold=self._distance):
            yield r

    @property
    def uids(self):
        """Generator for matching uids.
        """
        return imap(attrgetter('uid'), self.records)

    def select(self, *attrs):
        """ Generate out attr dicts from the records. """
        for r in self.records:
            yield {k: getattr(r, k, None) for k in attrs}
