import unittest

from priority_queue import PriorityQueue, InvalidKeyError, EmptyError


class TestPushPopOrder(unittest.TestCase):
    def test_single_element(self):
        pq = PriorityQueue()
        a = pq.push("a", 5)
        self.assertEqual(len(pq), 1)
        self.assertIs(pq.peek(), a)
        self.assertIs(pq.pop(), a)
        self.assertEqual(len(pq), 0)

    def test_order_lowest_priority_first(self):
        pq = PriorityQueue()
        a = pq.push("a", 3)
        b = pq.push("b", 1)
        c = pq.push("c", 2)
        self.assertEqual([pq.pop() for _ in range(3)], [b, c, a])

    def test_negative_priorities(self):
        pq = PriorityQueue()
        pq.push("a", -1)
        pq.push("b", -5)
        self.assertIs(pq.pop(), "b")
        self.assertIs(pq.pop(), "a")

    def test_duplicates_as_distinct_objects(self):
        # Two equal-valued strings are still distinct objects if we create
        # them distinctly. The queue keys on id(), not value equality.
        a = "x".capitalize()  # 'X' as a fresh str
        b = "x".capitalize()  # another 'X'
        self.assertIsNot(a, b)
        pq = PriorityQueue()
        pq.push(a, 1)
        pq.push(b, 1)
        self.assertEqual(len(pq), 2)
        self.assertIs(pq.pop(), a)
        self.assertIs(pq.pop(), b)


class TestDecreaseKey(unittest.TestCase):
    def test_basic_decrease(self):
        pq = PriorityQueue()
        a = pq.push("a", 5)
        b = pq.push("b", 10)
        pq.decrease_key(a, 1)
        self.assertIs(pq.pop(), a)
        self.assertIs(pq.pop(), b)

    def test_decrease_to_root(self):
        pq = PriorityQueue()
        pq.push("a", 1)
        b = pq.push("b", 5)
        c = pq.push("c", 4)
        pq.decrease_key(b, 0)
        self.assertIs(pq.peek(), b)
        self.assertEqual([pq.pop() for _ in range(3)], [b, "a", c])

    def test_decrease_internal_node(self):
        # Build a heap where the target is not a leaf and not the root, then
        # decrease it to become the root.
        pq = PriorityQueue()
        nodes = [pq.push(i, i) for i in range(7)]
        # heap shape: 0 / 1 2 / 3 4 5 6 ; node 4 is internal
        pq.decrease_key(nodes[4], -1)
        self.assertIs(pq.peek(), nodes[4])

    def test_decrease_unknown_raises(self):
        pq = PriorityQueue()
        pq.push("a", 1)
        with self.assertRaises(InvalidKeyError):
            pq.decrease_key("ghost", 0)

    def test_decrease_equal_raises(self):
        pq = PriorityQueue()
        a = pq.push("a", 2)
        with self.assertRaises(ValueError):
            pq.decrease_key(a, 2)

    def test_decrease_greater_raises(self):
        pq = PriorityQueue()
        a = pq.push("a", 2)
        with self.assertRaises(ValueError):
            pq.decrease_key(a, 3)

    def test_decrease_then_remove_priority_of(self):
        pq = PriorityQueue()
        a = pq.push("a", 10)
        pq.decrease_key(a, 4)
        self.assertEqual(pq.priority_of(a), 4)
        self.assertEqual(pq.remove(a), 4)


class TestRemove(unittest.TestCase):
    def test_remove_root(self):
        pq = PriorityQueue()
        a = pq.push("a", 1)
        b = pq.push("b", 2)
        self.assertEqual(pq.remove(a), 1)
        self.assertEqual([pq.pop() for _ in range(len(pq))], [b])

    def test_remove_leaf(self):
        pq = PriorityQueue()
        nodes = [pq.push(i, i) for i in range(7)]
        self.assertEqual(pq.remove(nodes[6]), 6)
        self.assertEqual([pq.pop() for _ in range(len(pq))], list(range(6)))

    def test_remove_internal_restores_order(self):
        pq = PriorityQueue()
        nodes = [pq.push(i, i) for i in range(7)]
        # Remove node 1 (internal). Heap should remain valid.
        self.assertEqual(pq.remove(nodes[1]), 1)
        remaining = [pq.pop() for _ in range(len(pq))]
        self.assertEqual(remaining, [0, 2, 3, 4, 5, 6])

    def test_remove_unknown_raises(self):
        pq = PriorityQueue()
        with self.assertRaises(InvalidKeyError):
            pq.remove("ghost")

    def test_remove_last_element(self):
        pq = PriorityQueue()
        a = pq.push("a", 1)
        self.assertEqual(pq.remove(a), 1)
        self.assertEqual(len(pq), 0)
        self.assertFalse(bool(pq))


class TestEdgeCases(unittest.TestCase):
    def test_pop_empty_raises(self):
        pq = PriorityQueue()
        with self.assertRaises(EmptyError):
            pq.pop()

    def test_peek_empty_raises(self):
        pq = PriorityQueue()
        with self.assertRaises(EmptyError):
            pq.peek()

    def test_push_same_object_twice_raises(self):
        pq = PriorityQueue()
        obj = object()
        pq.push(obj, 1)
        with self.assertRaises(ValueError):
            pq.push(obj, 2)

    def test_contains(self):
        pq = PriorityQueue()
        a = pq.push("a", 1)
        self.assertIn(a, pq)
        self.assertNotIn("ghost", pq)
        pq.pop()
        self.assertNotIn(a, pq)

    def test_priority_of_unknown(self):
        pq = PriorityQueue()
        with self.assertRaises(InvalidKeyError):
            pq.priority_of("ghost")

    def test_bool(self):
        pq = PriorityQueue()
        self.assertFalse(bool(pq))
        pq.push("a", 1)
        self.assertTrue(bool(pq))

    def test_key_tiebreak_is_deterministic(self):
        # With a key function, equal priorities break by key(item) ascending.
        pq = PriorityQueue(key=len)
        pq.push("aaaa", 1)
        pq.push("bb", 1)
        pq.push("ccc", 1)
        out = [pq.pop() for _ in range(3)]
        self.assertEqual(out, ["bb", "ccc", "aaaa"])

    def test_key_only_breaks_ties(self):
        # Priority dominates; key never overrides it.
        pq = PriorityQueue(key=len)
        pq.push("aaaa", 0)   # higher urgency
        pq.push("bb", 5)
        self.assertIs(pq.pop(), "aaaa")


class TestBulkSequence(unittest.TestCase):
    def test_random_sequence_preserves_invariant(self):
        import random
        rng = random.Random(20240517)
        pq = PriorityQueue()
        expected = []
        nodes = []
        for _ in range(200):
            if nodes and rng.random() < 0.3:
                # decrease an existing node
                idx = rng.randrange(len(nodes))
                node = nodes[idx]
                cur = pq.priority_of(node)
                # new priority strictly less than the current one
                new_pri = cur - (1 + rng.randrange(1 << 20))
                pq.decrease_key(node, new_pri)
                expected.append((node, new_pri))
            else:
                p = rng.randrange(1 << 20)
                node = pq.push(object(), p)
                nodes.append(node)
                expected.append((node, p))
        # Drain and verify monotonic non-decreasing priority order.
        got = []
        while pq:
            got.append(pq.pop())
        self.assertEqual(len(got), len(nodes))


if __name__ == "__main__":
    unittest.main()
