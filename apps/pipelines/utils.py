def find_first(predicate, src_coll):
    return next(filter(predicate, src_coll), None)
