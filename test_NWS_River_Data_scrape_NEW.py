from NWS_River_Data_scrape_NEW import ISO_datestring


def test_ISO_datestring():
    """should return a string representing date and time.
    """
    from dateparser.search import search_dates
    # generate a datetime object
    hypothesis.strategies.datetimes(
        min_value=datetime.datetime(1, 1, 1, 0, 0),
        max_value=datetime.datetime(9999, 12, 31, 23, 59, 59, 999999),
        timezones=none(),
    )
    # convert it to string
    isodatestr = dt.isoformat()
    # convert string to datetime
    searchdate = search_dates(isodatestr, languages=["en"])
    # compare results report failures
    assert isodatestr == searchdate.isoformat()
    # repeat 50,000 times


from collections import namedtuple

Task = namedtuple("Task", ["summary", "owner", "done", "id"])
Task.__new__.__defaults__ = (None, None, False, None)


def test_defaults():
    """Using no parameters should invoke defaults."""
    t1 = Task()
    t2 = Task(None, None, False, None)
    assert t1 == t2


def test_member_access():
    """Check .field functionality of namedtuple."""
    t = Task("buy milk", "brian")
    assert t.summary == "buy milk"
    assert t.owner == "brian"
    assert (t.done, t.id) == (False, None)


def test_asdict():
    """_asdict() should return a dictionary."""
    t_task = Task("do something", "okken", True, 21)
    t_dict = t_task._asdict()
    expected = {"summary": "do something", "owner": "okken", "done": True, "id": 21}
    assert t_dict == expected


def test_replace():
    """replace() should change passed in fields."""
    t_before = Task("finish book", "brian", False)
    t_after = t_before._replace(id=10, done=True)
    t_expected = Task("finish book", "brian", True, 10)
    assert t_after == t_expected
