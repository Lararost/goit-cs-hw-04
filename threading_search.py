"""Багатопотокова версія: окремий набір файлів для кожного Thread."""
from threading import Thread
from common import prepare, scan_files, merge_results, run_cli


def _worker(index, files, keywords, slots):
    # Потоки пишуть у різні слоти; головний потік читає лише після join.
    slots[index] = scan_files(files, keywords)


def search_threading(files, keywords, workers=4):
    """Повернути dict[str, list[str]]; файлові помилки надрукувати в stderr."""
    words, chunks = prepare(files, keywords, workers)
    slots = [None] * len(chunks)
    threads = [Thread(target=_worker, args=(i, chunk, words, slots), name=f"search-{i}")
               for i, chunk in enumerate(chunks)]
    started = []
    try:
        for thread in threads:
            thread.start()
            started.append(thread)
    finally:
        for thread in started:
            thread.join()
    if any(slot is None for slot in slots):
        raise RuntimeError("Один із потоків не повернув результат.")
    return merge_results(words, slots)


if __name__ == "__main__":
    raise SystemExit(run_cli({"threading": search_threading}))
