from queue import Queue


class UniqueQueue(Queue):
    def _init(self, maxsize):
        Queue._init(self, maxsize)
        self.all_items = set()

    def _put(self, item):
        if item not in self.all_items:
            Queue._put(self, item)
            self.all_items.add(item)

    def _get(self):
        item = Queue._get(self)
        self.all_items.remove(item)
        return item