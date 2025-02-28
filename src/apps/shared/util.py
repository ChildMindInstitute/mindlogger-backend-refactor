def assert_not_none[T](obj: T | None) -> T:
    """
    Assert that the object is not None to ignore type errors
    """
    assert obj is not None
    return obj
