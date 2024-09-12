import unittest
from itertools import permutations
from typing import ClassVar, List

from src.contracts.sort_itineraries import Itinerary
from src.sorts import SortAlgorithmIsUnknown
from src.sorts.base import (
    BestItinerariesSort, AbstractItinerariesSort, get_sort_algorithms, sort_itineraries, _currency_ratio, CheapestItinerariesSort, FastestItinerariesSort
)


class TestSortRegistration(unittest.IsolatedAsyncioTestCase):
    def test_new_class_will_be_registered_as_sort_algorithm(self):
        type("NewSort", (AbstractItinerariesSort,), {"name": "new_sort"})

        self.assertIn("new_sort", get_sort_algorithms())

    async def test_new_class_is_accessible_by_application(self):
        name = "new_sort"
        type("NewSort", (AbstractItinerariesSort,), {"name": name})

        with self.assertRaises(TypeError):  # no sort method
            await sort_itineraries(name, [])

        # recreate class with sort method
        type("NewSort", (AbstractItinerariesSort,), {"name": name, "sort": staticmethod(lambda x: x)})

        data = await sort_itineraries(name, [])
        self.assertEqual(data, [])

        # check that `sort_itineraries` is also not bugged
        with self.assertRaises(SortAlgorithmIsUnknown):
            await sort_itineraries("non_existing_sort", [])

    def test_algorithm_not_supporting_sort_protocol_is_not_registered(self):
        type("NewSort", (), {"name": "new_sort"})

        self.assertNotIn("new_sort", get_sort_algorithms())


class AbstractTestSort(unittest.TestCase):
    # is not run as is deleted at the end of the file
    cls: ClassVar[AbstractItinerariesSort]

    def permutate_testing(self, order, itineraries):
        """ Test all possible combinations of itineraries

        Important: in this method you should pass already sorted itineraries (or your expected result)
        :param order: order of itineraries
        :param itineraries: sorted list of itineraries
        """
        expected_result: List[Itinerary] = []
        for index in order:
            expected_result.append(itineraries[index])

        for case in permutations(itineraries):
            with self.subTest(case=case):
                self.assertEqual(
                    self.cls.sort(
                        case
                    ),
                    expected_result
                )

    def setUp(self):
        # assume USD-based currency
        _currency_ratio.set({"USD": 1, "EUR": 0.8})

    def test_sort_is_accessible(self):
        with self.subTest():
            self.assertEqual(self.cls.sort([]), [])

        with self.subTest():
            itinerary: Itinerary = Itinerary(
                id="1",
                duration_minutes=1,
                price={"amount": 1, "currency": "USD"},
            )
            self.assertEqual(self.cls.sort([itinerary]), [itinerary])

    def test_incorrect_data_on_input(self):
        # we can also test bad 'Price' or 'Duration' values (bad `Itinerary`)
        # but it is not responsibility of the sort algorithm, it's responsibility of the data provider - pydantic
        with self.subTest():
            with self.assertRaises(TypeError):
                self.cls.sort(None)  # noqa

    def sort_amount_diff(self, *order):
        self.permutate_testing(order, [
            Itinerary(
                id="1",
                duration_minutes=1,
                price={"amount": 1, "currency": "USD"},
            ),
            Itinerary(
                id="2",
                duration_minutes=1,
                price={"amount": 2, "currency": "USD"},
            ),
            Itinerary(
                id="3",
                duration_minutes=1,
                price={"amount": 3, "currency": "USD"},
            )
        ])

    def sort_currency_diff(self, *order):
        self.permutate_testing(order, [
            Itinerary(
                id="1",
                duration_minutes=1,
                price={"amount": 1, "currency": "USD"},
            ),
            Itinerary(
                id="2",
                duration_minutes=1,
                price={"amount": 1, "currency": "EUR"},
            )
        ])

    def sort_duration_diff(self, *order):
        self.permutate_testing(order, [
            Itinerary(
                id="1",
                duration_minutes=1,
                price={"amount": 1, "currency": "USD"},
            ),
            Itinerary(
                id="2",
                duration_minutes=2,
                price={"amount": 1, "currency": "USD"},
            )
        ])

    def sort_amount_duration_diff(self, *order):
        self.permutate_testing(order, [
            Itinerary(
                id="1",
                duration_minutes=1,
                price={"amount": 1, "currency": "USD"},
            ),
            Itinerary(
                id="2",
                duration_minutes=2,
                price={"amount": 2, "currency": "USD"},
            ),
            Itinerary(
                id="3",
                duration_minutes=1,
                price={"amount": 3, "currency": "USD"},
            )
        ])

    def sort_amount_currency_diff(self, *order):
        self.permutate_testing(order, [
            Itinerary(
                id="1",
                duration_minutes=1,
                price={"amount": 2, "currency": "USD"},
            ),
            Itinerary(
                id="2",
                duration_minutes=1,
                price={"amount": 1, "currency": "EUR"},
            )
        ])

    def sort_currency_duration_diff(self, *order):
        self.permutate_testing(order, [
            Itinerary(
                id="1",
                duration_minutes=1,
                price={"amount": 1, "currency": "USD"},
            ),
            Itinerary(
                id="2",
                duration_minutes=2,
                price={"amount": 1, "currency": "EUR"},  # 1 / 0.8 * 2 = 2.5 -> paying more, flight is longer
            )
        ])

    def sort_all_factors(self, *order):
        self.permutate_testing(order, [
            Itinerary(
                id="1",
                duration_minutes=1,
                price={"amount": 1, "currency": "USD"},  # 1 / 1 * 1 = 1, fast and cheap
            ),
            Itinerary(
                id="2",
                duration_minutes=2,
                price={"amount": 2, "currency": "USD"},  # 2 / 1 * 2 = 4, med fast and medium price
            ),
            Itinerary(
                id="3",
                duration_minutes=1,
                price={"amount": 3, "currency": "USD"},  # 3 / 1 * 1 = 3, fast and expensive
            ),
            Itinerary(
                id="4",
                duration_minutes=2,
                price={"amount": 1, "currency": "EUR"},  # 1 / 0.8 * 2 = 2.5 -> paying less, flight is med fast
            )
        ])


class TestBestSort(AbstractTestSort):
    cls: ClassVar[AbstractItinerariesSort] = BestItinerariesSort
    
    def test_sort_amount_diff(self):
        self.sort_amount_diff(0, 1, 2)

    def test_sort_currency_diff(self):
        self.sort_currency_diff(0, 1)

    def test_sort_duration_diff(self):
        self.sort_duration_diff(0, 1)

    def test_sort_amount_duration_diff(self):
        self.sort_amount_duration_diff(0, 2, 1)

    def test_sort_amount_currency_diff(self):
        self.sort_amount_currency_diff(1, 0)

    def test_sort_currency_duration_diff(self):
        self.sort_currency_duration_diff(0, 1)

    def test_sort_all_factors(self):
        self.sort_all_factors(0, 3, 2, 1)


class TestCheapestSort(AbstractTestSort):
    cls: ClassVar[AbstractItinerariesSort] = CheapestItinerariesSort

    def test_sort_amount_diff(self):
        self.sort_amount_diff(0, 1, 2)

    def test_sort_currency_diff(self):
        self.sort_currency_diff(0, 1)

    def test_sort_amount_duration_diff(self):
        self.sort_amount_duration_diff(0, 1, 2)

    def test_sort_amount_currency_diff(self):
        self.sort_amount_currency_diff(1, 0)

    def test_sort_currency_duration_diff(self):
        self.sort_currency_duration_diff(0, 1)

    def test_sort_all_factors(self):
        self.sort_all_factors(0, 3, 1, 2)


class TestFastestSort(AbstractTestSort):
    cls: ClassVar[AbstractItinerariesSort] = FastestItinerariesSort

    def test_sort_duration_diff(self):
        self.sort_duration_diff(0, 1)

    def test_sort_currency_duration_diff(self):
        self.sort_currency_duration_diff(0, 1)


# delete abstract class so unit tests not run
del AbstractTestSort

if __name__ == '__main__':
    unittest.main()
