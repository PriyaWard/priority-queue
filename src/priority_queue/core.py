"""Binary-heap priority queue with O(log n) decrease-key.

Design decisions (stated plainly so the tests and the reader agree):

1. The heap stores opaque "item" objects supplied by the caller; the caller
   never touches an index. Item identity (``id(item)``) is the internal key,
   so the caller can push the same value twice as long as each push is a
   distinct object. This is the only identity contract we rely on.

2. Priority is an orderable scalar (typically a number). Lower priority value
   means higher urgency (min-heap). We do not attempt to combine priorities that
   compare equal; ties resolve arbitrarily by heap position, which is
   deterministic for a fixed sequence of operations but callers must not rely
   on a tie-break order.

3. ``decrease_key`` *replaces* the stored priority with the one passed in; it
   does not compute a delta. If the new priority is larger than the current,
   we raise ``ValueError`` rather than silently doing nothing — this is a
   real bug-hiding case and we refuse to paper over it. This is the one
   interpretation of "supports decrease-key" we picked; we did not also try
   to support increase-key, and there is no ``update_priority`` method that
   figures out the direction. One clear rule.

4. ``change_item`` is not provided. The whole point of decrease-key is that
   the caller keeps a stable handle to the logical entity; replacing the item
   would break that invariant, so we don't offer it.

5. There is no copy semantics. ``push`` stores the object; the caller must not
   mutate it in a way that changes identity while it is in the queue. In
   practice nobody does this, but we say it out loud.

Why a binary heap and not a pairing heap or Fibonacci heap: the binary heap
keeps the implementation small, has good cache behaviour, and for the sizes
that matter (hundreds to low millions) it is competitive with the fancier
structures while being dramatically easier to audit. The trade-off is that
decrease-key is O(log n) rather than amortized O(1). We accept that; most
callers of a small library like this are not bound by it.
"""

from __future__ import annotations

from typing import Callable, Generic, List, Optional, TypeVar

T = TypeVar("T")
P = TypeVar("P")


class InvalidKeyError(KeyError):
    """Raised when an item handle is not present in this queue.

    Subclasses ``KeyError`` so ``except KeyError`` still catches it, but the
    distinct type lets callers distinguish a stale handle from other key
    errors if they care to.
    """


class EmptyError(IndexError):
    """Raised by ``pop``/``peek`` on an empty queue.

    Subclasses ``IndexError`` because popping an empty sequence is the closest
    stdlib analogy, and it lets ``except IndexError`` cover both list-pop and
    queue-pop in shared error handling.
    """


class _Slot(Generic[T, P]):
    __slots__ = ("item", "priority", "index")

    def __init__(self, item: T, priority: P, index: int) -> None:
        self.item = item
        self.priority = priority
        # index is the live position in _heap; kept in sync at every swap so
        # decrease-key can find the slot in O(1) via _positions[id(item)] and
        # then know where in _heap that slot lives without a linear scan.
        self.index = index


class PriorityQueue(Generic[T, P]):
    """A binary min-heap supporting efficient decrease-key by item identity.

    Items are compared by caller-supplied priorities only. The item itself is
    opaque to the queue; we key internal bookkeeping on ``id(item)``.

    Example:

        pq = PriorityQueue[str, float]()
        a = pq.push("a", 3.0)
        b = pq.push("b", 1.0)
        assert pq.pop() is b          # "b" has the lowest priority
        pq.decrease_key(a, 0.5)       # now "a" is most urgent
        assert pq.pop() is a

    The object returned by ``push`` is the same object passed in; treat it as
    the handle for ``decrease_key`` and ``remove``.
    """

    __slots__ = ("_heap", "_positions", "_key")

    def __init__(self, key: Optional[Callable[[T], P]] = None) -> None:
        self._heap: List[_Slot[T, P]] = []
        # id(item) -> _Slot. We hold a strong reference to the slot (and thus
        # transitively to the item) so the id() cannot be recycled while the
        # item is in the queue. Without this, id() reuse across GC would let a
        # new object alias a removed one's entry.
        self._positions: dict[int, _Slot[T, P]] = {}
        # Optional total-order function applied to items themselves, used only
        # to break priority ties deterministically. If None, ties break by heap
        # order (i.e. insertion/touch recency). We expose this rather than a
        # ``reverse`` flag because the two are independent concerns and a
        # reverse flag combined with a key is a classic source of off-by-one
        # confusion; a single key function is unambiguous.
        self._key = key

    # ------------------------------------------------------------------ #
    # Public API                                                          #
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self._heap)

    def __contains__(self, item: object) -> bool:
        return id(item) in self._positions

    def __bool__(self) -> bool:
        return bool(self._heap)

    def push(self, item: T, priority: P) -> T:
        """Insert ``item`` with ``priority`` and return ``item``.

        Returning the item (rather than None) lets callers write
        ``handle = pq.push(x, w)`` without keeping a separate variable; the
        returned object is the handle for ``decrease_key`` and ``remove``.
        """
        if id(item) in self._positions:
            raise ValueError("item is already in the queue")
        slot = _Slot(item, priority, len(self._heap))
        self._heap.append(slot)
        self._positions[id(item)] = slot
        self._siftdown(slot.index)
        return item

    def peek(self) -> T:
        """Return the highest-priority item without removing it."""
        if not self._heap:
            raise EmptyError("pop from an empty priority queue")
        return self._heap[0].item

    def pop(self) -> T:
        """Remove and return the highest-priority item."""
        if not self._heap:
            raise EmptyError("pop from an empty priority queue")
        last = self._heap.pop()
        if not self._heap:
            # Only one element was present; last is it.
            del self._positions[id(last.item)]
            return last.item
        root = self._heap[0]
        del self._positions[id(root.item)]
        self._heap[0] = last
        last.index = 0
        self._heapify(0)
        return root.item

    def decrease_key(self, item: T, priority: P) -> None:
        """Set ``item``'s priority to ``priority``.

        Raises ``InvalidKeyError`` if ``item`` is not in the queue. Raises
        ``ValueError`` if ``priority`` is not smaller than the current
        priority — we refuse to silently accept no-ops or increases because
        that hides bugs. If you genuinely need to raise a priority, ``pop``
        and ``push`` again; we deliberately do not provide a combined
        ``update`` that auto-detects direction, because two callers would
        expect opposite things from it.
        """
        slot = self._positions.get(id(item))
        if slot is None:
            raise InvalidKeyError(id(item))
        if priority == slot.priority:
            # Equal is not "smaller". Refuse, for the same reason as a larger
            # value: a silent no-op hides logic errors. Callers who want to
            # set-then-sift can check existence themselves first.
            raise ValueError("new priority is equal to the current priority")
        if priority > slot.priority:
            raise ValueError("new priority is greater than the current priority")
        slot.priority = priority
        # Decrease can only move the slot toward the root in a min-heap.
        self._siftdown(slot.index)

    def remove(self, item: T) -> P:
        """Remove ``item`` and return its priority at removal time.

        Returns the priority so callers that track external state (e.g. a
        tentative cost) can recover it without a separate lookup.
        """
        slot = self._positions.get(id(item))
        if slot is None:
            raise InvalidKeyError(id(item))
        idx = slot.index
        last = self._heap.pop()
        del self._positions[id(slot.item)]
        if idx < len(self._heap):
            # Fill the gap and restore order. Either sift-down or sift-up may
            # be needed depending on whether ``last`` is lighter or heavier
            # than the removed slot was; we try down first, and if it didn't
            # move, up. _heapify does exactly that.
            self._heap[idx] = last
            last.index = idx
            self._heapify(idx)
        return slot.priority

    def priority_of(self, item: T) -> P:
        """Return the current stored priority of ``item``."""
        slot = self._positions.get(id(item))
        if slot is None:
            raise InvalidKeyError(id(item))
        return slot.priority

    # ------------------------------------------------------------------ #
    # Heap mechanics                                                      #
    # ------------------------------------------------------------------ #

    def _cmp(self, a: _Slot[T, P], b: _Slot[T, P]) -> bool:
        # True if a should be above b (a has strictly smaller priority, or
        # equal priority and a._key(item) < b._key(item)). Equality of *both*
        # does not count — swapping equal slots is wasted work and, worse,
        # would make tie order depend on sift path rather than insertion.
        if a.priority < b.priority:
            return True
        if a.priority > b.priority:
            return False
        if self._key is None:
            return False
        return self._key(a.item) < self._key(b.item)

    def _swap(self, i: int, j: int) -> None:
        ai = self._heap[i]
        aj = self._heap[j]
        self._heap[i] = aj
        self._heap[j] = ai
        aj.index = i
        ai.index = j

    def _siftdown(self, i: int) -> None:
        # Move slot at i up toward root while it's lighter than its parent.
        while i > 0:
            parent = (i - 1) >> 1
            if self._cmp(self._heap[i], self._heap[parent]):
                self._swap(i, parent)
                i = parent
            else:
                break

    def _siftup(self, i: int) -> None:
        n = len(self._heap)
        while True:
            left = (i << 1) + 1
            right = left + 1
            best = i
            if left < n and self._cmp(self._heap[left], self._heap[best]):
                best = left
            if right < n and self._cmp(self._heap[right], self._heap[best]):
                best = right
            if best == i:
                break
            self._swap(i, best)
            i = best

    def _heapify(self, i: int) -> None:
        # After a fill-in, the slot might need to go either way. Try down
        # first; if it didn't move, try up. Exactly one (or neither) will do
        # work.
        before = self._heap[i].index  # == i, but be explicit
        self._siftup(i)
        if self._heap[before].index == before:
            self._siftdown(before)
