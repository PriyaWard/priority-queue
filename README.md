# priority_queue

A binary min-heap priority queue that supports `decrease_key` in O(log n)
without rebuilding the heap. Standard library only; no dependencies.

## Usage

```python
from priority_queue import PriorityQueue, InvalidKeyError, EmptyError

pq = PriorityQueue[str, float]()
a = pq.push("a", 3.0)
b = pq.push("b", 1.0)
assert pq.pop() is b          # "b" is most urgent (lowest priority value)
pq.decrease_key(a, 0.5)      # "a" becomes most urgent
assert pq.pop() is a

# Errors raised on misuse:
# pq.decrease_key("missing", 1.0)   -> InvalidKeyError
# pq.decrease_key(a, 2.0)          -> ValueError (must be strictly smaller)
# pq.pop()                         -> EmptyError  (when empty)
```

The object you pass to `push` is the handle you pass back to `decrease_key`,
`remove`, and `priority_of`. The queue keys its internal bookkeeping on
`id(item)`, so the same Python object must be used for both operations.

## Exported names

- `PriorityQueue` — the queue class.
- `InvalidKeyError` — raised when a handle is not in the queue (subclass of
  `KeyError`).
- `EmptyError` — raised by `pop`/`peek` on an empty queue (subclass of
  `IndexError`).

Methods on `PriorityQueue`:

- `push(item, priority) -> item`
- `pop() -> item`
- `peek() -> item`
- `decrease_key(item, priority) -> None`
- `remove(item) -> priority`
- `priority_of(item) -> priority`
- `__len__`, `__bool__`, `__contains__`

An optional `key` callable can be passed to the constructor; it is applied to
the items and used **only** to break priority ties deterministically. It does
not replace the priority for ordering.

## Why this exists

The standard `heapq` module gives you a heap of lists but no way to find and
update an existing element short of a linear scan. For algorithms that need
to relax priorities on already-queued items — Dijkstra, A*, Prim, min-cost
flow residual updates — that scan turns the whole algorithm O(n^2). This
library keeps a live index from `id(item)` to the item's slot so
decrease-key and remove are O(log n).

The trade-off: the queue holds strong references to every queued item (so
`id()` cannot be recycled by the GC while an item is enqueued). If you queue
millions of long-lived objects, that is real memory. For the sizes that
matter most — graph searches over a few hundred thousand nodes — it is fine.

## The awkward edge you will hit

`decrease_key` **refuses** a priority that is equal to or greater than the
current one and raises `ValueError`. This is deliberate: a silent no-op on an
equal value or a silent *increase* hides real bugs in caller math. If you
genuinely need to raise a priority, `pop` and `push` again — there is no
combined `update` method, because half the callers of such a method expect it
to sift up and half expect it to sift down, and guessing wrong is worse than
making you say what you mean.

Ties between equal priorities break arbitrarily by heap position unless you
pass a `key` to the constructor. Even with a `key`, two items with equal
priority *and* equal `key(item)` remain arbitrary — do not rely on a
stable tie-break in that case.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```
